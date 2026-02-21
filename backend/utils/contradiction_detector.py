"""
backend/utils/contradiction_detector.py

Contradiction detection module for the AI Research Agent.

Identifies conflicting signals across forecast, fundamental, risk, peer,
and scenario analysis outputs. Each contradiction is independently detected
using deterministic if-else rules applied to structured data — no LLM.

Each detected contradiction is a dict with:
    type       (str)   — contradiction category
    severity   (str)   — 'critical' | 'warning' | 'note'
    signal_a   (str)   — first conflicting signal description
    signal_b   (str)   — second conflicting signal description
    message    (str)   — human-readable contradiction summary

Contradictions with severity='critical' should prominently appear in memos.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds (named constants — no magic numbers)
# ---------------------------------------------------------------------------

# Probability above which forecast is considered "strong bullish"
BULLISH_PROB_THRESHOLD: float = 0.60

# Net margin below which profitability is considered weak despite forecast
WEAK_MARGIN_THRESHOLD: float = 5.0

# D/E ratio above which leverage is "high"
HIGH_DE_THRESHOLD: float = 2.0

# Revenue growth rate considered "high growth"
HIGH_GROWTH_THRESHOLD: float = 15.0

# FCF-to-net-income ratio below which cash flow quality is "poor"
POOR_FCF_RATIO_THRESHOLD: float = 0.50

# Net margin considered "high profitability"
HIGH_MARGIN_THRESHOLD: float = 15.0


def detect_contradictions(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Detect conflicting signals across all available analysis outputs.

    Runs a suite of independent contradiction checks. Each check is
    fault-tolerant — failures in one check do not affect others.

    Args:
        data (dict): Combined analysis output. Expected keys (all optional):
            forecast        (dict) — ensemble forecast output
            fundamentals    (dict) — financial analysis output
            risk            (dict) — risk intelligence output
            scenario        (dict) — scenario stress output
            insights        (dict) — synthesizer output
            peer_comparison (dict) — peer analysis output

    Returns:
        list[dict]: List of detected contradictions, each with:
            type, severity, signal_a, signal_b, message
    """
    contradictions: List[Dict[str, Any]] = []

    forecast     = data.get("forecast")     or {}
    fundamentals = data.get("fundamentals") or {}
    risk         = data.get("risk")         or {}
    scenario     = data.get("scenario")     or {}
    insights     = data.get("insights")     or {}

    prof    = fundamentals.get("profitability") or {}
    val     = fundamentals.get("valuation")     or {}
    lev     = fundamentals.get("leverage")      or {}
    growth  = fundamentals.get("growth")        or {}
    eff     = fundamentals.get("efficiency")    or {}

    # Run all checks
    _check_bullish_forecast_weak_fundamentals(contradictions, forecast, prof)
    _check_high_growth_rising_leverage(contradictions, growth, lev)
    _check_profitable_negative_cashflow(contradictions, prof, eff)
    _check_bullish_outlook_high_risk(contradictions, insights, risk)
    _check_bullish_trend_recession_sensitivity(contradictions, forecast, scenario)
    _check_positive_outlook_margin_stress(contradictions, insights, scenario)
    _check_strong_forecast_volatile_earnings(contradictions, forecast, risk)
    _check_high_pe_weak_growth(contradictions, val, growth)

    logger.info(
        "[contradiction_detector] Detected %d contradiction(s)", len(contradictions)
    )
    return contradictions


# ---------------------------------------------------------------------------
# Individual contradiction checks
# ---------------------------------------------------------------------------

def _check_bullish_forecast_weak_fundamentals(
    out: List, forecast: Dict, prof: Dict
) -> None:
    """Strong bullish forecast but fundamentals show weak profitability."""
    prob_up = forecast.get("prob_up") or forecast.get("probability_up")
    nm      = prof.get("net_profit_margin")

    if prob_up is not None and nm is not None:
        if prob_up >= BULLISH_PROB_THRESHOLD and nm < WEAK_MARGIN_THRESHOLD:
            out.append(_contradiction(
                type_    = "forecast_vs_fundamentals",
                severity = "warning",
                signal_a = f"forecast prob_up={prob_up:.0%} (bullish)",
                signal_b = f"net margin={nm:.1f}% (weak)",
                message  = (
                    f"Model forecasts bullish price move ({prob_up:.0%} probability up) "
                    f"but net profit margin is only {nm:.1f}% — may not be fundamentally justified."
                ),
            ))


def _check_high_growth_rising_leverage(
    out: List, growth: Dict, lev: Dict
) -> None:
    """High revenue growth paired with high or rising debt — could be debt-funded growth."""
    rev_growth = growth.get("revenue_growth_yoy") or growth.get("avg_revenue_growth")
    de_ratio   = lev.get("debt_to_equity")

    if rev_growth is not None and de_ratio is not None:
        if rev_growth > HIGH_GROWTH_THRESHOLD and de_ratio > HIGH_DE_THRESHOLD:
            out.append(_contradiction(
                type_    = "growth_vs_leverage",
                severity = "warning",
                signal_a = f"revenue growth={rev_growth:.1f}% (high)",
                signal_b = f"D/E ratio={de_ratio:.2f} (elevated)",
                message  = (
                    f"High revenue growth ({rev_growth:.1f}%) appears to be partially "
                    f"debt-funded (D/E={de_ratio:.2f}). Leverage amplifies downside risk."
                ),
            ))


