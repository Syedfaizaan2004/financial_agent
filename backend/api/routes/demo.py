"""
backend/api/routes/demo.py

Demo mode API endpoints for the Financial Research Agent.

Provides endpoints that:
  - Run a full demo analysis instantly (using cache)
  - Return the guided demo flow steps
  - Report cache and readiness status
  - Allow manual cache refresh

All endpoints work whether DEMO_MODE is True or False.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)
router = APIRouter(tags=["demo"])


# ---------------------------------------------------------------------------
# GET /demo/status
# ---------------------------------------------------------------------------

@router.get("/status", summary="Demo mode status and cache info")
def demo_status() -> Dict[str, Any]:
    """
    Return demo mode configuration and cache statistics.

    Response includes:
      - demo_mode: bool
      - default_ticker: str
      - demo_tickers: list
      - cache_stats: {total_entries, live, expired}
    """
    from backend.app.demo_config import (
        is_demo_mode, get_demo_default_ticker, get_demo_tickers, get_demo_ttl
    )
    from backend.utils.cache import cache_stats

    return {
        "demo_mode":      is_demo_mode(),
        "default_ticker": get_demo_default_ticker(),
        "demo_tickers":   get_demo_tickers(),
        "cache_ttl_secs": get_demo_ttl(),
        "cache_stats":    cache_stats(),
    }


# ---------------------------------------------------------------------------
# GET /demo/run
# ---------------------------------------------------------------------------

@router.get("/run", summary="Run full demo analysis for a ticker")
def demo_run(
    ticker:   str = Query(default="AAPL", description="Ticker symbol to demo"),
    fresh:    bool = Query(default=False,  description="Force fresh analysis ignoring cache"),
    user_id:  str = Query(default="demo",  description="User ID for personalization"),
) -> Dict[str, Any]:
    """
    Return a complete analysis for a demo ticker.

    Checks demo cache first for instant response.
    If not cached (or fresh=True), runs the full agent pipeline.

    Response time:
      - Cached  → < 10 ms
      - Uncached → 2–8 s depending on workflow

    Returns full AgentResponse dict + demo metadata.
    """
    t_start = time.perf_counter()
    ticker  = ticker.upper().strip()

    # 1. Try demo cache (unless forced fresh)
    if not fresh:
        from backend.data.demo_cache import get_demo_data
        cached = get_demo_data(ticker)
        if cached is not None:
            elapsed = (time.perf_counter() - t_start) * 1000
            return {
                **cached,
                "_demo": {
                    "source":       "cache",
                    "response_ms":  round(elapsed, 2),
                    "demo_mode":    True,
                },
            }

    # 2. Run live analysis
    try:
        from backend.agent.agent import run_research_agent
        result = run_research_agent(
            query   = f"Quick summary of {ticker}",
            user_id = user_id,
        )
        elapsed = (time.perf_counter() - t_start) * 1000

        # Store in cache for next time
        from backend.data.demo_cache import store_demo_data
        store_demo_data(ticker, result)

        return {
            **result,
            "_demo": {
                "source":      "live",
                "response_ms": round(elapsed, 2),
                "demo_mode":   True,
            },
        }
    except Exception as exc:
        logger.error("[demo/run] Analysis failed for %s: %s", ticker, exc)
        raise HTTPException(status_code=500, detail=f"Demo analysis failed: {exc}")


# ---------------------------------------------------------------------------
# GET /demo/steps
# ---------------------------------------------------------------------------

@router.get("/steps", summary="Get guided demo flow steps")
def demo_steps() -> List[Dict[str, Any]]:
    """
    Return the full guided demo presentation flow.

    Each step includes:
      - step:        sequence number
      - id:          unique identifier ('forecast', 'scenario', etc.)
      - title:       short display title
      - description: what this step demonstrates
      - feature:     which UI component is highlighted
      - query:       example query to run
      - hint:        text for the audience explaining the feature
      - ticker / workflow: context

    Steps cover: Overview → Risk → Forecast → Scenario → Peers → Deep → Personalization
    """
    from backend.demo.flow import get_demo_steps
    return get_demo_steps()


# ---------------------------------------------------------------------------
# POST /demo/preload
# ---------------------------------------------------------------------------

@router.post("/preload", summary="Manually trigger demo cache pre-warm")
def demo_preload() -> Dict[str, Any]:
    """
    Manually trigger pre-warming of the demo cache.

    Useful after a server restart or when DEMO_MODE is newly enabled.

    Returns a per-ticker status dict: {AAPL: 'ok', MSFT: 'skipped', ...}
    """
    from backend.data.demo_cache import preload_demo_data
    t0     = time.perf_counter()
    status = preload_demo_data()
    elapsed = time.perf_counter() - t0
    return {
        "status":     status,
        "elapsed_s":  round(elapsed, 2),
        "message":    "Demo cache pre-warm complete.",
    }


# ---------------------------------------------------------------------------
# DELETE /demo/cache
# ---------------------------------------------------------------------------

@router.delete("/cache", summary="Clear demo cache entries")
def demo_clear_cache() -> Dict[str, Any]:
    """
    Clear all demo-mode cache entries.

    Useful when you want to force fresh data on next run.
    """
    from backend.data.demo_cache import clear_demo_cache
    clear_demo_cache()
    return {"message": "Demo cache cleared successfully."}


# ---------------------------------------------------------------------------
# GET /demo/cache/stats
# ---------------------------------------------------------------------------

@router.get("/cache/stats", summary="Detailed cache statistics")
def demo_cache_stats() -> Dict[str, Any]:
    """Return full cache statistics including all live entries."""
    from backend.utils.cache import cache_stats, evict_expired
    evict_expired()
    return cache_stats()
