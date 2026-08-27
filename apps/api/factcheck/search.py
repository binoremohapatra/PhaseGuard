"""
factcheck/search.py — Web verification of extracted scam claims.

Design (3-Tier Free Fallback Chain):
  Tier 1: NewsAPI.org        — Best for India-specific scam news coverage.
           Requires NEWSAPI_KEY (free, no card — https://newsapi.org/register).
  Tier 2: DuckDuckGo Instant — No key required. Always available.
  Tier 3: Wikipedia API      — No key required. Good for general fact-checking
           (e.g. "does RBI/police ever call demanding money?").
  Stub:   Returned only when all three tiers produce no useful results.

Cache key: SHA-256 of normalized claim text (category + entities + demands).
Caching protects NewsAPI's 100 req/day free quota from scripted scam replays.

Consistent return shape (regardless of which tier answered):
  {
    verified: bool | None,
    source: "newsapi" | "duckduckgo" | "wikipedia" | "stub",
    results: [{"title": str, "snippet": str, "url": str}],
    note: str,
    query: str,
    cached: bool,
  }
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, TypedDict
from urllib.parse import quote_plus

import httpx

logger = logging.getLogger(__name__)

_NEWSAPI_URL       = "https://newsapi.org/v2/everything"
_DDGS_INSTANT_URL  = "https://api.duckduckgo.com/"
_WIKIPEDIA_URL     = "https://en.wikipedia.org/w/api.php"


# ── Return type ───────────────────────────────────────────────────────────────

class SearchResult(TypedDict):
    verified: Optional[bool]
    source: str          # "newsapi" | "duckduckgo" | "wikipedia" | "stub"
    results: List[Dict[str, str]]  # [{"title", "snippet", "url"}]
    note: str
    query: str
    cached: bool


# ── Cache helpers ─────────────────────────────────────────────────────────────

def _claim_cache_key(claim_data: dict) -> str:
    """SHA-256 of the normalized claim (category + entities + demands)."""
    normalized = json.dumps(
        {k: claim_data.get(k) for k in ("category", "entities_claimed", "demands")},
        sort_keys=True,
    )
    return hashlib.sha256(normalized.encode()).hexdigest()[:16]


# ── Query builder ─────────────────────────────────────────────────────────────

def _build_search_query(claim: dict) -> str:
    """Build a context-rich India-centric search query from an ExtractedClaim."""
    parts: List[str] = []
    category  = claim.get("category", "")
    entities  = claim.get("entities_claimed", [])
    demands   = claim.get("demands", [])
    authority = claim.get("claimed_authority", "")

    if entities:
        parts.append(entities[0])
    elif authority:
        parts.append(authority)

    if demands:
        parts.append(demands[0])

    if not parts and category:
        parts.append(category.replace("_", " "))

    parts.append("scam India")
    return " ".join(parts)


# ── Tier 1 — NewsAPI ──────────────────────────────────────────────────────────

async def _search_newsapi(query: str, api_key: str) -> Optional[List[Dict[str, str]]]:
    """Query NewsAPI /v2/everything. Returns list of results or None on error."""
    try:
        params = {
            "q": query,
            "apiKey": api_key,
            "language": "en",
            "sortBy": "relevancy",
            "pageSize": 5,
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(_NEWSAPI_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        items = data.get("articles", [])[:5]
        results = [
            {
                "title":   a.get("title", ""),
                "snippet": a.get("description", "") or a.get("content", "")[:200],
                "url":     a.get("url", ""),
            }
            for a in items
            if a.get("title")
        ]
        return results if results else None
    except Exception as exc:
        logger.warning("NewsAPI search failed: %s", exc)
        return None


# ── Tier 2 — DuckDuckGo ───────────────────────────────────────────────────────

async def _search_duckduckgo(query: str) -> Optional[List[Dict[str, str]]]:
    """Query DuckDuckGo Instant Answer API (no key required)."""
    try:
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(_DDGS_INSTANT_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        results: List[Dict[str, str]] = []
        abstract     = data.get("AbstractText", "")
        abstract_url = data.get("AbstractURL", "")
        if abstract:
            results.append({
                "title":   data.get("AbstractSource", "DuckDuckGo"),
                "snippet": abstract,
                "url":     abstract_url,
            })
        for topic in data.get("RelatedTopics", [])[:4]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title":   topic.get("Text", "")[:80],
                    "snippet": topic.get("Text", ""),
                    "url":     topic.get("FirstURL", ""),
                })
        return results if results else None
    except Exception as exc:
        logger.warning("DuckDuckGo search failed: %s", exc)
        return None


# ── Tier 3 — Wikipedia ────────────────────────────────────────────────────────

async def _search_wikipedia(query: str) -> Optional[List[Dict[str, str]]]:
    """Query Wikipedia search API (no key required)."""
    try:
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 5,
        }
        headers = {
            # Wikipedia API requires a User-Agent per their API policy
            "User-Agent": "PhaseGuard/1.0 (anti-scam-app; contact@phaseguard.dev)"
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(_WIKIPEDIA_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        items = data.get("query", {}).get("search", [])[:5]
        results = [
            {
                "title":   item.get("title", ""),
                "snippet": item.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", ""),
                "url":     f"https://en.wikipedia.org/wiki/{quote_plus(item.get('title','').replace(' ', '_'))}",
            }
            for item in items
            if item.get("title")
        ]
        return results if results else None
    except Exception as exc:
        logger.warning("Wikipedia search failed: %s", exc)
        return None


# ── SearchVerifier ────────────────────────────────────────────────────────────

class SearchVerifier:
    """
    Runs the 3-tier free search fallback chain for a given scam claim.
    Caches results within the instance lifetime to protect the NewsAPI quota.
    """

    def __init__(self) -> None:
        self._cache: Dict[str, SearchResult] = {}

    async def verify_claim(self, claim: dict, call_id: str = "") -> SearchResult:
        """
        Execute the 3-tier fallback: NewsAPI -> DuckDuckGo -> Wikipedia -> Stub.
        Falls through to the next tier only when the previous returns no results.
        """
        cache_key = _claim_cache_key(claim)
        if cache_key in self._cache:
            cached = dict(self._cache[cache_key])
            cached["cached"] = True
            logger.debug("Search cache hit for call_id=%r key=%s", call_id, cache_key)
            return cached  # type: ignore[return-value]

        query = _build_search_query(claim)

        from core.config import get_settings
        cfg = get_settings()

        result: SearchResult

        # ── Tier 1: NewsAPI ───────────────────────────────────────────────────
        if cfg.newsapi_key:
            logger.info("Searching [NewsAPI] for claim evidence: %r (call_id=%s)", query, call_id)
            news_results = await _search_newsapi(query, cfg.newsapi_key)
            if news_results:
                result = SearchResult(
                    verified=None,
                    source="newsapi",
                    results=news_results,
                    note="Results from NewsAPI.org news search.",
                    query=query,
                    cached=False,
                )
                self._cache[cache_key] = result
                return result

        # ── Tier 2: DuckDuckGo ────────────────────────────────────────────────
        logger.info("Searching [DuckDuckGo] for claim evidence: %r (call_id=%s)", query, call_id)
        ddg_results = await _search_duckduckgo(query)
        if ddg_results:
            result = SearchResult(
                verified=None,
                source="duckduckgo",
                results=ddg_results,
                note="Results from DuckDuckGo Instant Answer API.",
                query=query,
                cached=False,
            )
            self._cache[cache_key] = result
            return result

        # ── Tier 3: Wikipedia ─────────────────────────────────────────────────
        logger.info("Searching [Wikipedia] for claim evidence: %r (call_id=%s)", query, call_id)
        wiki_results = await _search_wikipedia(query)
        if wiki_results:
            result = SearchResult(
                verified=None,
                source="wikipedia",
                results=wiki_results,
                note="Results from Wikipedia search API.",
                query=query,
                cached=False,
            )
            self._cache[cache_key] = result
            return result

        # ── Stub: all tiers exhausted ─────────────────────────────────────────
        logger.info(
            "All search tiers returned empty for claim evidence: %r (call_id=%s) [STUB]",
            query, call_id,
        )
        result = SearchResult(
            verified=None,
            source="stub",
            results=[],
            note="No results found across NewsAPI / DuckDuckGo / Wikipedia for this query.",
            query=query,
            cached=False,
        )
        self._cache[cache_key] = result
        return result
