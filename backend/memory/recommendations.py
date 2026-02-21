"""
backend/memory/recommendations.py

Next-analysis recommendation engine.

Generates context-aware suggestions for follow-up research based on:
  - What analyses have already been run
  - User preferences (risk profile, time horizon)
  - Signals in the current analysis output

All recommendations are deterministic and grounded in actual data signals.
No LLM or randomness is used.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Recommendation templates (populated with dynamic data)
# ---------------------------------------------------------------------------

_REC_PEER_COMPARE   = "Compare {ticker} with sector peers for relative valuation insight."
_REC_RECESSION      = "Run a recession scenario on {ticker} to assess macro resilience."
_REC_INFLATION      = "Analyse {ticker} under a high inflation scenario — margin compression risk."
_REC_RATE_HIKE      = "Assess {ticker} under a rate hike scenario — leverage sensitivity."
_REC_LEVERAGE       = "Deep-dive into {ticker}'s leverage trends — D/E ratio warrants monitoring."
_REC_DEEP_RESEARCH  = "Run a full deep-research on {ticker} for a comprehensive picture."
_REC_FORECAST       = "Get a quantitative directional forecast for {ticker}."
_REC_EARNINGS_STAB  = "Review {ticker}'s earnings stability over multiple years."
_REC_GROWTH_OUTLOOK = "Analyse {ticker}'s revenue growth trajectory for long-term outlook."
_REC_FCF_QUALITY    = "Examine {ticker}'s free cash flow quality and cash conversion."


def suggest_next_analysis(
    prefs: Dict[str, Any],
    data: Dict[str, Any],
) -> List[str]:
    """
    Generate a list of actionable follow-up research suggestions.

    Combines:
      1. Rules based on what's missing from the current response
      2. User preference alignment
      3. Detected signals (risk level, leverage, contradictions)

    Args:
        prefs (dict): User preferences from memory store.
        data (dict): Current agent response / workflow output.

    Returns:
        list[str]: Up to 4 prioritised suggestion strings.
    """
    ticker    = (data.get("ticker") or "").upper() or "this company"
    workflow  = data.get("workflow", "")
    insights  = data.get("insights") or {}
    risk      = (data.get("raw_data") or {}).get("risk") or {}
    peer      = (data.get("raw_data") or {}).get("peer_comparison") or \
                 data.get("peer_comparison") or {}

    risk_profile  = (prefs.get("risk_profile") or "moderate").lower()
    time_horizon  = (prefs.get("time_horizon")  or "medium").lower()
    pref_metrics  = [m.lower() for m in (prefs.get("preferred_metrics") or [])]

    suggestions: List[str] = []

    # --- Gap-based recommendations (what hasn't been run yet) ---
    raw_data = data.get("raw_data") or {}

    if not peer.get("peer_group") and "compare" not in workflow:
        suggestions.append(_REC_PEER_COMPARE.format(ticker=ticker))

    if not raw_data.get("scenario") and "scenario" not in workflow:
        suggestions.append(_REC_RECESSION.format(ticker=ticker))

    if not raw_data.get("forecast") and "forecast" not in workflow:
        suggestions.append(_REC_FORECAST.format(ticker=ticker))

    if workflow == "quick_research":
        suggestions.append(_REC_DEEP_RESEARCH.format(ticker=ticker))

    # --- Risk signal-based recommendations ---
    overall_risk = risk.get("overall_risk", "")
    lev_risk     = (risk.get("leverage_risk") or {}).get("risk_level", "")
    earn_cls     = (risk.get("earnings_stability") or {}).get("classification", "")

    if overall_risk == "high":
        if _REC_RECESSION.format(ticker=ticker) not in suggestions:
            suggestions.append(_REC_RECESSION.format(ticker=ticker))

    if lev_risk in ("high", "critical"):
        suggestions.append(_REC_LEVERAGE.format(ticker=ticker))
        if _REC_RATE_HIKE.format(ticker=ticker) not in suggestions:
            suggestions.append(_REC_RATE_HIKE.format(ticker=ticker))

    if earn_cls in ("volatile", "highly_volatile", "insufficient_data"):
        suggestions.append(_REC_EARNINGS_STAB.format(ticker=ticker))

    # --- Preference-based recommendations ---
    if risk_profile == "conservative":
        # Extra scenario coverage for risk-averse users
        if _REC_INFLATION.format(ticker=ticker) not in suggestions:
            suggestions.append(_REC_INFLATION.format(ticker=ticker))

    elif risk_profile == "aggressive":
        # Growth-focused
        if _REC_GROWTH_OUTLOOK.format(ticker=ticker) not in suggestions:
            suggestions.append(_REC_GROWTH_OUTLOOK.format(ticker=ticker))

    if time_horizon == "short":
        if _REC_FORECAST.format(ticker=ticker) not in suggestions:
            suggestions.append(_REC_FORECAST.format(ticker=ticker))

    for m in pref_metrics:
        if "fcf" in m or "cash" in m:
            if _REC_FCF_QUALITY.format(ticker=ticker) not in suggestions:
                suggestions.append(_REC_FCF_QUALITY.format(ticker=ticker))
            break

    # De-duplicate and cap at 4
    seen, out = set(), []
    for s in suggestions:
        if s not in seen:
            seen.add(s)
            out.append(s)
        if len(out) == 4:
            break

    logger.info("[recommendations] %d suggestion(s) for ticker=%s", len(out), ticker)
    return out
