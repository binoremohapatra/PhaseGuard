"""
intel/company_verification.py — Entity/company verification signals module.

PURPOSE:
  This module produces SIGNALS FOR HUMAN JUDGMENT, not automated fraud
  determinations. The goal is to give the protected user and later
  investigators useful leads, not to make a legal claim about any specific
  company or person.

Checks performed:
  1. MCA Portal search link    — direct URL to verify company registration
                                   manually (no scraping, .gov.in is fragile).
  2. WHOIS domain age check    — flags recently registered domains (<6 months)
                                   as a mild caution signal.
  3. Public presence check     — uses the 3-tier search fallback to look for
                                   public news/wiki coverage of the claimed entity.
                                   Absence of coverage is a signal, not proof.

Output of verify_entity():
  {
    entity_name: str,
    mca_search_url: str,
    domain: str | None,
    domain_age_days: int | None,
    domain_flag: str | None,     # e.g. "recently registered (<6 months)"
    public_presence_found: bool,
    public_presence_sources: list[str],
    confidence_note: str,
  }

IMPORTANT: All fields are provided as investigative signals only.
None of them constitute legal evidence of fraud or legitimacy.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)

_RECENT_DOMAIN_THRESHOLD_DAYS = 180  # domains younger than 6 months flagged as caution

_MCA_SEARCH_BASE = (
    "https://www.mca.gov.in/mcafoportal/companyLLPMasterData.do"
    "?companyname={name}"
)
_MCA_ALT_BASE = (
    "https://efiling.mca.gov.in/eFiling/helpdeskdata.do"
    "?companyname={name}"
)


# ── WHOIS domain age ──────────────────────────────────────────────────────────

def _check_domain_age(domain: str) -> tuple[Optional[int], Optional[str]]:
    """
    Look up WHOIS data for a domain and return (age_days, flag).
    Returns (None, None) if WHOIS data is unavailable or privacy-shielded.

    This is a SIGNAL: recently registered domains are more commonly
    associated with scam infrastructure, but many legitimate businesses
    also use new domains.
    """
    try:
        import whois  # python-whois

        w = whois.whois(domain)
        creation_date = w.creation_date

        if creation_date is None:
            return None, "WHOIS: creation date unavailable (privacy-shielded or unsupported TLD)"

        # python-whois sometimes returns a list
        if isinstance(creation_date, list):
            creation_date = creation_date[0]

        if not isinstance(creation_date, datetime):
            return None, "WHOIS: creation date in unexpected format"

        # Normalize to UTC
        if creation_date.tzinfo is None:
            creation_date = creation_date.replace(tzinfo=timezone.utc)

        age_days = (datetime.now(timezone.utc) - creation_date).days

        if age_days < _RECENT_DOMAIN_THRESHOLD_DAYS:
            flag = (
                f"recently registered ({age_days} days old) — exercise caution; "
                f"scam sites are typically short-lived"
            )
        elif age_days < 365:
            flag = f"registered {age_days} days ago (under 1 year old — mild caution)"
        else:
            flag = None  # established domain, no special flag

        return age_days, flag

    except Exception as exc:
        logger.debug("WHOIS lookup failed for %r: %s", domain, exc)
        return None, "WHOIS: lookup failed or registry unsupported"


# ── MCA search URL ────────────────────────────────────────────────────────────

def _build_mca_search_url(name: str) -> str:
    """
    Build a direct MCA Portal search URL for manual verification.
    No web scraping performed — this is a human-usable reference link.
    """
    encoded = quote_plus(name.strip())
    # MCA21 v3 portal search
    return (
        f"https://www.mca.gov.in/mcafoportal/viewCompanyMasterData.do"
        f"?companyname={encoded}"
    )


# ── Public presence cross-check ───────────────────────────────────────────────

async def _check_public_presence(name: str) -> tuple[bool, List[str]]:
    """
    Use the 3-tier search fallback to look for public presence of the entity.
    Returns (found: bool, source_urls: list[str]).

    Absence of results for a claimed large/well-known entity is a meaningful
    signal — real banks, government bodies and large companies almost always
    have verifiable online coverage.
    """
    try:
        from factcheck.search import _search_newsapi, _search_duckduckgo, _search_wikipedia
        from core.config import get_settings

        cfg = get_settings()
        query = f'"{name}" official verified India'

        # Tier 1: NewsAPI
        if cfg.newsapi_key:
            results = await _search_newsapi(query, cfg.newsapi_key)
            if results:
                return True, [r["url"] for r in results if r.get("url")]

        # Tier 2: DuckDuckGo
        results = await _search_duckduckgo(query)
        if results:
            return True, [r["url"] for r in results if r.get("url")]

        # Tier 3: Wikipedia
        results = await _search_wikipedia(query)
        if results:
            return True, [r["url"] for r in results if r.get("url")]

        return False, []

    except Exception as exc:
        logger.warning("Public presence check failed for %r: %s", name, exc)
        return False, []


# ── Main entry point ──────────────────────────────────────────────────────────

async def verify_entity(
    name: str,
    domain: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Produce a verification signal dossier for a claimed entity/company.

    Parameters
    ----------
    name : str
        The entity name as extracted from the call (e.g. "Google HR",
        "State Bank of India", "XYZ Global Refund Services").
    domain : str or None
        An optional domain/URL associated with the entity (e.g. from a
        WhatsApp link or caller reference). Triggers WHOIS lookup.

    Returns
    -------
    dict with keys:
        entity_name, mca_search_url, domain, domain_age_days,
        domain_flag, public_presence_found, public_presence_sources,
        confidence_note

    IMPORTANT: All fields are investigative signals, not legal conclusions.
    """
    logger.info("Verifying entity: %r (domain=%r)", name, domain)

    # ── MCA link (no scraping, human-usable) ──────────────────────────────────
    mca_url = _build_mca_search_url(name)

    # ── WHOIS domain age ──────────────────────────────────────────────────────
    domain_age_days: Optional[int] = None
    domain_flag: Optional[str]     = None

    if domain:
        # Strip scheme/path — WHOIS only needs the bare domain
        bare_domain = domain.removeprefix("https://").removeprefix("http://").split("/")[0].strip()
        if bare_domain:
            domain_age_days, domain_flag = _check_domain_age(bare_domain)

    # ── Public presence check (async search) ──────────────────────────────────
    presence_found, presence_sources = await _check_public_presence(name)

    # ── Confidence note builder ───────────────────────────────────────────────
    signals: List[str] = []

    if domain_flag:
        signals.append(f"Domain: {domain_flag}.")
    if not presence_found:
        signals.append(
            f"No independent public coverage found for \"{name}\" via news/"
            f"search/Wikipedia — real banks, government bodies, and large "
            f"companies typically have verifiable online presence."
        )
    else:
        signals.append(
            f"Public presence found for \"{name}\" in search/news results."
        )

    if signals:
        note = (
            "SIGNAL ONLY \u2014 for human judgment: "
            + " ".join(signals)
            + " Verify manually via MCA link before drawing conclusions."
        )
    else:
        note = (
            f"No caution signals detected for \"{name}\". "
            "This does not guarantee legitimacy — always verify independently."
        )

    return {
        "entity_name":            name,
        "mca_search_url":         mca_url,
        "domain":                 domain,
        "domain_age_days":        domain_age_days,
        "domain_flag":            domain_flag,
        "public_presence_found":  presence_found,
        "public_presence_sources": presence_sources[:5],
        "confidence_note":        note,
    }
