"""
backend/utils/cache.py

In-memory TTL cache for the Financial Research Agent.

Provides a lightweight, thread-safe cache with automatic expiry.
Used to avoid repeated yfinance / LLM calls during demo mode or
repeated requests for the same ticker within a session.

Usage:
    from backend.utils.cache import cache_result, get_cached_result, clear_cache

    cache_result("forecast:AAPL", data, ttl=300)
    result = get_cached_result("forecast:AAPL")   # None if expired/missing
"""

from __future__ import annotations

import time
import logging
import threading
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal store: key → (data, expiry_timestamp)
# ---------------------------------------------------------------------------
_store: Dict[str, Tuple[Any, float]] = {}
_lock  = threading.RLock()

# ---------------------------------------------------------------------------
# Default TTL constants (seconds)
# ---------------------------------------------------------------------------
TTL_FORECAST    = 300    # 5 min  — forecast directions
TTL_FUNDAMENTALS = 600   # 10 min — fundamental data
TTL_SCENARIO    = 300    # 5 min  — scenario results
TTL_AGENT       = 180    # 3 min  — full agent responses
TTL_DEMO        = 3600   # 1 hr   — demo-mode preloaded data


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def cache_result(key: str, data: Any, ttl: int = TTL_FUNDAMENTALS) -> None:
    """
    Store a result in the in-memory cache with a TTL.

    Args:
        key (str): Cache key (e.g. 'forecast:AAPL', 'agent:MSFT:quick_research').
        data (Any): The data to cache. Should be JSON-serialisable.
        ttl (int): Time-to-live in seconds. 0 = no expiry.
    """
    expiry = time.monotonic() + ttl if ttl > 0 else float("inf")
    with _lock:
        _store[key] = (data, expiry)
    logger.debug("[cache] SET  key=%s ttl=%ds entries=%d", key, ttl, len(_store))


def get_cached_result(key: str) -> Optional[Any]:
    """
    Retrieve a cached result. Returns None if missing or expired.

    Args:
        key (str): Cache key.

    Returns:
        Any | None: Cached data or None.
    """
    with _lock:
        entry = _store.get(key)
        if entry is None:
            return None
        data, expiry = entry
        if time.monotonic() > expiry:
            del _store[key]
            logger.debug("[cache] EXPIRED key=%s", key)
            return None
        logger.debug("[cache] HIT  key=%s", key)
        return data


def invalidate(key: str) -> bool:
    """Remove a specific key from the cache. Returns True if it existed."""
    with _lock:
        if key in _store:
            del _store[key]
            return True
        return False


def clear_cache() -> int:
    """Remove all entries. Returns number of entries cleared."""
    with _lock:
        n = len(_store)
        _store.clear()
    logger.info("[cache] Cleared %d entries", n)
    return n


def evict_expired() -> int:
    """Remove all expired entries. Returns number evicted."""
    now = time.monotonic()
    with _lock:
        expired_keys = [k for k, (_, exp) in _store.items() if now > exp]
        for k in expired_keys:
            del _store[k]
    if expired_keys:
        logger.debug("[cache] Evicted %d expired entries", len(expired_keys))
    return len(expired_keys)


def cache_stats() -> Dict[str, int]:
    """Return cache statistics."""
    now = time.monotonic()
    with _lock:
        total   = len(_store)
        expired = sum(1 for _, exp in _store.values() if now > exp)
    return {"total_entries": total, "expired": expired, "live": total - expired}


# ---------------------------------------------------------------------------
# Convenience: cache key builders
# ---------------------------------------------------------------------------

def key_forecast(ticker: str) -> str:
    return f"forecast:{ticker.upper()}"

def key_fundamentals(ticker: str) -> str:
    return f"fundamentals:{ticker.upper()}"

def key_scenario(ticker: str, scenario: str) -> str:
    return f"scenario:{ticker.upper()}:{scenario}"

def key_agent(ticker: str, workflow: str) -> str:
    return f"agent:{ticker.upper()}:{workflow}"

def key_demo(ticker: str) -> str:
    return f"demo:{ticker.upper()}"
