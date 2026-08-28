import logging
import asyncio
import os
from typing import Dict, Any

import httpx
from duckduckgo_search import DDGS
from tavily import TavilyClient

logger = logging.getLogger(__name__)

async def execute_resilient_search(query: str) -> dict:
    """
    Cascading Fallback Search Pipeline:
    Tier 1: Tavily API (Primary)
    Tier 2: Jina AI (Fallback 1)
    Tier 3: Serper.dev (Fallback 2)
    Tier 4: DuckDuckGo Python Package (Failsafe)
    """
    
    # Tier 1: Tavily API
    try:
        tavily_api_key = os.getenv("TAVILY_API_KEY", "")
        if tavily_api_key:
            logger.info(f"Attempting Tier 1 (Tavily) for query: {query}")
            client = TavilyClient(api_key=tavily_api_key)
            
            # Run the synchronous Tavily client in an executor
            loop = asyncio.get_running_loop()
            def tavily_search():
                return client.search(query, search_depth="advanced")
                
            response = await asyncio.wait_for(loop.run_in_executor(None, tavily_search), timeout=8.0)
            
            snippets = [res.get("content", "") for res in response.get("results", []) if res.get("content")]
            context = "\n".join(snippets)
            
            if context.strip():
                return {
                    "source_tier": "Tavily",
                    "context": context[:2500],
                    "success": True
                }
        else:
            logger.warning("Tier 1 (Tavily) skipped: TAVILY_API_KEY not set")
    except Exception as e:
        logger.warning(f"Tier 1 (Tavily) failed: {e}")

    # Tier 2: Jina AI
    try:
        logger.info(f"Attempting Tier 2 (Jina AI) for query: {query}")
        async with httpx.AsyncClient(timeout=5.0) as client:
            headers = {
                "Accept": "text/plain",
                "X-Retain-Images": "none"
            }
            resp = await client.get(f"https://s.jina.ai/{query}", headers=headers)
            resp.raise_for_status()
            text = resp.text
            context = text[:2500]
            if context.strip():
                return {
                    "source_tier": "Jina AI",
                    "context": context,
                    "success": True
                }
    except Exception as e:
        logger.warning(f"Tier 2 (Jina AI) failed: {e}")

    # Tier 3: Serper.dev
    try:
        logger.info(f"Attempting Tier 3 (Serper.dev) for query: {query}")
        serper_api_key = os.getenv("SERPER_API_KEY", "")
        if serper_api_key:
            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = {
                    "X-API-KEY": serper_api_key,
                    "Content-Type": "application/json",
                }
                payload = {"q": query, "gl": "in", "hl": "en", "num": 3}
                resp = await client.post("https://google.serper.dev/search", headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                
                items = data.get("organic", [])[:3]
                snippets = [item.get("snippet", "") for item in items if item.get("snippet")]
                context = "\n".join(snippets)
                
                if context.strip():
                    return {
                        "source_tier": "Serper.dev",
                        "context": context[:2500],
                        "success": True
                    }
        else:
            logger.warning("Tier 3 (Serper.dev) skipped: SERPER_API_KEY not set")
    except Exception as e:
        logger.warning(f"Tier 3 (Serper.dev) failed: {e}")

    # Tier 4: DuckDuckGo Search Package
    try:
        logger.info(f"Attempting Tier 4 (DuckDuckGo) for query: {query}")
        loop = asyncio.get_running_loop()
        def ddg_search():
            return DDGS().text(query, max_results=3)
        
        results = await asyncio.wait_for(loop.run_in_executor(None, ddg_search), timeout=8.0)
        
        snippets = [res.get("body", "") for res in results if res.get("body")]
        context = "\n".join(snippets)
        
        if context.strip():
            return {
                "source_tier": "DuckDuckGo",
                "context": context[:2500],
                "success": True
            }
    except Exception as e:
        logger.warning(f"Tier 4 (DuckDuckGo) failed: {e}")

    # Fallback failure
    return {
        "source_tier": "None",
        "context": "No search results could be retrieved from any tier.",
        "success": False
    }
