"""
backend/core/peer_metrics.py

Peer metrics fetcher for the Peer Comparison Engine.

Retrieves key valuation, profitability, and leverage metrics for a list
of tickers from Yahoo Finance (via yfinance). All missing fields are set
to None — downstream code must handle absent values safely.

Metrics fetched per ticker:
  Valuation    : pe_ratio, price_to_book
  Profitability: net_margin, roe
  Growth       : revenue_growth (trailing YoY from yfinance info)
  Leverage     : debt_to_equity
  Market info  : market_cap, sector
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _safe_float(value: Any) -> Optional[float]:
    """Safely convert a value to float, returning None on failure."""
    if value is None:
        return None
    try:
        import math
        v = float(value)
        return None if math.isnan(v) or math.isinf(v) else v
    except (TypeError, ValueError):
        return None


def fetch_peer_metrics(tickers: List[str]) -> Dict[str, Dict[str, Any]]:
    """
    Fetch key comparative metrics for a list of stock tickers.

    Uses yfinance's `.info` dict which returns pre-computed trailing metrics,
    avoiding the need to recalculate ratios from raw financial statements
    (making this fast and suitable for peer-wide comparison).

    Args:
        tickers (list[str]): List of uppercase stock symbols.

    Returns:
        dict[str, dict]: Keyed by ticker symbol. Each value contains:
            pe_ratio (float | None)
            price_to_book (float | None)
            net_margin (float | None): As a percentage (e.g. 23.5 = 23.5%)
            roe (float | None): As a percentage
            revenue_growth (float | None): YoY % (e.g. 12.4 = 12.4%)
            debt_to_equity (float | None)
            market_cap (float | None)
            sector (str | None)
            company_name (str | None)
            data_available (bool): False if no info could be fetched

    Raises:
        RuntimeError: If yfinance is not installed.
    """
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError(
            "yfinance is required for peer metrics. "
            "Install it with: pip install yfinance"
        ) from exc

    results: Dict[str, Dict[str, Any]] = {}

    for ticker in tickers:
        logger.info("Fetching metrics for peer: %s", ticker)
        try:
            info = yf.Ticker(ticker).info or {}
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("Could not fetch info for %s: %s", ticker, exc)
            info = {}

        if not info:
            results[ticker] = _empty_metrics(ticker, data_available=False)
            continue

        # --- Net margin: yfinance returns decimal (0.23) → convert to % ---
        raw_net_margin = _safe_float(info.get("profitMargins"))
        net_margin = round(raw_net_margin * 100, 2) if raw_net_margin is not None else None

        # --- ROE: yfinance returns decimal → convert to % ---
        raw_roe = _safe_float(info.get("returnOnEquity"))
        roe = round(raw_roe * 100, 2) if raw_roe is not None else None

        # --- Revenue growth: yfinance returns decimal → convert to % ---
        raw_rev_growth = _safe_float(info.get("revenueGrowth"))
        revenue_growth = round(raw_rev_growth * 100, 2) if raw_rev_growth is not None else None

        results[ticker] = {
            "ticker": ticker,
            "company_name": info.get("longName") or info.get("shortName") or ticker,
            "sector": info.get("sector"),
            "pe_ratio": _safe_float(info.get("trailingPE")),
            "price_to_book": _safe_float(info.get("priceToBook")),
            "net_margin": net_margin,
            "roe": roe,
            "revenue_growth": revenue_growth,
            "debt_to_equity": _safe_float(info.get("debtToEquity")),
            "market_cap": _safe_float(info.get("marketCap")),
            "data_available": True,
        }
        logger.debug("Metrics for %s: %s", ticker, results[ticker])

    return results


def _empty_metrics(ticker: str, data_available: bool = False) -> Dict[str, Any]:
    """Return a stub metrics dict for a ticker with unavailable data."""
    return {
        "ticker": ticker,
        "company_name": ticker,
        "sector": None,
        "pe_ratio": None,
        "price_to_book": None,
        "net_margin": None,
        "roe": None,
        "revenue_growth": None,
        "debt_to_equity": None,
        "market_cap": None,
        "data_available": data_available,
    }
