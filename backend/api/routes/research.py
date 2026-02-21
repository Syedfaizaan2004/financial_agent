"""
backend/api/routes/research.py

Research API endpoint for the Financial & Market Research Agent.

Returns a comprehensive report combining:
  - Fundamental analysis (Phase 3)
  - Risk intelligence (Phase 4)
  - Peer comparison summary (Phase 5)
  - Recession scenario insights (Phase 6)

Endpoint:
    GET /research/{ticker}
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/research", tags=["Research"])


@router.get(
    "/{ticker}",
    summary="Company Research — Fundamentals + Risk + Peers + Scenario",
    description=(
        "Returns a full fundamental + risk + peer + scenario analysis report.\n\n"
        "**Fundamentals**: profitability, valuation, liquidity, leverage, growth, financial strength\n"
        "**Risk**: leverage, liquidity, earnings stability, cash flow, hidden risks\n"
        "**Peer Comparison**: positioning vs sector peers (valuation, profitability, growth)\n"
        "**Scenario Insights**: recession stress test on revenue, margins, and leverage\n\n"
        "Returns **503** if yfinance is not installed.\n"
        "Returns **404** if ticker data is unavailable.\n"
        "Returns **500** on unexpected analysis errors."
    ),
    response_description="Comprehensive multi-dimensional research report",
)
async def get_research(ticker: str) -> Dict[str, Any]:
    """
    GET /research/{ticker}

    Runs fundamentals → risk → peer comparison → scenario pipeline sequentially.
    Each step after fundamentals is non-fatal — partial results are returned
    with error notes rather than crashing the entire response.
    """
    canonical = ticker.upper().strip()
    logger.info("Research requested for ticker: %s", canonical)

    # -----------------------------------------------------------------------
    # Step 1: Fundamental analysis (Phase 3)
    # -----------------------------------------------------------------------
    try:
        from backend.core.financial_analyzer import analyze_company_fundamentals
        fundamentals = analyze_company_fundamentals(canonical)
    except RuntimeError as exc:
        error_msg = str(exc)
        if "yfinance" in error_msg.lower() and "install" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail=(
                    "Market data provider is not available. "
                    "Install yfinance with: pip install yfinance"
                ),
            ) from exc
        raise HTTPException(
            status_code=404,
            detail=(
                f"No financial data available for ticker '{canonical}'. "
                "Verify the ticker symbol is valid and publicly traded."
            ),
        ) from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Fundamental analysis failed for %s", canonical)
        raise HTTPException(
            status_code=500,
            detail=f"Fundamental analysis error: {type(exc).__name__}: {exc}",
        ) from exc

    # -----------------------------------------------------------------------
    # Step 2: Risk intelligence (Phase 4) — non-fatal
    # -----------------------------------------------------------------------
    risk_result: Dict[str, Any] = {}
    risk_error: str = ""
    try:
        from backend.risk_engine.risk_analysis import analyze_company_risks
        risk_result = analyze_company_risks(canonical)
    except RuntimeError as exc:
        logger.error("Risk analysis failed for %s: %s", canonical, exc)
        risk_error = str(exc)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Unexpected risk analysis error for %s: %s", canonical, exc)
        risk_error = f"{type(exc).__name__}: {exc}"

    # -----------------------------------------------------------------------
    # Step 3: Peer comparison summary (Phase 5) — non-fatal
    # -----------------------------------------------------------------------
    peer_comparison_result: Dict[str, Any] = {}
    try:
        from backend.core.peer_fetcher import get_peer_group
        from backend.core.peer_comparison import compare_with_peers
        peers = get_peer_group(canonical)
        if peers:
            peer_comparison_result = compare_with_peers(canonical, peers)
        else:
            peer_comparison_result = {
                "peer_group": [],
                "summary": ["No peer group defined for this ticker."],
            }
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Peer comparison unavailable for %s: %s", canonical, exc)
        peer_comparison_result = {
            "peer_group": [],
            "summary": [f"Peer comparison unavailable: {type(exc).__name__}"],
        }

    # -----------------------------------------------------------------------
    # Step 4: Scenario insights — recession baseline (Phase 6) — non-fatal
    # -----------------------------------------------------------------------
    scenario_result: Dict[str, Any] = {}
    try:
        from backend.risk_engine.scenario_engine import run_scenario_analysis
        scenario_result = run_scenario_analysis(canonical, "recession")
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Scenario analysis unavailable for %s: %s", canonical, exc)
        scenario_result = {
            "scenario": "recession",
            "risk_outlook": "scenario analysis unavailable",
            "summary": [],
        }

    # -----------------------------------------------------------------------
    # Step 5: Merge and return
    # -----------------------------------------------------------------------
    response: Dict[str, Any] = {
        # Identity
        "ticker": fundamentals.get("ticker"),
        "company_name": fundamentals.get("company_name"),
        "sector": fundamentals.get("sector"),
        "industry": fundamentals.get("industry"),

        # ---- Fundamental Analysis ----
        "profitability": fundamentals.get("profitability"),
        "valuation": fundamentals.get("valuation"),
        "efficiency": fundamentals.get("efficiency"),
        "liquidity": fundamentals.get("liquidity"),
        "leverage": fundamentals.get("leverage"),
        "growth": fundamentals.get("growth"),
        "financial_strength": fundamentals.get("financial_strength"),
        "raw_financials": fundamentals.get("raw_financials"),

        # ---- Risk Intelligence ----
        "risk": {
            "overall_risk": risk_result.get("overall_risk", "unavailable"),
            "overall_risk_score": risk_result.get("overall_risk_score"),
            "leverage_risk": risk_result.get("leverage_risk"),
            "liquidity_risk": risk_result.get("liquidity_risk"),
            "earnings_stability": {
                "score": risk_result.get("earnings_stability", {}).get("stability_score"),
                "classification": risk_result.get("earnings_stability", {}).get("classification"),
                "trend": risk_result.get("earnings_stability", {}).get("trend"),
                "risk_level": risk_result.get("earnings_stability", {}).get("risk_level"),
            } if risk_result.get("earnings_stability") else None,
            "cashflow_risk": risk_result.get("cashflow_risk"),
            "hidden_risks": risk_result.get("hidden_risks", []),
            "risk_analysis_status": risk_result.get(
                "analysis_status", "failed" if risk_error else "complete"
            ),
            "risk_errors": risk_result.get("errors", [risk_error] if risk_error else []),
        },

        # ---- Peer Comparison Summary ----
        "peer_comparison": {
            "peer_group": peer_comparison_result.get("peer_group", []),
            "summary": peer_comparison_result.get("summary", []),
            "valuation_comparison": peer_comparison_result.get("valuation_comparison", {}),
            "profitability_comparison": peer_comparison_result.get("profitability_comparison", {}),
            "growth_comparison": peer_comparison_result.get("growth_comparison", {}),
            "leverage_comparison": peer_comparison_result.get("leverage_comparison", {}),
        },

        # ---- Scenario Insights (recession baseline) ----
        "scenario_insights": {
            "scenario": scenario_result.get("scenario", "recession"),
            "risk_outlook": scenario_result.get("risk_outlook", ""),
            "revenue_growth_adjusted": (
                scenario_result.get("revenue_stress", {}).get("adjusted_growth")
            ),
            "margin_adjusted": (
                scenario_result.get("margin_stress", {}).get("adjusted_margin")
            ),
            "summary": scenario_result.get("summary", []),
        },

        # ---- Pipeline Metadata ----
        "analysis_status": fundamentals.get("analysis_status"),
        "data_quality_notes": fundamentals.get("data_quality_notes", []),
        "errors": fundamentals.get("errors", []),
    }

    logger.info(
        "Research complete for %s | fundamentals=%s | risk=%s | peers=%d | hidden=%d",
        canonical,
        response["analysis_status"],
        response["risk"]["overall_risk"],
        len(response["peer_comparison"]["peer_group"]),
        len(response["risk"]["hidden_risks"]),
    )
    return response
