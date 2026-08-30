import logging
import asyncio
import os
import traceback
from typing import Dict, Any

import httpx
from duckduckgo_search import DDGS
from tavily import TavilyClient

logger = logging.getLogger(__name__)

async def _search_tavily(query: str) -> dict:
    tavily_api_key = os.getenv("TAVILY_API_KEY", "")
    if not tavily_api_key:
        raise ValueError("TAVILY_API_KEY not set")
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        payload = {"api_key": tavily_api_key, "query": query, "search_depth": "advanced"}
        resp = await client.post("https://api.tavily.com/search", json=payload)
        resp.raise_for_status()
        response = resp.json()
        
    snippets = [res.get("content", "") for res in response.get("results", []) if res.get("content")]
    context = "\n".join(snippets)
    if not context.strip():
        raise ValueError("Empty results")
    return {"source_tier": "Tavily", "context": context[:2500], "success": True}

async def _search_jina(query: str) -> dict:
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"https://s.jina.ai/{query}", headers={"Accept": "text/plain", "X-Retain-Images": "none"})
        resp.raise_for_status()
        context = resp.text[:2500]
        if not context.strip():
            raise ValueError("Empty results")
        return {"source_tier": "Jina AI", "context": context, "success": True}

async def _search_serper(query: str) -> dict:
    serper_api_key = os.getenv("SERPER_API_KEY", "")
    if not serper_api_key:
        raise ValueError("SERPER_API_KEY not set")
    async with httpx.AsyncClient(timeout=5.0) as client:
        headers = {"X-API-KEY": serper_api_key, "Content-Type": "application/json"}
        payload = {"q": query, "gl": "in", "hl": "en", "num": 3}
        resp = await client.post("https://google.serper.dev/search", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        items = data.get("organic", [])[:3]
        snippets = [item.get("snippet", "") for item in items if item.get("snippet")]
        context = "\n".join(snippets)
        if not context.strip():
            raise ValueError("Empty results")
        return {"source_tier": "Serper.dev", "context": context[:2500], "success": True}

async def _search_ddg(query: str) -> dict:
    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(None, lambda: DDGS(timeout=5.0).text(query, max_results=3))
    snippets = [res.get("body", "") for res in results if res.get("body")]
    context = "\n".join(snippets)
    if not context.strip():
        raise ValueError("Empty results")
    return {"source_tier": "DuckDuckGo", "context": context[:2500], "success": True}

async def execute_resilient_search(query: str) -> dict:
    """
    Concurrent Search Pipeline:
    Fires all available search tiers at once. The first one to return a valid
    non-empty result wins. Max total wait time is 6 seconds.
    """
    logger.info(f"Executing concurrent search for: {query}")
    
    tasks = [
        asyncio.create_task(_search_tavily(query), name="Tavily"),
        asyncio.create_task(_search_jina(query), name="Jina AI"),
        asyncio.create_task(_search_serper(query), name="Serper.dev"),
        asyncio.create_task(_search_ddg(query), name="DuckDuckGo")
    ]
    
    # We want the FIRST successful result, but if one fails quickly, we wait for others.
    start_time = asyncio.get_running_loop().time()
    timeout = 6.0
    
    try:
        for fut in asyncio.as_completed(tasks, timeout=timeout):
            try:
                result = await fut
                if result and result.get("success"):
                    logger.info(f"Search won by {result['source_tier']} in {asyncio.get_running_loop().time() - start_time:.2f}s")
                    # Cancel remaining
                    for t in tasks:
                        if not t.done():
                            t.cancel()
                    return result
            except Exception as e:
                # One of the tiers failed, continue to the next completed one
                continue
    except asyncio.TimeoutError:
        logger.error(f"Search timed out after {timeout}s for all concurrent tiers")
    
    # Cancel any hanging tasks
    for t in tasks:
        if not t.done():
            t.cancel()

    return {
        "source_tier": "None",
        "context": "web verification unavailable",
        "success": False
    }

class SearchVerifier:
    async def verify_claim(self, claim: dict, call_id: str = None) -> dict:
        if isinstance(claim, dict):
            parts = []
            if claim.get('category'): parts.append(claim.get('category'))
            
            # Deduplicate entities
            for e in claim.get('entities_claimed', []):
                if e and e not in parts: parts.append(e)
                
            authority = claim.get('claimed_authority', '')
            if authority and authority not in parts: parts.append(authority)
            
            query = " ".join([str(p) for p in parts if p]).strip()
        else:
            query = str(claim)
            
        if not query:
            query = "scam check"
            
        result = await execute_resilient_search(query)
        return {
            "source": result.get("source_tier", "Unknown"),
            "context": result.get("context", ""),
            "results": [{"body": result.get("context", "")}] if result.get("context") else [],
            "error": None if result.get("success") else "Search failed"
        }
