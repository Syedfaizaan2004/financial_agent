"""
backend/data/financials.py

Financial data fetch module for the Financial & Market Research Agent.

Fetches income statement, balance sheet, cash flow, and key statistics
from yfinance and returns a clean, structured dictionary of financial
data ready for KPI calculation and analysis.

Data source: yfinance (Yahoo Finance)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Safe value extractor
# ---------------------------------------------------------------------------

def _safe_get(data: Any, *keys: str, default: Optional[float] = None) -> Optional[float]:
    """
    Safely extract a numeric value from a nested dict / DataFrame cell.

    Args:
        data: Source object (dict, DataFrame, Series, or scalar).
        *keys: Key sequence to traverse.
        default: Value to return when the key is missing or value is None/NaN.

    Returns:
        float | None: Extracted value or default.
    """
    import pandas as pd

    obj = data
    for key in keys:
        if obj is None:
            return default
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif hasattr(obj, "get"):
            obj = obj.get(key)
        else:
            return default

    if obj is None:
        return default
    try:
        val = float(obj)
        return default if pd.isna(val) else val
    except (TypeError, ValueError):
        return default


def _first_row_value(df: Any, label: str) -> Optional[float]:
    """
    Extract the most recent (first column) value for a given row label
    from a yfinance-style transposed financial statement DataFrame.

    Args:
        df: pandas DataFrame (index = metric labels).
        label: Row label to look up (case-insensitive partial match).

    Returns:
        float | None
    """
    import pandas as pd

    if df is None or df.empty:
        return None

    # Try exact match first, then case-insensitive partial match
    for idx in df.index:
        if str(idx).lower() == label.lower():
            val = df.loc[idx].iloc[0]
            try:
                v = float(val)
                return None if pd.isna(v) else v
            except (TypeError, ValueError):
                return None

    for idx in df.index:
        if label.lower() in str(idx).lower():
            val = df.loc[idx].iloc[0]
            try:
                v = float(val)
                return None if pd.isna(v) else v
            except (TypeError, ValueError):
                return None

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_financial_statements(ticker: str) -> Dict[str, Any]:
    """
    Fetch and structure financial statements for the given ticker.

    Retrieves income statement, balance sheet, cash flow statement, and
    key statistics from Yahoo Finance (via yfinance) and returns a clean
    dictionary. Missing or unavailable fields are set to None — callers
    must handle None values safely.

    Args:
        ticker (str): Validated uppercase stock symbol (e.g. 'AAPL').

    Returns:
        dict: Structured financial data with keys:
            ticker, revenue, net_income, operating_income,
            total_assets, total_debt, shareholder_equity,
            current_assets, current_liabilities, free_cash_flow,
            market_cap, pe_ratio, eps, beta, dividend_yield,
            data_source, data_quality_notes

    Raises:
        RuntimeError: If yfinance is not installed.
        ValueError: If ticker is invalid or no data is returned.
    """
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError(
            "yfinance is required for financial data fetching. "
            "Install it with: pip install yfinance"
        ) from exc

    logger.info("Fetching financial statements for: %s", ticker)

    stock = yf.Ticker(ticker)
    data_quality_notes: list[str] = []

    # --- Income Statement ---
    try:
        income_stmt = stock.financials          # annual, rows = metrics, cols = dates
    except Exception as exc:
        logger.warning("Income statement unavailable for %s: %s", ticker, exc)
        income_stmt = None

    # --- Balance Sheet ---
    try:
        balance_sheet = stock.balance_sheet
    except Exception as exc:
        logger.warning("Balance sheet unavailable for %s: %s", ticker, exc)
        balance_sheet = None

    # --- Cash Flow ---
    try:
        cash_flow = stock.cashflow
    except Exception as exc:
        logger.warning("Cash flow unavailable for %s: %s", ticker, exc)
        cash_flow = None

    # --- Key Stats / Info ---
    try:
        info = stock.info or {}
    except Exception as exc:
        logger.warning("Info unavailable for %s: %s", ticker, exc)
        info = {}

    # --- Extract revenue (Total Revenue) ---
    revenue = _first_row_value(income_stmt, "Total Revenue")
    if revenue is None:
        revenue = _first_row_value(income_stmt, "Revenue")
        if revenue is None:
            data_quality_notes.append("revenue not found in income statement")

    # --- Net Income ---
    net_income = _first_row_value(income_stmt, "Net Income")
    if net_income is None:
        net_income = _first_row_value(income_stmt, "Net Income Common Stockholders")
        if net_income is None:
            data_quality_notes.append("net_income not found")

    # --- Operating Income ---
    operating_income = _first_row_value(income_stmt, "Operating Income")
    if operating_income is None:
        operating_income = _first_row_value(income_stmt, "EBIT")
        if operating_income is None:
            data_quality_notes.append("operating_income not found")

    # --- Total Assets ---
    total_assets = _first_row_value(balance_sheet, "Total Assets")
    if total_assets is None:
        data_quality_notes.append("total_assets not found")

    # --- Total Debt ---
    total_debt = _first_row_value(balance_sheet, "Total Debt")
    if total_debt is None:
        total_debt = _first_row_value(balance_sheet, "Long Term Debt")
        if total_debt is None:
            data_quality_notes.append("total_debt not found")

    # --- Shareholder Equity ---
    shareholder_equity = _first_row_value(balance_sheet, "Stockholders Equity")
    if shareholder_equity is None:
        shareholder_equity = _first_row_value(balance_sheet, "Total Equity Gross Minority Interest")
        if shareholder_equity is None:
            data_quality_notes.append("shareholder_equity not found")

    # --- Current Assets & Liabilities ---
    current_assets = _first_row_value(balance_sheet, "Current Assets")
    if current_assets is None:
        current_assets = _first_row_value(balance_sheet, "Total Current Assets")
        if current_assets is None:
            data_quality_notes.append("current_assets not found")

    current_liabilities = _first_row_value(balance_sheet, "Current Liabilities")
    if current_liabilities is None:
        current_liabilities = _first_row_value(balance_sheet, "Total Current Liabilities")
        if current_liabilities is None:
            data_quality_notes.append("current_liabilities not found")

    # --- Free Cash Flow ---
    free_cash_flow = _first_row_value(cash_flow, "Free Cash Flow")
    if free_cash_flow is None:
        # Derive: Operating CF - CapEx
        operating_cf = _first_row_value(cash_flow, "Operating Cash Flow")
        capex = _first_row_value(cash_flow, "Capital Expenditure")
        if operating_cf is not None and capex is not None:
            free_cash_flow = operating_cf - abs(capex)
        else:
            data_quality_notes.append("free_cash_flow could not be computed")

    # --- Market / Valuation data from info dict ---
    market_cap = _safe_get(info, "marketCap")
    pe_ratio = _safe_get(info, "trailingPE")
    eps = _safe_get(info, "trailingEps")
    beta = _safe_get(info, "beta")
    dividend_yield = _safe_get(info, "dividendYield")
    company_name = info.get("longName") or info.get("shortName") or ticker
    sector = info.get("sector", "Unknown")
    industry = info.get("industry", "Unknown")

    if data_quality_notes:
        logger.warning(
            "Data quality issues for %s: %s",
            ticker, "; ".join(data_quality_notes),
        )
    else:
        logger.info("Financial statements fetched successfully for %s", ticker)

    return {
        "ticker": ticker,
        "company_name": company_name,
        "sector": sector,
        "industry": industry,
        # Income statement
        "revenue": revenue,
        "net_income": net_income,
        "operating_income": operating_income,
        # Balance sheet
        "total_assets": total_assets,
        "total_debt": total_debt,
        "shareholder_equity": shareholder_equity,
        "current_assets": current_assets,
        "current_liabilities": current_liabilities,
        # Cash flow
        "free_cash_flow": free_cash_flow,
        # Valuation / market data
        "market_cap": market_cap,
        "pe_ratio": pe_ratio,
        "eps": eps,
        "beta": beta,
        "dividend_yield": dividend_yield,
        # Metadata
        "data_source": "yfinance",
        "data_quality_notes": data_quality_notes,
    }
