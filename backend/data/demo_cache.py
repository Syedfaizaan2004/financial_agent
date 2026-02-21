"""
backend/data/demo_cache.py

Demo data cache for the Financial Research Agent.

Stores precomputed analysis results for demo tickers so responses
are instant during presentations. When DEMO_MODE=True, the agent
checks this cache before running any analysis pipeline.

Two levels:
    1. In-memory TTL cache (utils/cache.py)  — fast, session-scoped
    2. This module pre-populates at startup  — ensures t=0 readiness

Usage:
    from backend.data.demo_cache import get_demo_data, preload_demo_data

    data = get_demo_data("AAPL")   # None if not loaded yet / not demo mode
    await preload_demo_data()       # called at startup
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_PRELOAD_TIMEOUT_SECS = 30   # max time to spend on any single prewarm ticker


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_demo_data(ticker: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve preloaded demo data for a ticker from the TTL cache.

    Returns None if:
      - Demo mode is disabled
      - Ticker not yet preloaded
      - Cache entry has expired

    Args:
        ticker (str): Ticker symbol (case-insensitive).

    Returns:
        dict | None: Full agent response dict or None.
    """
    from backend.app.demo_config import is_demo_mode
    if not is_demo_mode():
        return None

    from backend.utils.cache import get_cached_result, key_demo
    result = get_cached_result(key_demo(ticker.upper()))
    if result is not None:
        logger.info("[demo_cache] Cache HIT for %s — returning instantly", ticker.upper())
    return result


def store_demo_data(ticker: str, data: Dict[str, Any]) -> None:
    """
    Store analysis result in the demo cache with a 1-hour TTL.

    Args:
        ticker (str): Ticker symbol.
        data (dict): Full agent response dict to cache.
    """
    from backend.utils.cache import cache_result, key_demo, TTL_DEMO
    cache_result(key_demo(ticker.upper()), data, ttl=TTL_DEMO)
    logger.info("[demo_cache] Stored demo data for %s (TTL=%ds)", ticker.upper(), TTL_DEMO)


def preload_demo_data() -> Dict[str, str]:
    """
    Pre-warm the demo cache by running quick_research for each demo ticker.

    Called at FastAPI startup when DEMO_MODE=True.
    Non-blocking per ticker — failures are caught and logged.

    Returns:
        dict: {ticker: "ok" | "failed" | "skipped"} status map.
    """
    from backend.app.demo_config import get_demo_tickers
    from backend.utils.cache import get_cached_result, key_demo

    tickers = get_demo_tickers()
    status: Dict[str, str] = {}

    logger.info("[demo_cache] Pre-warming %d demo tickers: %s", len(tickers), tickers)

    for ticker in tickers:
        # Skip if already in cache (e.g. server restarted with hot cache)
        if get_cached_result(key_demo(ticker)):
            logger.info("[demo_cache] %s already cached — skipping", ticker)
            status[ticker] = "skipped"
            continue

        t0 = time.perf_counter()
        try:
            from backend.agent.agent import run_research_agent
            result = run_research_agent(
                query   = f"Quick summary of {ticker}",
                user_id = "demo",
            )
            elapsed = time.perf_counter() - t0
            store_demo_data(ticker, result)
            logger.info(
                "[demo_cache] ✅ %s preloaded in %.2fs | status=%s",
                ticker, elapsed, result.get("status", "?"),
            )
            status[ticker] = "ok"
        except Exception as exc:  # pylint: disable=broad-except
            elapsed = time.perf_counter() - t0
            logger.warning(
                "[demo_cache] ⚠️  %s failed to preload in %.2fs: %s",
                ticker, elapsed, exc,
            )
            status[ticker] = f"failed: {exc}"

    oks     = sum(1 for v in status.values() if v == "ok")
    skipped = sum(1 for v in status.values() if v == "skipped")
    logger.info(
        "[demo_cache] Preload complete — %d/%d ok, %d skipped",
        oks, len(tickers), skipped,
    )
    return status


def clear_demo_cache() -> None:
    """Remove all demo cache entries."""
    from backend.app.demo_config import get_demo_tickers
    from backend.utils.cache import invalidate, key_demo
    for ticker in get_demo_tickers():
        invalidate(key_demo(ticker))
    logger.info("[demo_cache] All demo cache entries cleared.")
