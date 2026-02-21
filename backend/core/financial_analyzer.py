"""
backend/core/financial_analyzer.py

Main financial analysis pipeline for the Financial & Market Research Agent.

Orchestrates the full fundamental analysis workflow:
  1. Fetch financial statements (yfinance)
  2. Calculate KPIs (ratios)
  3. Analyze growth (YoY revenue & earnings)
  4. Evaluate financial strength (strengths / weaknesses)

Exposes a single entry-point function: analyze_company_fundamentals()
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def analyze_company_fundamentals(ticker: str) -> Dict[str, Any]:
    """
    Run the complete fundamental analysis pipeline for a given ticker.

    Calls each analysis sub-module in sequence, collecting their outputs
    into a single structured response. Individual module failures are
    caught and reported as partial results rather than crashing the pipeline.

    Args:
        ticker (str): Validated uppercase stock symbol (e.g. 'AAPL').

    Returns:
        dict: Structured fundamental analysis report containing:
            ticker (str)
            company_name (str)
            sector (str)
            industry (str)
            profitability (dict): KPI ratios (margins, ROE, ROA, etc.)
            valuation (dict): PE ratio, EPS, market cap, beta
            liquidity (dict): current_ratio
            leverage (dict): debt_to_equity, debt_to_assets
            growth (dict): YoY growth rates, trend labels
            financial_strength (dict): strengths list, weaknesses list, score
            raw_financials (dict): Underlying financial statement values
            analysis_status (str): 'complete' | 'partial' | 'failed'
            errors (list[str]): Any non-fatal errors encountered

    Raises:
        RuntimeError: Only if financials fetch fails completely.
    """
    errors: list[str] = []
    analysis_status = "complete"

    # -----------------------------------------------------------------------
    # Step 1: Fetch financial statements
    # -----------------------------------------------------------------------
    logger.info("=== Starting fundamental analysis for: %s ===", ticker)

    from backend.data.financials import fetch_financial_statements
    try:
        financials = fetch_financial_statements(ticker)
    except Exception as exc:
        logger.error("Failed to fetch financials for %s: %s", ticker, exc)
        raise RuntimeError(
            f"Could not fetch financial data for '{ticker}': {exc}"
        ) from exc

    # -----------------------------------------------------------------------
    # Step 2: Calculate KPIs
    # -----------------------------------------------------------------------
    from backend.core.kpi_calculator import calculate_kpis
    try:
        kpis = calculate_kpis(financials)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("KPI calculation failed for %s: %s", ticker, exc)
        kpis = {}
        errors.append(f"KPI calculation error: {exc}")
        analysis_status = "partial"

    # -----------------------------------------------------------------------
    # Step 3: Analyze growth (requires separate yfinance call for multi-year data)
    # -----------------------------------------------------------------------
    from backend.core.growth_analysis import analyze_growth
    try:
        growth = analyze_growth(ticker)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Growth analysis failed for %s: %s", ticker, exc)
        growth = {
            "revenue_growth_yoy": None,
            "earnings_growth_yoy": None,
            "revenue_growth_trend": "unknown",
            "earnings_growth_trend": "unknown",
            "avg_revenue_growth": None,
            "years_analyzed": 0,
        }
        errors.append(f"Growth analysis error: {exc}")
        analysis_status = "partial"

    # -----------------------------------------------------------------------
    # Step 4: Evaluate financial strength
    # -----------------------------------------------------------------------
    from backend.core.financial_strength import evaluate_financial_strength
    try:
        strength = evaluate_financial_strength(kpis)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Strength evaluation failed for %s: %s", ticker, exc)
        strength = {"strengths": [], "weaknesses": [], "overall_score": None, "score_rationale": "evaluation failed"}
        errors.append(f"Strength evaluation error: {exc}")
        analysis_status = "partial"

    # -----------------------------------------------------------------------
    # Step 5: Compose structured output
    # -----------------------------------------------------------------------
    logger.info(
        "Fundamental analysis complete for %s | status=%s | score=%s",
        ticker, analysis_status, strength.get("overall_score"),
    )

    return {
        # Identity
        "ticker": ticker,
        "company_name": financials.get("company_name", ticker),
        "sector": financials.get("sector", "Unknown"),
        "industry": financials.get("industry", "Unknown"),

        # Profitability metrics
        "profitability": {
            "net_profit_margin": kpis.get("net_profit_margin"),     # %
            "operating_margin": kpis.get("operating_margin"),        # %
            "roe": kpis.get("roe"),                                   # %
            "roa": kpis.get("roa"),                                   # %
        },

        # Valuation metrics
        "valuation": {
            "pe_ratio": kpis.get("pe_ratio"),
            "eps": kpis.get("eps"),
            "market_cap": kpis.get("market_cap"),
            "beta": kpis.get("beta"),
            "dividend_yield": kpis.get("dividend_yield"),
        },

        # Efficiency metric
        "efficiency": {
            "asset_turnover": kpis.get("asset_turnover"),
            "free_cash_flow": kpis.get("free_cash_flow"),
        },

        # Liquidity
        "liquidity": {
            "current_ratio": kpis.get("current_ratio"),
        },

        # Leverage
        "leverage": {
            "debt_to_equity": kpis.get("debt_to_equity"),
            "debt_to_assets": kpis.get("debt_to_assets"),
        },

        # Growth
        "growth": {
            "revenue_growth_yoy": growth.get("revenue_growth_yoy"),          # %
            "earnings_growth_yoy": growth.get("earnings_growth_yoy"),         # %
            "revenue_growth_trend": growth.get("revenue_growth_trend"),
            "earnings_growth_trend": growth.get("earnings_growth_trend"),
            "avg_revenue_growth": growth.get("avg_revenue_growth"),           # %
            "years_analyzed": growth.get("years_analyzed", 0),
        },

        # Financial strength summary
        "financial_strength": {
            "strengths": strength.get("strengths", []),
            "weaknesses": strength.get("weaknesses", []),
            "overall_score": strength.get("overall_score"),
            "score_rationale": strength.get("score_rationale", ""),
        },

        # Raw financials for transparency / downstream use
        "raw_financials": {
            "revenue": financials.get("revenue"),
            "net_income": financials.get("net_income"),
            "operating_income": financials.get("operating_income"),
            "total_assets": financials.get("total_assets"),
            "total_debt": financials.get("total_debt"),
            "shareholder_equity": financials.get("shareholder_equity"),
            "current_assets": financials.get("current_assets"),
            "current_liabilities": financials.get("current_liabilities"),
            "free_cash_flow": financials.get("free_cash_flow"),
        },

        # Pipeline metadata
        "analysis_status": analysis_status,
        "data_quality_notes": financials.get("data_quality_notes", []),
        "errors": errors,
    }