def _check_profitable_negative_cashflow(
    out: List, prof: Dict, eff: Dict
) -> None:
    """Profitable on income statement but FCF is negative — earnings quality concern."""
    nm  = prof.get("net_profit_margin")
    fcf = eff.get("free_cash_flow")

    if nm is not None and fcf is not None:
        if nm > HIGH_MARGIN_THRESHOLD and fcf < 0:
            out.append(_contradiction(
                type_    = "profitability_vs_cashflow",
                severity = "critical",
                signal_a = f"net margin={nm:.1f}% (strong profitability)",
                signal_b = f"free cash flow={fcf:,.0f} (negative)",
                message  = (
                    f"Reports strong net margin ({nm:.1f}%) but free cash flow is negative "
                    f"({fcf:,.0f}). This suggests potential earnings quality issues — "
                    "accruals may exceed cash generation."
                ),
            ))


def _check_bullish_outlook_high_risk(
    out: List, insights: Dict, risk: Dict
) -> None:
    """Overall outlook is positive/moderately positive but risk level is 'high'."""
    outlook      = insights.get("outlook", "")
    overall_risk = risk.get("overall_risk", "")

    if outlook in ("positive", "moderately_positive") and overall_risk == "high":
        out.append(_contradiction(
            type_    = "outlook_vs_risk",
            severity = "critical",
            signal_a = f"outlook={outlook}",
            signal_b = "overall risk=HIGH",
            message  = (
                f"Outlook is '{outlook}' but overall risk rating is HIGH. "
                "Multiple risk indicators are elevated — positive outlook may not be sustainable."
            ),
        ))


def _check_bullish_trend_recession_sensitivity(
    out: List, forecast: Dict, scenario: Dict
) -> None:
    """Bullish forecast trend but scenario analysis shows bearish direction under recession."""
    direction   = str(forecast.get("direction", "")).lower()
    scen_dir    = (scenario.get("forecast_adjustment") or {}).get("direction", "")

    if direction in ("up", "upward") and scen_dir == "bearish":
        out.append(_contradiction(
            type_    = "forecast_vs_scenario",
            severity = "warning",
            signal_a = "base forecast direction: bullish",
            signal_b = "recession scenario: bearish directional bias",
            message  = (
                "Forecast is bullish under base conditions but turns bearish under a "
                "recession scenario — significant macro sensitivity. "
                "Bull case is conditional on benign macro environment."
            ),
        ))


def _check_positive_outlook_margin_stress(
    out: List, insights: Dict, scenario: Dict
) -> None:
    """Positive outlook but severe margin compression under stress scenario."""
    outlook        = insights.get("outlook", "")
    margin_stress  = scenario.get("margin_stress") or {}
    adj_margin     = margin_stress.get("adjusted_margin")
    margin_state   = margin_stress.get("margin_state", "")

    if outlook in ("positive", "moderately_positive") and margin_state == "loss_making":
        out.append(_contradiction(
            type_    = "outlook_vs_stress",
            severity = "critical",
            signal_a = f"outlook={outlook}",
            signal_b = f"scenario margin state={margin_state} (adj margin={adj_margin})",
            message  = (
                f"Outlook is '{outlook}' but company becomes loss-making under stress scenario "
                f"(stressed margin: {adj_margin}%). Risk of significant reversal under macro shock."
            ),
        ))


def _check_strong_forecast_volatile_earnings(
    out: List, forecast: Dict, risk: Dict
) -> None:
    """Model signals high confidence but earnings historically volatile."""
    fc_confidence   = forecast.get("confidence") or forecast.get("forecast_confidence")
    earnings_stab   = risk.get("earnings_stability") or {}
    classification  = earnings_stab.get("classification", "")

    if fc_confidence is not None and fc_confidence > 0.70:
        if classification in ("highly_volatile", "volatile"):
            out.append(_contradiction(
                type_    = "forecast_vs_earnings_stability",
                severity = "warning",
                signal_a = f"forecast confidence={fc_confidence:.0%} (high)",
                signal_b = f"earnings stability={classification}",
                message  = (
                    f"Forecast confidence is high ({fc_confidence:.0%}) but historical earnings "
                    f"are {classification}. High forecast confidence may be overstated "
                    "given unpredictable earnings history."
                ),
            ))


def _check_high_pe_weak_growth(
    out: List, val: Dict, growth: Dict
) -> None:
    """Valuation premium (high P/E) not supported by revenue growth."""
    pe    = val.get("pe_ratio")
    gr    = growth.get("revenue_growth_yoy") or growth.get("avg_revenue_growth")

    if pe is not None and gr is not None:
        if pe > 30 and gr < 5.0:
            out.append(_contradiction(
                type_    = "valuation_vs_growth",
                severity = "warning",
                signal_a = f"PE ratio={pe:.1f} (premium valuation)",
                signal_b = f"revenue growth={gr:.1f}% (low)",
                message  = (
                    f"Trades at a premium P/E of {pe:.1f}x but revenue growth is only "
                    f"{gr:.1f}%. Premium valuation lacks a high-growth justification — "
                    "valuation compression risk if growth disappoints."
                ),
            ))


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _contradiction(
    type_: str, severity: str, signal_a: str, signal_b: str, message: str
) -> Dict[str, Any]:
    return {
        "type":     type_,
        "severity": severity,
        "signal_a": signal_a,
        "signal_b": signal_b,
        "message":  message,
    }
