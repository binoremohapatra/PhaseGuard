import asyncio, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def main():
    from core.config import get_settings
    cfg = get_settings()
    print("=" * 60)
    cfg.log_startup_summary()
    print("=" * 60)

    print("\n[TEST 1] verify_claim() with live APIs...")
    from factcheck.search import SearchVerifier
    verifier = SearchVerifier()
    claim = {
        "category": "FAKE_JOB_TASK",
        "entities_claimed": ["Google HR"],
        "demands": ["processing fee"],
        "claimed_authority": "Google HR",
    }
    result = await verifier.verify_claim(claim, call_id="smoke-001")
    print(f"  source : {result['source']}")
    print(f"  cached : {result['cached']}")
    print(f"  query  : {result['query']}")
    print(f"  hits   : {len(result['results'])}")
    for i, r in enumerate(result["results"], 1):
        print(f"  [{i}] {r['title']}")
        print(f"       {r['url']}")
        print(f"       {r['snippet'][:100]}...")
    if result["source"] in ["newsapi", "duckduckgo", "wikipedia"] and result["results"]:
        print(f"\n  PASS - {result['source']} returned real results")
    else:
        print(f"\n  FAIL or STUB - source={result['source']}, hits={len(result['results'])}")

    print("\n[TEST 2] Cache hit on second call...")
    r2 = await verifier.verify_claim(claim, call_id="smoke-001")
    print("  PASS - cache hit" if r2["cached"] else "  FAIL - no cache hit")

    print("\n[TEST 3] Graceful fallback to DuckDuckGo when NewsAPI key is blank...")
    orig = getattr(cfg, "newsapi_key", None)
    cfg.newsapi_key = ""
    v2 = SearchVerifier()
    r3 = await v2.verify_claim({"category": "DIGITAL_ARREST", "entities_claimed": [], "demands": [], "claimed_authority": ""}, call_id="smoke-002")
    cfg.newsapi_key = orig
    if r3["source"] in ["duckduckgo", "wikipedia"]:
        print(f"  PASS - successfully fell back to {r3['source']} (valid fallback)")
    else:
        print(f"  FAIL - expected duckduckgo or wikipedia, got {r3['source']}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
