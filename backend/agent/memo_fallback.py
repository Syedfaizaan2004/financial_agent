"""
backend/agent/memo_fallback.py

Rule-based fallback investment memo generator.

Used when LLM is disabled or unavailable. Produces a structured memo
using deterministic rules applied to synthesized insights and raw tool
outputs. No content is fabricated — every claim is derived from actual
analysis data passed in.

This module is intentionally standalone — it imports nothing from the
LLM layer, making it safe to use in offline/test environments.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Outlook → confidence mapping
# ---------------------------------------------------------------------------
_OUTLOOK_CONFIDENCE = {
    "positive":           0.82,
    "moderately_positive": 0.70,
    "neutral":            0.58,
    "cautious":           0.45,
    "negative":           0.32,
}

_VALID_OUTLOOKS = set(_OUTLOOK_CONFIDENCE.keys())


def generate_fallback_memo(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a structured investment memo using rule-based logic.

    Args:
        data (dict): Structured output from the agent workflow, expected keys:
            ticker        (str)
            insights      (dict)  — synthesizer output
            fundamentals  (dict)  — raw fundamentals data (optional)
            risk          (dict)  — raw risk data (optional)
            forecast      (dict)  — raw forecast data (optional)
            peer_comparison (dict)
            scenario      (dict)

    Returns:
        dict: Investment memo with the standard memo schema.
    """
    ticker       = data.get("ticker", "UNKNOWN")
    insights     = data.get("insights") or {}
    fundamentals = data.get("fundamentals") or {}
    risk         = data.get("risk") or {}
    forecast     = data.get("forecast") or {}
    peer         = data.get("peer_comparison") or {}
    scenario     = data.get("scenario") or {}

    # -----------------------------------------------------------------------
    # Build key strengths and risks from synthesizer output
    # -----------------------------------------------------------------------
    key_strengths: List[str] = list(insights.get("strengths", []))
    key_risks:     List[str] = list(insights.get("risks", []))
    opportunities: List[str] = list(insights.get("opportunities", []))

    # Supplement strengths from financials if synthesizer returned too few
    if len(key_strengths) < 2:
        _augment_strengths(key_strengths, fundamentals, insights)

    # Supplement risks from risk engine
    if len(key_risks) < 2:
        _augment_risks(key_risks, risk, scenario)

    # -----------------------------------------------------------------------
    # Bull case
    # -----------------------------------------------------------------------
    bull_case = _build_bull_case(
        strengths=key_strengths,
        opportunities=opportunities,
        forecast_trend=insights.get("forecast_trend", "unavailable"),
        peer_summary=peer.get("summary", []),
        fundamentals=fundamentals,
    )

    # -----------------------------------------------------------------------
    # Bear case
    # -----------------------------------------------------------------------
    bear_case = _build_bear_case(
        risks=key_risks,
        scenario=scenario,
        risk_data=risk,
        forecast_trend=insights.get("forecast_trend", "unavailable"),
    )

    # -----------------------------------------------------------------------
    # Outlook + confidence
    # -----------------------------------------------------------------------
    outlook = insights.get("outlook", "neutral")
    if outlook not in _VALID_OUTLOOKS:
        outlook = "neutral"
    confidence = _compute_confidence(outlook, len(bull_case), len(bear_case))

    # -----------------------------------------------------------------------
    # Executive summary
    # -----------------------------------------------------------------------
    executive_summary = _build_executive_summary(
        ticker=ticker,
        outlook=outlook,
        fundamentals=fundamentals,
        risk_data=risk,
        forecast_trend=insights.get("forecast_trend", "unavailable"),
        peer_positioning=insights.get("peer_positioning", ""),
    )

    # -----------------------------------------------------------------------
    # Analyst note
    # -----------------------------------------------------------------------
    analyst_note = _build_analyst_note(outlook, len(key_risks), len(bull_case))

    logger.info(
        "[fallback_memo] %s | outlook=%s | confidence=%.2f | bull=%d | bear=%d",
        ticker, outlook, confidence, len(bull_case), len(bear_case),
    )

    return {
        "ticker":            ticker,
        "executive_summary": executive_summary,
        "bull_case":         bull_case[:4],
        "bear_case":         bear_case[:4],
        "key_strengths":     key_strengths[:6],
        "key_risks":         key_risks[:6],
        "outlook":           outlook,
        "confidence":        confidence,
        "analyst_note":      analyst_note,
        "generated_by":      "rule_based_fallback",
    }


# ---------------------------------------------------------------------------
# Internal builders
# ---------------------------------------------------------------------------

def _augment_strengths(
    strengths: List[str],
    fundamentals: Dict[str, Any],
    insights: Dict[str, Any],
) -> None:
    """Add extra strengths derived from raw financials."""
    prof = fundamentals.get("profitability") or {}
    nm   = prof.get("net_profit_margin")
    roe  = prof.get("roe")
    if nm and nm > 15 and "profitability" not in " ".join(strengths).lower():
        strengths.append(f"above-average net margin of {nm:.1f}%")
    if roe and roe > 20 and "equity" not in " ".join(strengths).lower():
        strengths.append(f"strong return on equity ({roe:.1f}%)")

    km = insights.get("key_metrics") or {}
    if km.get("market_cap") and "cap" not in " ".join(strengths).lower():
        mc_b = km["market_cap"] / 1e9
        if mc_b > 50:
            strengths.append(f"large-cap company (market cap ~${mc_b:.0f}B) — scale advantage")


