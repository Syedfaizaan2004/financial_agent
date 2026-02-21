"""
backend/forecasting/utils.py

Ticker validation utilities for the Financial & Market Research Agent.

Loads the supported stock list once at import time and exposes helpers
to validate that a requested ticker is within the trained model universe.
"""

import logging
import pickle
from typing import List

from fastapi import HTTPException

from backend.app.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Load supported tickers once at module import (fast path for every request)
# ---------------------------------------------------------------------------
_settings = get_settings()
_SUPPORTED_TICKERS: List[str] = []

try:
    with open(_settings.STOCKS_LIST_PATH, "rb") as _f:
        _raw = pickle.load(_f)
        # Normalise to uppercase strings
        _SUPPORTED_TICKERS = [str(t).upper() for t in _raw]
    logger.info(
        "✅  Ticker universe loaded: %d tickers from %s",
        len(_SUPPORTED_TICKERS),
        _settings.STOCKS_LIST_PATH,
    )
except FileNotFoundError:
    logger.error(
        "❌  stocks_used.pkl not found at '%s'. "
        "Ticker validation will reject all tickers.",
        _settings.STOCKS_LIST_PATH,
    )
except Exception as exc:  # pylint: disable=broad-except
    logger.error("❌  Failed to load ticker universe: %s", exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_supported_tickers() -> List[str]:
    """
    Return the full list of tickers supported by the trained models.

    Returns:
        List[str]: Uppercase ticker symbols known to the model universe.
    """
    return list(_SUPPORTED_TICKERS)


def is_supported_ticker(ticker: str) -> bool:
    """
    Check whether a ticker is within the trained model universe.

    Args:
        ticker (str): Stock symbol to check (case-insensitive).

    Returns:
        bool: True if the ticker is supported, False otherwise.
    """
    return ticker.upper() in _SUPPORTED_TICKERS


def validate_ticker(ticker: str) -> str:
    """
    Validate a ticker and return its canonical uppercase form.

    Raises a 404 HTTPException with a descriptive message if the ticker
    is not supported, so API callers always receive a clear error.

    Args:
        ticker (str): Stock symbol to validate (case-insensitive).

    Returns:
        str: Canonical uppercase ticker symbol.

    Raises:
        HTTPException: 404 if ticker is not in the supported universe.
    """
    canonical = ticker.upper()
    if canonical not in _SUPPORTED_TICKERS:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Ticker '{canonical}' is not supported by the current model universe. "
                f"Supported tickers: {', '.join(sorted(_SUPPORTED_TICKERS))}."
            ),
        )
    return canonical
