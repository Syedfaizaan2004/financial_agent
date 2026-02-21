"""
backend/core/growth_analysis.py

Revenue and earnings growth analysis module.

Fetches up to 4 years of annual income statement data via yfinance and
computes year-over-year growth rates with trend classification.

Growth classifications:
  high_growth     : YoY revenue growth  > 20%
  moderate_growth : YoY revenue growth  5%–20%
  stagnant        : YoY revenue growth  0%–5%
  declining       : YoY revenue growth  < 0%
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _yoy_growth(current: float, previous: float) -> Optional[float]:
    """
    Compute year-over-year growth rate as a percentage.

    Args:
        current: Most recent year value.
        previous: Prior year value.

    Returns:
        float | None: Growth % rounded to 2 dp, or None if previous == 0 / None.
    """
    if previous is None or previous == 0:
        return None
    try:
        return round((current - previous) / abs(previous) * 100, 2)
    except (TypeError, ZeroDivisionError):
        return None


def _classify_growth(growth_pct: Optional[float]) -> str:
    """
    Classify a growth percentage into a human-readable trend label.

    Args:
        growth_pct: Revenue or earnings growth % (can be None).

    Returns:
        str: One of 'high_growth', 'moderate_growth', 'stagnant', 'declining', 'unknown'.
    """
    if growth_pct is None:
        return "unknown"
    if growth_pct > 20:
        return "high_growth"
    if growth_pct > 5:
        return "moderate_growth"
    if growth_pct >= 0:
        return "stagnant"
    return "declining"


def _extract_series(df: Any, label: str) -> List[Optional[float]]:
    """
    Extract values across all available years for a given row label in a
    yfinance-style DataFrame (index = metric, columns = dates desc).

    Args:
        df: pandas DataFrame or None.
        label: Row label (partial case-insensitive match).

    Returns:
        List of floats (most-recent first), up to 4 values.
    """
    import pandas as pd

    if df is None or df.empty:
        return []

    for idx in df.index:
        if label.lower() in str(idx).lower():
            row = df.loc[idx]
            values: List[Optional[float]] = []
            for val in row.iloc[:4]:       # Most recent 4 years
                try:
                    v = float(val)
                    values.append(None if pd.isna(v) else v)
                except (TypeError, ValueError):
                    values.append(None)
            return values
    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_growth(ticker: str) -> Dict[str, Any]:
    """
    Compute revenue and earnings YoY growth rates for the given ticker.

    Fetches up to 4 years of annual income statement data from yfinance
    and returns structured growth metrics with trend classification.

    Args:
        ticker (str): Validated uppercase stock symbol (e.g. 'AAPL').

    Returns:
        dict:
            revenue_series (list[float|None]): Annual revenues, most-recent first
            earnings_series (list[float|None]): Annual net incomes, most-recent first
            revenue_growth_yoy (float|None): Latest YoY revenue growth %
            earnings_growth_yoy (float|None): Latest YoY earnings growth %
            revenue_growth_trend (str): Trend label for revenue
            earnings_growth_trend (str): Trend label for earnings
            avg_revenue_growth (float|None): Average revenue growth over available years
            years_analyzed (int): Number of years used in the calculation

    Raises:
        RuntimeError: If yfinance is not installed.
    """
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError(
            "yfinance is required for growth analysis. "
            "Install it with: pip install yfinance"
        ) from exc

    logger.info("Analysing growth for: %s", ticker)
    stock = yf.Ticker(ticker)

    try:
        income_stmt = stock.financials
    except Exception as exc:
        logger.warning("Could not fetch income statement for %s: %s", ticker, exc)
        income_stmt = None

    # Extract multi-year series
    revenue_series  = _extract_series(income_stmt, "Total Revenue")
    if not revenue_series:
        revenue_series = _extract_series(income_stmt, "Revenue")

    earnings_series = _extract_series(income_stmt, "Net Income")
    if not earnings_series:
        earnings_series = _extract_series(income_stmt, "Net Income Common Stockholders")

    years_analyzed = max(len(revenue_series), len(earnings_series))

    # -----------------------------------------------------------------------
    # YoY growth (most recent vs. year before)
    # -----------------------------------------------------------------------
    revenue_growth_yoy: Optional[float] = None
    if len(revenue_series) >= 2 and revenue_series[0] and revenue_series[1]:
        revenue_growth_yoy = _yoy_growth(revenue_series[0], revenue_series[1])

    earnings_growth_yoy: Optional[float] = None
    if len(earnings_series) >= 2 and earnings_series[0] and earnings_series[1]:
        earnings_growth_yoy = _yoy_growth(earnings_series[0], earnings_series[1])

    # -----------------------------------------------------------------------
    # Average revenue growth over all available years
    # -----------------------------------------------------------------------
    avg_revenue_growth: Optional[float] = None
    if len(revenue_series) >= 2:
        growth_rates: List[float] = []
        for i in range(len(revenue_series) - 1):
            g = _yoy_growth(revenue_series[i], revenue_series[i + 1])
            if g is not None:
                growth_rates.append(g)
        if growth_rates:
            avg_revenue_growth = round(sum(growth_rates) / len(growth_rates), 2)

    revenue_growth_trend  = _classify_growth(revenue_growth_yoy)
    earnings_growth_trend = _classify_growth(earnings_growth_yoy)

    logger.info(
        "Growth for %s: rev_growth=%.2f%% (%s) | earn_growth=%.2f%% (%s)",
        ticker,
        revenue_growth_yoy or 0,
        revenue_growth_trend,
        earnings_growth_yoy or 0,
        earnings_growth_trend,
    )

    return {
        "revenue_series": revenue_series,
        "earnings_series": earnings_series,
        "revenue_growth_yoy": revenue_growth_yoy,
        "earnings_growth_yoy": earnings_growth_yoy,
        "revenue_growth_trend": revenue_growth_trend,
        "earnings_growth_trend": earnings_growth_trend,
        "avg_revenue_growth": avg_revenue_growth,
        "years_analyzed": years_analyzed,
    }
