"""
backend/risk_engine/risk_analysis.py

Main Risk Intelligence pipeline for the Financial & Market Research Agent.

Orchestrates all four risk analyzers + hidden risk detector and computes
an overall risk level. Individual module failures degrade gracefully.

Pipeline:
  1. fetch financial statements (reuses data/ module)
  2. calculate KPIs (reuses core/ module)
  3. assess leverage risk
  4. assess liquidity risk
  5. assess earnings stability
  6. assess cash flow risk
  7. detect hidden risks
  8. compute overall risk level

Overall risk scoring:
  Weighted average of per-module risk scores (0–10), then bucketed:
    0–3   → low
    4–6   → moderate
    7–10  → high
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module weights for overall risk score
# ---------------------------------------------------------------------------
RISK_WEIGHTS = {
    "leverage":  0.30,
    "liquidity": 0.25,
    "earnings":  0.25,
    "cashflow":  0.20,
}

# String risk level → numeric score mapping
LEVEL_TO_SCORE: Dict[str, int] = {
    "low":      2,
    "moderate": 5,
    "high":     8,
    "critical": 10,
}


def analyze_company_risks(ticker: str) -> Dict[str, Any]:
    """
    Run the complete Risk Intelligence pipeline for the given ticker.

    Fetches financial data, runs all risk analysis sub-modules, and
    returns a structured risk report. Each sub-module failure is isolated —
    partial results are returned with an error log rather than a crash.

    Args:
        ticker (str): Validated uppercase stock symbol (e.g. 'AAPL').

    Returns:
        dict:
            ticker (str)
            overall_risk (str): 'low' | 'moderate' | 'high'
            overall_risk_score (float): Weighted 0–10 score
            leverage_risk (dict): From leverage_risk.assess_leverage_risk()
            liquidity_risk (dict): From liquidity_risk.assess_liquidity_risk()
            earnings_stability (dict): From earnings_stability.assess_earnings_stability()
            cashflow_risk (dict): From cashflow_risk.assess_cashflow_risk()
            hidden_risks (list[str]): From hidden_risks.detect_hidden_risks()
            analysis_status (str): 'complete' | 'partial'
            errors (list[str]): Non-fatal errors encountered

    Raises:
        RuntimeError: If financial data fetch fails completely.
    """
    errors: List[str] = []
    analysis_status = "complete"
    logger.info("=== Starting risk analysis for: %s ===", ticker)

    # -------------------------------------------------------------------
    # Step 1 & 2: Fetch financials + calculate KPIs
    # -------------------------------------------------------------------
    from backend.data.financials import fetch_financial_statements
    from backend.core.kpi_calculator import calculate_kpis

    try:
        financials = fetch_financial_statements(ticker)
    except Exception as exc:
        logger.error("Failed to fetch financials for risk analysis: %s", exc)
        raise RuntimeError(
            f"Cannot run risk analysis without financial data for '{ticker}': {exc}"
        ) from exc

    try:
        kpis = calculate_kpis(financials)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("KPI calculation failed for risk analysis: %s", exc)
        kpis = {}
        errors.append(f"KPI calculation failed: {exc}")
        analysis_status = "partial"

    # -------------------------------------------------------------------
    # Step 3: Leverage risk
    # -------------------------------------------------------------------
    from backend.risk_engine.leverage_risk import assess_leverage_risk
    try:
        leverage_risk_result = assess_leverage_risk(financials, kpis)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Leverage risk assessment failed: %s", exc)
        leverage_risk_result = _error_risk("leverage risk assessment failed")
        errors.append(f"Leverage risk error: {exc}")
        analysis_status = "partial"

    # -------------------------------------------------------------------
    # Step 4: Liquidity risk
    # -------------------------------------------------------------------
    from backend.risk_engine.liquidity_risk import assess_liquidity_risk
    try:
        liquidity_risk_result = assess_liquidity_risk(financials, kpis)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Liquidity risk assessment failed: %s", exc)
        liquidity_risk_result = _error_risk("liquidity risk assessment failed")
        errors.append(f"Liquidity risk error: {exc}")
        analysis_status = "partial"

    # -------------------------------------------------------------------
    # Step 5: Earnings stability
    # -------------------------------------------------------------------
    from backend.risk_engine.earnings_stability import assess_earnings_stability
    try:
        earnings_stability_result = assess_earnings_stability(ticker)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Earnings stability assessment failed: %s", exc)
        earnings_stability_result = {
            "stability_score": None,
            "classification": "error",
            "risk_level": "moderate",
            "flags": [f"assessment failed: {exc}"],
        }
        errors.append(f"Earnings stability error: {exc}")
        analysis_status = "partial"

    # -------------------------------------------------------------------
    # Step 6: Cash flow risk
    # -------------------------------------------------------------------
    from backend.risk_engine.cashflow_risk import assess_cashflow_risk
    try:
        cashflow_risk_result = assess_cashflow_risk(financials)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Cash flow risk assessment failed: %s", exc)
        cashflow_risk_result = _error_risk("cashflow risk assessment failed")
        errors.append(f"Cash flow risk error: {exc}")
        analysis_status = "partial"

    # -------------------------------------------------------------------
    # Step 7: Hidden risks
    # -------------------------------------------------------------------
    from backend.risk_engine.hidden_risks import detect_hidden_risks
    try:
        hidden_risks_list = detect_hidden_risks(financials, kpis)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Hidden risk detection failed: %s", exc)
        hidden_risks_list = [f"hidden risk detection failed: {exc}"]
        errors.append(f"Hidden risks error: {exc}")
        analysis_status = "partial"

    # -------------------------------------------------------------------
    # Step 8: Overall risk score (weighted average)
    # -------------------------------------------------------------------
    module_scores: Dict[str, Optional[float]] = {
        "leverage":  _level_to_score(leverage_risk_result.get("risk_level")),
        "liquidity": _level_to_score(liquidity_risk_result.get("risk_level")),
        "earnings":  _level_to_score(earnings_stability_result.get("risk_level")),
        "cashflow":  _level_to_score(cashflow_risk_result.get("risk_level")),
    }

    weighted_score = _compute_weighted_score(module_scores)
    overall_risk   = _score_to_level(weighted_score)

    # Add extra weight for combined hidden risks
    if len(hidden_risks_list) >= 3:
        overall_risk = _bump_risk(overall_risk)

    logger.info(
        "Risk analysis complete for %s | overall=%s (%.1f/10) | hidden=%d",
        ticker, overall_risk, weighted_score or 0, len(hidden_risks_list),
    )

    return {
        "ticker": ticker,
        "overall_risk": overall_risk,
        "overall_risk_score": round(weighted_score, 2) if weighted_score is not None else None,
        "leverage_risk": leverage_risk_result,
        "liquidity_risk": liquidity_risk_result,
        "earnings_stability": earnings_stability_result,
        "cashflow_risk": cashflow_risk_result,
        "hidden_risks": hidden_risks_list,
        "analysis_status": analysis_status,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _error_risk(msg: str) -> Dict[str, Any]:
    """Return a stub risk result for a failed module."""
    return {
        "risk_level": "moderate",
        "risk_score": 5,
        "details": msg,
        "flags": [msg],
    }


def _level_to_score(risk_level: Optional[str]) -> Optional[float]:
    """Convert a string risk level to numeric score for weighting."""
    return float(LEVEL_TO_SCORE.get(risk_level or "", 5))


def _compute_weighted_score(
    scores: Dict[str, Optional[float]],
) -> Optional[float]:
    """Compute weighted average of module risk scores."""
    total_weight = 0.0
    weighted_sum = 0.0
    for module, score in scores.items():
        if score is not None:
            w = RISK_WEIGHTS.get(module, 0.0)
            weighted_sum += score * w
            total_weight += w
    return (weighted_sum / total_weight) if total_weight > 0 else None


def _score_to_level(score: Optional[float]) -> str:
    """Convert a 0–10 numeric score to a risk level label."""
    if score is None:
        return "moderate"
    if score >= 7:
        return "high"
    if score >= 4:
        return "moderate"
    return "low"


def _bump_risk(level: str) -> str:
    """Bump risk level up by one grade if hidden risks are numerous."""
    if level == "low":
        return "moderate"
    if level == "moderate":
        return "high"
    return level   # Already 'high' — can't go higher