def _augment_risks(
    risks: List[str],
    risk_data: Dict[str, Any],
    scenario: Dict[str, Any],
) -> None:
    """Add extra risks from risk engine output."""
    overall = risk_data.get("overall_risk", "")
    if overall == "high" and "high" not in " ".join(risks).lower():
        risks.append("overall risk rated HIGH — multiple risk indicators elevated")
    scen_msg = scenario.get("risk_outlook", "")
    if scen_msg and "scenario" not in " ".join(risks).lower():
        risks.append(f"macro scenario risk: {scen_msg[:80]}")


def _build_bull_case(
    strengths: List[str],
    opportunities: List[str],
    forecast_trend: str,
    peer_summary: List[str],
    fundamentals: Dict[str, Any],
) -> List[str]:
    bull: List[str] = []
    # From opportunities (already bullish-framed)
    for opp in opportunities[:2]:
        bull.append(opp)
    # From strengths (top 2)
    for s in strengths[:2]:
        if s not in bull:
            bull.append(s)
    # Forecast
    if forecast_trend == "upward":
        bull.append("quantitative model signals upward price momentum")
    # Peer undervaluation
    for p in peer_summary:
        if "undervalued" in p or "discount" in p:
            bull.append(p[:80])
            break
    return _dedup(bull)[:4]


def _build_bear_case(
    risks: List[str],
    scenario: Dict[str, Any],
    risk_data: Dict[str, Any],
    forecast_trend: str,
) -> List[str]:
    bear: List[str] = []
    for r in risks[:3]:
        bear.append(r)
    if forecast_trend == "downward":
        bear.append("model signals negative price direction in near term")
    scen_summary = scenario.get("summary", [])
    if scen_summary:
        bear.append(f"recession stress: {scen_summary[0][:80]}")
    hidden = risk_data.get("hidden_risks", [])
    if hidden:
        bear.append(f"compound risk detected: {hidden[0][:80]}")
    return _dedup(bear)[:4]


def _build_executive_summary(
    ticker: str,
    outlook: str,
    fundamentals: Dict[str, Any],
    risk_data: Dict[str, Any],
    forecast_trend: str,
    peer_positioning: str,
) -> str:
    prof    = fundamentals.get("profitability") or {}
    nm      = prof.get("net_profit_margin")
    risk_lv = risk_data.get("overall_risk", "moderate")

    parts = []

    # Profitability sentence
    if nm is not None:
        if nm > 20:
            parts.append(f"{ticker} demonstrates strong profitability with a {nm:.1f}% net margin")
        elif nm > 10:
            parts.append(f"{ticker} operates with a moderate {nm:.1f}% net profit margin")
        elif nm > 0:
            parts.append(f"{ticker} shows thin profitability with a {nm:.1f}% net margin")
        else:
            parts.append(f"{ticker} is currently unprofitable with a {nm:.1f}% net margin")
    else:
        parts.append(f"{ticker} is under analysis")

    # Risk + forecast sentence
    risk_phrase = {"low": "low risk profile", "moderate": "moderate risk", "high": "elevated risk"}.get(risk_lv, "moderate risk")
    fc_phrase   = {"upward": "positive directional bias", "downward": "negative directional bias"}.get(forecast_trend, "uncertain near-term direction")
    parts.append(f"and carries a {risk_phrase} with {fc_phrase}")

    # Outlook
    outlook_phrase = outlook.replace("_", " ")
    parts.append(f"Overall investment outlook is {outlook_phrase}")

    return ". ".join(parts) + "."


def _compute_confidence(
    outlook: str, bull_count: int, bear_count: int
) -> float:
    base     = _OUTLOOK_CONFIDENCE.get(outlook, 0.58)
    bonus    = min(bull_count, 3) * 0.02
    penalty  = min(bear_count, 3) * 0.02
    return round(min(0.95, max(0.20, base + bonus - penalty)), 2)


def _build_analyst_note(
    outlook: str, risk_count: int, bull_count: int
) -> str:
    if outlook in ("positive", "moderately_positive"):
        return (
            "Suitable for growth-oriented investors; monitor risk indicators for deterioration."
            if risk_count <= 2 else
            "Growth story intact but elevated risks warrant position sizing discipline."
        )
    if outlook == "neutral":
        return "Balanced risk-reward; awaiting catalyst for directional clarity."
    if outlook == "cautious":
        return "Multiple risk factors present; prefer waiting for stronger financial signals."
    return "Multiple headwinds identified; suitable only for high-risk-tolerance investors."


def _dedup(items: List[str]) -> List[str]:
    seen, out = set(), []
    for item in items:
        key = item[:50].lower()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out
