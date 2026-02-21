"""
backend/memory/personalization.py

Personalization adapter for the AI Research Agent.

Adjusts synthesized research output based on a user's stored preferences.
All transformations are deterministic and non-destructive — original data
is always preserved; only the presentation priority and notes are changed.

Preference dimensions:
    risk_profile    — conservative | moderate | aggressive
    time_horizon    — short | medium | long
    preferred_metrics — list of metric strings (e.g. ['ROE', 'FCF', 'margins'])
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_user_preferences(
    data: Dict[str, Any],
    prefs: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Adapt an agent research output to match user preferences.

    Adds a 'personalized_notes' list and re-orders 'strengths' / 'risks'
    based on the user's risk profile and time horizon. Does NOT remove
    or replace any existing analysis data.

    Args:
        data (dict): Full agent response dict (with 'insights' key).
        prefs (dict): User preferences from the memory system.

    Returns:
        dict: Enhanced data dict with 'personalized_notes' added to insights,
              and risk/strength ordering adjusted per user profile.
    """
    if not prefs:
        return data

    insights = data.get("insights") or {}
    risk_profile  = prefs.get("risk_profile", "moderate")
    time_horizon  = prefs.get("time_horizon", "medium")
    pref_metrics  = [m.lower() for m in (prefs.get("preferred_metrics") or [])]
    pref_sectors  = prefs.get("preferred_sectors") or []

    notes: List[str] = []

    # --- Risk profile adaptation ---
    notes.extend(_apply_risk_profile(insights, risk_profile))

    # --- Time horizon adaptation ---
    notes.extend(_apply_time_horizon(insights, time_horizon))

    # --- Preferred metrics highlights ---
    notes.extend(_apply_preferred_metrics(data, pref_metrics))

    # --- Reorder insights lists to match profile ---
    enhanced_insights = dict(insights)
    enhanced_insights = _reorder_for_profile(enhanced_insights, risk_profile, time_horizon)
    enhanced_insights["personalized_notes"] = notes

    return {**data, "insights": enhanced_insights}


# ---------------------------------------------------------------------------
# Adaptation logic
# ---------------------------------------------------------------------------

def _apply_risk_profile(
    insights: Dict[str, Any], risk_profile: str
) -> List[str]:
    """Generate personalized notes based on risk profile."""
    notes = []
    risks    = insights.get("risks", [])
    strengths = insights.get("strengths", [])
    outlook  = insights.get("outlook", "neutral")
    overall_risk = (insights.get("key_metrics") or {}).get("overall_risk", "")

    if risk_profile == "conservative":
        if overall_risk == "high":
            notes.append(
                "⚠️ Based on your conservative profile, the HIGH risk rating warrants caution — "
                "consider reviewing risk factors before investing."
            )
        elif risks:
            notes.append(
                "Based on your conservative profile, risks are highlighted first — "
                "review risk factors before considering upside."
            )
        if outlook in ("positive", "moderately_positive") and overall_risk in ("moderate", "high"):
            notes.append(
                "Although outlook is positive, your conservative preference suggests "
                "waiting for stronger risk confirmation."
            )

    elif risk_profile == "aggressive":
        if strengths:
            notes.append(
                "Based on your aggressive profile, growth and upside signals are "
                "prioritised in this analysis."
            )
        fc_trend = insights.get("forecast_trend", "")
        if fc_trend == "upward":
            notes.append(
                "Quantitative model signals upward price momentum — aligned with "
                "your higher risk tolerance."
            )

    else:  # moderate
        notes.append(
            "Analysis is presented with balanced risk-reward framing, "
            "matching your moderate risk profile."
        )

    return notes


def _apply_time_horizon(
    insights: Dict[str, Any], time_horizon: str
) -> List[str]:
    """Generate personalized notes based on time horizon."""
    notes = []
    fc_trend = insights.get("forecast_trend", "unavailable")

    if time_horizon == "short":
        notes.append(
            "Short-term focus: near-term price direction and volatility signals are most relevant."
        )
        if fc_trend == "downward":
            notes.append(
                "Short-term model signals a downward bias — caution warranted for near-term entry."
            )
        elif fc_trend == "upward":
            notes.append(
                "Short-term model signals an upward bias — may support tactical positioning."
            )

    elif time_horizon == "long":
        notes.append(
            "Long-term focus: fundamental strength, growth trajectory, and earnings stability "
            "are the primary drivers of value."
        )
        if "high revenue growth" in " ".join(insights.get("strengths", [])):
            notes.append(
                "Strong revenue growth trajectory aligns well with your long-term investment horizon."
            )

    else:  # medium
        notes.append(
            "Medium-term focus: balancing fundamental quality with market momentum signals."
        )

    return notes


def _apply_preferred_metrics(
    data: Dict[str, Any], pref_metrics: List[str]
) -> List[str]:
    """Highlight facts about the user's preferred financial metrics."""
    notes = []
    fundamentals = data.get("raw_data", {}).get("fundamentals") or \
                   data.get("fundamentals") or {}
    insights     = data.get("insights") or {}
    km           = insights.get("key_metrics") or {}
    prof         = fundamentals.get("profitability") or {}
    eff          = fundamentals.get("efficiency")    or {}

    for metric in pref_metrics:
        if "roe" in metric:
            roe = prof.get("roe") or km.get("roe")
            if roe is not None:
                quality = "strong" if roe > 20 else "moderate" if roe > 10 else "weak"
                notes.append(f"ROE is {quality} at {roe:.1f}% — matches your preferred focus on efficiency.")
            else:
                notes.append("ROE data unavailable for this ticker — efficiency analysis is limited.")

        elif "fcf" in metric or "cash" in metric:
            fcf = eff.get("free_cash_flow")
            if fcf is not None:
                quality = "positive" if fcf > 0 else "negative"
                notes.append(
                    f"Free cash flow is {quality} ({fcf:,.0f}) — relevant to your "
                    "cash generation preference."
                )
            else:
                notes.append("Free cash flow data unavailable — cash quality analysis limited.")

        elif "margin" in metric:
            nm = prof.get("net_profit_margin") or km.get("net_margin")
            if nm is not None:
                quality = "strong" if nm > 15 else "moderate" if nm > 5 else "thin"
                notes.append(f"Net margin is {quality} at {nm:.1f}% — aligned with your margin focus.")

        elif "growth" in metric:
            growth = (fundamentals.get("growth") or {}).get("revenue_growth_yoy")
            if growth is not None:
                notes.append(f"Revenue growth is {growth:.1f}% YoY — matches your growth metric preference.")

    return notes


def _reorder_for_profile(
    insights: Dict[str, Any], risk_profile: str, time_horizon: str
) -> Dict[str, Any]:
    """
    Re-order strengths/risks lists based on user profile.

    Conservative: risks first in the risks list (already natural order).
    Aggressive: opportunities + strengths given more prominence.
    Short horizon: no reorder (existing order is fine).
    """
    if risk_profile == "aggressive":
        # Move opportunities to the front — most relevant for growth seekers
        opportunities = insights.get("opportunities", [])
        strengths     = insights.get("strengths", [])
        # Merge opp into strengths for aggressive view (deduped)
        merged = _dedup(opportunities + strengths)
        insights["strengths"] = merged[:6]

    elif risk_profile == "conservative":
        # Ensure risks appear before hidden insights
        risks = insights.get("risks", [])
        insights["risks"] = risks  # Already ordered — no change needed

    return insights


def _dedup(items: List[str]) -> List[str]:
    seen, out = set(), []
    for item in items:
        key = item[:50].lower()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out
