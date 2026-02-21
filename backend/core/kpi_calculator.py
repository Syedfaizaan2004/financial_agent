"""
backend/core/kpi_calculator.py

KPI (Key Performance Indicator) calculator for the Financial Analysis Engine.

Takes a structured financial data dictionary (output of fetch_financial_statements)
and computes all key financial ratios safely — all divide-by-zero cases return None.

Ratios computed:
  Profitability : net_profit_margin, operating_margin, roe, roa
  Efficiency    : asset_turnover
  Liquidity     : current_ratio
  Leverage      : debt_to_equity, debt_to_assets
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Safe division helper
# ---------------------------------------------------------------------------

def _safe_div(
    numerator: Optional[float],
    denominator: Optional[float],
    round_digits: int = 4,
) -> Optional[float]:
    """
    Divide numerator by denominator, returning None on any failure.

    Handles: None inputs, zero denominator, non-numeric types.

    Args:
        numerator: Dividend value.
        denominator: Divisor value.
        round_digits: Decimal places to round to.

    Returns:
        float | None: Rounded result, or None if computation is impossible.
    """
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    try:
        return round(numerator / denominator, round_digits)
    except (TypeError, ZeroDivisionError):
        return None


def _pct(value: Optional[float]) -> Optional[float]:
    """Convert a ratio to a percentage rounded to 2 decimal places."""
    if value is None:
        return None
    return round(value * 100, 2)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_kpis(financials: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate key financial ratios from structured financial statement data.

    All values are derived from the input `financials` dict (output of
    fetch_financial_statements). No external calls are made here.

    Args:
        financials (dict): Structured financial data for a single company.
            Must contain the keys produced by fetch_financial_statements().

    Returns:
        dict: Computed KPIs with keys:
            Profitability:
                net_profit_margin (% | None)
                operating_margin (% | None)
                roe — Return on Equity (% | None)
                roa — Return on Assets (% | None)
            Efficiency:
                asset_turnover (ratio | None)
            Liquidity:
                current_ratio (ratio | None)
            Leverage:
                debt_to_equity (ratio | None)
                debt_to_assets (ratio | None)
            Meta:
                pe_ratio, eps, beta, market_cap, free_cash_flow, dividend_yield

    Notes:
        - All margin/return values are expressed as percentages (e.g. 23.5 = 23.5%)
        - None means the metric could not be calculated due to missing data
    """
    revenue             = financials.get("revenue")
    net_income          = financials.get("net_income")
    operating_income    = financials.get("operating_income")
    total_assets        = financials.get("total_assets")
    shareholder_equity  = financials.get("shareholder_equity")
    total_debt          = financials.get("total_debt")
    current_assets      = financials.get("current_assets")
    current_liabilities = financials.get("current_liabilities")

    # -----------------------------------------------------------------------
    # Profitability ratios
    # -----------------------------------------------------------------------

    # Net Profit Margin = Net Income / Revenue × 100
    net_profit_margin = _pct(_safe_div(net_income, revenue))

    # Operating Margin = Operating Income / Revenue × 100
    operating_margin = _pct(_safe_div(operating_income, revenue))

    # Return on Equity = Net Income / Shareholder Equity × 100
    roe = _pct(_safe_div(net_income, shareholder_equity))

    # Return on Assets = Net Income / Total Assets × 100
    roa = _pct(_safe_div(net_income, total_assets))

    # -----------------------------------------------------------------------
    # Efficiency ratios
    # -----------------------------------------------------------------------

    # Asset Turnover = Revenue / Total Assets
    asset_turnover = _safe_div(revenue, total_assets, round_digits=4)

    # -----------------------------------------------------------------------
    # Liquidity ratios
    # -----------------------------------------------------------------------

    # Current Ratio = Current Assets / Current Liabilities
    current_ratio = _safe_div(current_assets, current_liabilities, round_digits=4)

    # -----------------------------------------------------------------------
    # Leverage ratios
    # -----------------------------------------------------------------------

    # Debt-to-Equity = Total Debt / Shareholder Equity
    debt_to_equity = _safe_div(total_debt, shareholder_equity, round_digits=4)

    # Debt-to-Assets = Total Debt / Total Assets
    debt_to_assets = _safe_div(total_debt, total_assets, round_digits=4)

    # -----------------------------------------------------------------------
    # Pass-through market / valuation metrics
    # -----------------------------------------------------------------------
    pe_ratio       = financials.get("pe_ratio")
    eps            = financials.get("eps")
    beta           = financials.get("beta")
    market_cap     = financials.get("market_cap")
    free_cash_flow = financials.get("free_cash_flow")
    dividend_yield = financials.get("dividend_yield")

    kpis = {
        # Profitability
        "net_profit_margin": net_profit_margin,     # %
        "operating_margin": operating_margin,        # %
        "roe": roe,                                  # %
        "roa": roa,                                  # %
        # Efficiency
        "asset_turnover": asset_turnover,
        # Liquidity
        "current_ratio": current_ratio,
        # Leverage
        "debt_to_equity": debt_to_equity,
        "debt_to_assets": debt_to_assets,
        # Valuation
        "pe_ratio": pe_ratio,
        "eps": eps,
        "beta": beta,
        "market_cap": market_cap,
        "free_cash_flow": free_cash_flow,
        "dividend_yield": dividend_yield,
    }

    logger.debug("KPIs calculated for %s: %s", financials.get("ticker"), kpis)
    return kpis
