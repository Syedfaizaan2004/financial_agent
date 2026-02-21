"""
backend/app/demo_config.py

Demo mode configuration for the Financial Research Agent.

Demo mode enables:
  - Pre-cached analysis results for instant responses
  - Warm startup preloading of demo tickers
  - Guided demo flow steps
  - Graceful fallback on API failures

Configuration via .env:
    DEMO_MODE=True
    DEMO_DEFAULT_TICKER=AAPL
    DEMO_TICKERS=AAPL,MSFT,TSLA
"""

from __future__ import annotations

import os
import logging
from typing import List

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_demo_mode() -> bool:
    """
    Return True if DEMO_MODE env var is set to a truthy value.

    Accepts: True, true, 1, yes, on
    """
    return os.getenv("DEMO_MODE", "false").strip().lower() in {"true", "1", "yes", "on"}


def get_demo_default_ticker() -> str:
    """Return the ticker to auto-load in demo mode (default: AAPL)."""
    return os.getenv("DEMO_DEFAULT_TICKER", "AAPL").strip().upper()


def get_demo_tickers() -> List[str]:
    """
    Return the list of tickers to pre-warm at startup.

    Reads comma-separated DEMO_TICKERS env var.
    Falls back to [AAPL, MSFT, TSLA, GOOGL].
    """
    raw = os.getenv("DEMO_TICKERS", "AAPL,MSFT,TSLA,GOOGL").strip()
    return [t.strip().upper() for t in raw.split(",") if t.strip()]


def get_demo_ttl() -> int:
    """Return TTL in seconds for demo cache entries (default: 3600 = 1 hour)."""
    try:
        return int(os.getenv("DEMO_CACHE_TTL", "3600"))
    except ValueError:
        return 3600


def log_demo_status() -> None:
    """Log the current demo mode configuration."""
    if is_demo_mode():
        logger.info("=" * 50)
        logger.info("🎯  DEMO MODE  : ENABLED")
        logger.info("    Default ticker  : %s", get_demo_default_ticker())
        logger.info("    Pre-warm tickers: %s", ", ".join(get_demo_tickers()))
        logger.info("    Cache TTL       : %ds", get_demo_ttl())
        logger.info("=" * 50)
    else:
        logger.info("[demo_config] Demo mode: DISABLED (set DEMO_MODE=True to enable)")
