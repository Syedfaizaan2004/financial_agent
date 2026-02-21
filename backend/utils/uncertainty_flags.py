"""
backend/utils/uncertainty_flags.py

Uncertainty flagging module for the AI Research Agent.

Identifies conditions that reduce the reliability of analysis outputs.
Flags are informational signals — they do not block execution but should
be surfaced in memos and agent responses to ensure transparency.

Each flag is a dict with:
    type       (str) — flag category
    severity   (str) — 'high' | 'medium' | 'low'
    field      (str) — data field or area affected
    message    (str) — human-readable explanation

This module is fully deterministic — no LLM, no randomness.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Threshold constants
# ---------------------------------------------------------------------------

# Minimum number of financial fields required for "complete" data
MIN_REQUIRED_FIELDS: int = 5

# Volatility CV threshold considered "high"
HIGH_VOLATILITY_CV: float = 0.30

# Scenario confidence adjustment below which sensitivity is "high"
HIGH_SCENARIO_SENSITIVITY: float = 0.80

# Earnings stability score below which earnings are "volatile"
LOW_STABILITY_SCORE: float = 0.50

# Minimum years of earnings data for reliable stability assessment
MIN_EARNINGS_YEARS: int = 3


def identify_uncertainties(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Identify uncertainty flags across all available analysis outputs.

    Each check independently scans a different dimension of uncertainty:
      1. Missing financial data fields
      2. Volatile / insufficient earnings history
      3. High scenario stress sensitivity
      4. Forecast model disagreement
      5. Data quality notes from the financial analyzer
      6. Unknown risk classifications

    Args:
        data (dict): Combined analysis output. Keys (all optional):
            forecast, fundamentals, risk, scenario, insights

    Returns:
        list[dict]: Uncertainty flags, each with type, severity, field, message.
    """
    flags: List[Dict[str, Any]] = []

    forecast     = data.get("forecast")     or {}
    fundamentals = data.get("fundamentals") or {}
    risk         = data.get("risk")         or {}
    scenario     = data.get("scenario")     or {}
    insights     = data.get("insights")     or {}

    _flag_missing_financial_data(flags, fundamentals)
    _flag_volatile_earnings(flags, risk)
    _flag_scenario_sensitivity(flags, scenario)
    _flag_model_disagreement(flags, forecast)
    _flag_data_quality_notes(flags, fundamentals)
    _flag_unknown_risk_components(flags, risk)
    _flag_forecast_unavailable(flags, forecast)
    _flag_peer_group_missing(flags, data.get("peer_comparison") or {})

    logger.info("[uncertainty_flags] %d flag(s) identified", len(flags))
    return flags


# ---------------------------------------------------------------------------
# Individual uncertainty checks
# ---------------------------------------------------------------------------

def _flag_missing_financial_data(flags: List, fundamentals: Dict) -> None:
    """Flag when several core financial metrics are unavailable."""
    raw = fundamentals.get("raw_financials") or {}
    missing = [k for k, v in raw.items() if v is None]
    total   = len(raw)

    if total == 0:
        flags.append(_flag(
            type_    = "missing_data",
            severity = "high",
            field    = "fundamentals",
            message  = "No financial data available — all analysis is based on defaults.",
        ))
    elif len(missing) >= MIN_REQUIRED_FIELDS:
        flags.append(_flag(
            type_    = "missing_data",
            severity = "medium",
            field    = "raw_financials",
            message  = (
                f"{len(missing)}/{total} core financial fields unavailable. "
                "Fundamental analysis may be incomplete or unreliable."
            ),
        ))


def _flag_volatile_earnings(flags: List, risk: Dict) -> None:
    """Flag earnings instability indicators from the risk engine."""
    stab = risk.get("earnings_stability") or {}
    classification  = stab.get("classification", "")
    years_analyzed  = stab.get("total_years_analyzed", 0)
    volatility_cv   = stab.get("volatility_cv")

    if classification in ("highly_volatile", "volatile"):
        flags.append(_flag(
            type_    = "volatile_earnings",
            severity = "high",
            field    = "earnings_stability",
            message  = (
                f"Earnings classified as '{classification}' over {years_analyzed} years. "
                "High earnings volatility reduces forecast reliability."
            ),
        ))
    elif classification == "insufficient_data" or years_analyzed < MIN_EARNINGS_YEARS:
        flags.append(_flag(
            type_    = "insufficient_earnings_history",
            severity = "medium",
            field    = "earnings_stability",
            message  = (
                f"Only {years_analyzed} year(s) of earnings data available "
                f"(minimum {MIN_EARNINGS_YEARS} required for reliable stability assessment)."
            ),
        ))

    if volatility_cv is not None and volatility_cv > HIGH_VOLATILITY_CV:
        flags.append(_flag(
            type_    = "high_earnings_volatility_cv",
            severity = "medium",
            field    = "earnings_stability.volatility_cv",
            message  = (
                f"Earnings coefficient of variation is high (CV={volatility_cv:.2f}). "
                "Earnings series is unpredictable — forecasts have wider error bands."
            ),
        ))


