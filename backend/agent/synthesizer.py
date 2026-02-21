"""
backend/agent/synthesizer.py

Research insight synthesizer for the AI Research Agent.

Combines raw tool outputs into a structured, readable insight report.
All synthesis is rule-based — no LLM required.

Output format:
    {
        "ticker": str,
        "strengths": list[str],
        "risks": list[str],
        "opportunities": list[str],
        "outlook": str,         # 'positive' | 'moderately_positive' | 'neutral' | 'cautious' | 'negative'
        "forecast_trend": str,  # 'upward' | 'downward' | 'neutral' | 'unavailable'
        "key_metrics": dict,    # curated snapshot of most important numbers
        "scenario_impact": str, # one-line scenario description if available
        "peer_positioning": str,# one-line peer summary if available
        "confidence": float,    # composite confidence score 0.0–1.0
        "contradictions": list, # detected conflicting signals
        "uncertainties": list,  # uncertainty / data quality flags
    }
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def synthesize_insights(
    ticker: str,
    fundamentals: Optional[Dict[str, Any]] = None,
    risk:         Optional[Dict[str, Any]] = None,
    forecast:     Optional[Dict[str, Any]] = None,
    peer:         Optional[Dict[str, Any]] = None,
    scenario:     Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Synthesize tool outputs into a concise structured insight report.

    Each parameter is optional — synthesis degrades gracefully if a tool
    was not called or failed. All inputs are raw `data` dicts from the
    tool envelope (not the full envelope including ok/error).

    Args:
        ticker (str): Target ticker symbol.
        fundamentals (dict | None): Output of get_fundamentals tool data.
        risk         (dict | None): Output of get_risk_analysis tool data.
        forecast     (dict | None): Output of get_forecast tool data.
        peer         (dict | None): Output of get_peer_comparison tool data.
        scenario     (dict | None): Output of run_scenario tool data.

    Returns:
        dict: Structured insight report (see module docstring for schema).
    """
    strengths:     List[str] = []
    risks:         List[str] = []
    opportunities: List[str] = []

    # -----------------------------------------------------------------------
    # Fundamentals → strengths / risks
    # -----------------------------------------------------------------------
    if fundamentals:
        fin_strength = fundamentals.get("financial_strength") or {}
        strengths.extend(fin_strength.get("strengths", []))
        risks.extend(fin_strength.get("weaknesses", []))

        # Growth opportunities
        growth = fundamentals.get("growth") or {}
        rev_trend = growth.get("revenue_growth_trend", "")
        if rev_trend == "high_growth":
            opportunities.append("high revenue growth trajectory — significant expansion opportunity")
        elif rev_trend == "moderate_growth":
            opportunities.append("steady revenue growth — sustaining organic expansion")

    # -----------------------------------------------------------------------
    # Risk → risks
    # -----------------------------------------------------------------------
    if risk:
        overall_risk = risk.get("overall_risk", "")
        if overall_risk == "high":
            risks.append(f"overall risk level is HIGH — multiple risk dimensions elevated")
        elif overall_risk == "moderate":
            risks.append("moderate overall risk — several areas warrant monitoring")

        hidden = risk.get("hidden_risks", [])
        for h in hidden[:3]:   # Cap at 3 hidden risks in synthesis
            risks.append(f"hidden risk: {h}")

        leverage_r = (risk.get("leverage_risk") or {}).get("risk_level", "")
        if leverage_r in ("high", "critical"):
            risks.append("elevated leverage risk — debt burden is significant")

    # -----------------------------------------------------------------------
    # Peer comparison → opportunities / risks
    # -----------------------------------------------------------------------
    peer_positioning_line = ""
    if peer:
        summary = peer.get("summary", [])
        if summary:
            peer_positioning_line = summary[0]   # Most salient insight
        for line in summary:
            if "undervalued" in line or "above_peers" in line or "outpacing" in line:
                opportunities.append(f"peer advantage: {line}")
            elif "below" in line or "lagging" in line or "higher leverage" in line:
                risks.append(f"peer risk: {line}")

    # -----------------------------------------------------------------------
    # Forecast → forecast_trend
    # -----------------------------------------------------------------------
    forecast_trend = "unavailable"
    if forecast and forecast.get("supported", True):
        prob_up = forecast.get("prob_up") or forecast.get("ensemble_prob_up")
        if prob_up is not None:
            forecast_trend = "upward" if prob_up >= 0.5 else "downward"
            if forecast_trend == "upward" and prob_up >= 0.65:
                opportunities.append(
                    f"model forecast: high-confidence upward movement (prob_up={prob_up:.0%})"
                )
            elif forecast_trend == "downward" and prob_up < 0.40:
                risks.append(
                    f"model forecast: downward bias (prob_up={prob_up:.0%})"
                )

    # -----------------------------------------------------------------------
    # Scenario → scenario_impact
    # -----------------------------------------------------------------------
    scenario_impact_line = ""
    if scenario:
        scenario_impact_line = scenario.get("risk_outlook", "")
        scenario_summary = scenario.get("summary", [])
        if scenario_summary:
            risks.append(f"recession scenario: {scenario_summary[0]}")

    # -----------------------------------------------------------------------
    # Key metrics snapshot
    # -----------------------------------------------------------------------
    key_metrics: Dict[str, Any] = {}
    if fundamentals:
        prof = fundamentals.get("profitability") or {}
        val  = fundamentals.get("valuation") or {}
        key_metrics.update({
            "net_margin":  prof.get("net_profit_margin"),
            "roe":         prof.get("roe"),
            "pe_ratio":    val.get("pe_ratio"),
            "market_cap":  val.get("market_cap"),
        })
    if risk:
        key_metrics["overall_risk"] = risk.get("overall_risk")
        key_metrics["risk_score"]   = risk.get("overall_risk_score")

    # -----------------------------------------------------------------------
    # Overall outlook (rule-based scoring)
    # -----------------------------------------------------------------------
    outlook = _compute_outlook(
        risk_level=risk.get("overall_risk") if risk else None,
        forecast_trend=forecast_trend,
        strengths=strengths,
        risks=risks,
    )

    # De-duplicate
    strengths     = _dedup(strengths)
    risks         = _dedup(risks)
    opportunities = _dedup(opportunities)

    # -----------------------------------------------------------------------
    # Confidence, contradictions, uncertainties from utils layer
    # -----------------------------------------------------------------------
    analysis_data = {
        "forecast":     forecast,
        "fundamentals": fundamentals,
        "risk":         risk,
        "scenario":     scenario,
        "insights":     {
            "outlook": outlook,
            "strengths": strengths,
            "risks": risks,
        },
        "peer_comparison": peer,
    }

    confidence    = 0.60
    contradictions: List[Dict[str, Any]] = []
    uncertainties:  List[Dict[str, Any]] = []

    try:
        from backend.utils.confidence_score import calculate_confidence
        confidence = calculate_confidence(analysis_data)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("[synthesizer] Confidence scoring failed: %s", exc)

    try:
        from backend.utils.contradiction_detector import detect_contradictions
        contradictions = detect_contradictions(analysis_data)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("[synthesizer] Contradiction detection failed: %s", exc)

    try:
        from backend.utils.uncertainty_flags import identify_uncertainties
        uncertainties = identify_uncertainties(analysis_data)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("[synthesizer] Uncertainty flagging failed: %s", exc)

    result = {
        "ticker": ticker,
        "strengths": strengths[:6],
        "risks": risks[:6],
        "opportunities": opportunities[:4],
        "outlook": outlook,
        "forecast_trend": forecast_trend,
        "key_metrics": {k: v for k, v in key_metrics.items() if v is not None},
        "scenario_impact": scenario_impact_line,
        "peer_positioning": peer_positioning_line,
        "confidence": confidence,
        "contradictions": contradictions,
        "uncertainties": uncertainties,
    }

    logger.info(
        "Synthesis for %s: outlook=%s | conf=%.2f | contradictions=%d | uncertainties=%d",
        ticker, outlook, confidence,
        len(contradictions), len(uncertainties),
    )
    return result


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _compute_outlook(
    risk_level: Optional[str],
    forecast_trend: str,
    strengths: List[str],
    risks: List[str],
) -> str:
    score = 0
    # Risk level
    if risk_level == "low":
        score += 2
    elif risk_level == "moderate":
        score += 0
    elif risk_level == "high":
        score -= 2
    # Forecast
    if forecast_trend == "upward":
        score += 2
    elif forecast_trend == "downward":
        score -= 2
    # Strengths vs risks balance
    score += min(len(strengths), 3) - min(len(risks), 3)

    if   score >= 4:  return "positive"
    elif score >= 2:  return "moderately_positive"
    elif score >= 0:  return "neutral"
    elif score >= -2: return "cautious"
    else:             return "negative"


def _dedup(items: List[str]) -> List[str]:
    """Remove duplicates while preserving order."""
    seen = set()
    result = []
    for item in items:
        key = item[:60].lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result