def _flag_scenario_sensitivity(flags: List, scenario: Dict) -> None:
    """Flag high macro stress sensitivity from scenario analysis."""
    fc_adj = scenario.get("forecast_adjustment") or {}
    adj_conf = fc_adj.get("adjusted_confidence")

    if adj_conf is not None and adj_conf < HIGH_SCENARIO_SENSITIVITY:
        flags.append(_flag(
            type_    = "high_scenario_sensitivity",
            severity = "medium",
            field    = "scenario.forecast_adjustment",
            message  = (
                f"Scenario analysis reduces forecast confidence to {adj_conf:.0%}. "
                "Company shows elevated sensitivity to macro stress conditions."
            ),
        ))

    # Flag if margin turns loss-making under stress
    margin_state = (scenario.get("margin_stress") or {}).get("margin_state", "")
    if margin_state == "loss_making":
        flags.append(_flag(
            type_    = "stress_loss_risk",
            severity = "high",
            field    = "scenario.margin_stress",
            message  = (
                "Company becomes loss-making under the stress scenario. "
                "Significant financial fragility under adverse macro conditions."
            ),
        ))


def _flag_model_disagreement(flags: List, forecast: Dict) -> None:
    """Flag when forecast sub-models disagree on direction."""
    if not forecast:
        return
    from backend.utils.model_agreement import evaluate_model_agreement
    agreement_result = evaluate_model_agreement(forecast)
    if not agreement_result["agreement"] and agreement_result["direction_match"] is False:
        if agreement_result["tft_direction"] != "unknown" and \
           agreement_result["xgb_direction"] != "unknown":
            flags.append(_flag(
                type_    = "model_disagreement",
                severity = "high",
                field    = "forecast.sub_models",
                message  = (
                    f"TFT and XGBoost models disagree: "
                    f"TFT={agreement_result['tft_direction'].upper()}, "
                    f"XGBoost={agreement_result['xgb_direction'].upper()}. "
                    "Treat directional forecast with elevated skepticism."
                ),
            ))


def _flag_data_quality_notes(flags: List, fundamentals: Dict) -> None:
    """Surface data quality notes from the financial analyzer."""
    notes = fundamentals.get("data_quality_notes") or []
    if len(notes) >= 5:
        flags.append(_flag(
            type_    = "data_quality",
            severity = "medium",
            field    = "fundamentals.data_quality_notes",
            message  = (
                f"{len(notes)} financial data quality issue(s) detected. "
                "Financial analysis is working with incomplete market data."
            ),
        ))


def _flag_unknown_risk_components(flags: List, risk: Dict) -> None:
    """Flag when key risk sub-modules returned 'unknown' classifications."""
    unknown_areas = []

    if (risk.get("leverage_risk") or {}).get("risk_level") == "unknown":
        unknown_areas.append("leverage")
    if (risk.get("liquidity_risk") or {}).get("risk_level") == "unknown":
        unknown_areas.append("liquidity")
    if (risk.get("earnings_stability") or {}).get("risk_level") == "unknown":
        unknown_areas.append("earnings stability")

    if unknown_areas:
        flags.append(_flag(
            type_    = "unknown_risk_components",
            severity = "low",
            field    = "risk",
            message  = (
                f"Risk assessment incomplete for: {', '.join(unknown_areas)}. "
                "These areas could not be evaluated due to missing data."
            ),
        ))


def _flag_forecast_unavailable(flags: List, forecast: Dict) -> None:
    """Flag when forecast model doesn't support this ticker."""
    if forecast.get("supported") is False:
        flags.append(_flag(
            type_    = "forecast_unavailable",
            severity = "low",
            field    = "forecast",
            message  = (
                forecast.get("message") or
                "This ticker is not in the forecasting model universe. "
                "Price direction analysis is unavailable."
            ),
        ))


def _flag_peer_group_missing(flags: List, peer: Dict) -> None:
    """Flag when no peer group is defined for the ticker."""
    peer_group = peer.get("peer_group") or []
    if not peer_group:
        flags.append(_flag(
            type_    = "no_peer_group",
            severity = "low",
            field    = "peer_comparison",
            message  = (
                "No peer group defined for this ticker. "
                "Relative valuation and peer benchmarking are unavailable."
            ),
        ))


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _flag(type_: str, severity: str, field: str, message: str) -> Dict[str, Any]:
    return {
        "type":     type_,
        "severity": severity,
        "field":    field,
        "message":  message,
    }
