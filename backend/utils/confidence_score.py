"""
backend/utils/confidence_score.py

Confidence scoring module for the AI Research Agent.

Calculates a composite confidence score (0.0 – 1.0) for a research
analysis output by combining signals from:

  1. Forecast model agreement (TFT vs XGBoost)
  2. Earnings stability
  3. Risk level (leverage, liquidity, overall)
  4. Data completeness
  5. Scenario stress sensitivity

All factors apply named, documented adjustments to a baseline score.
The result is clipped to [MIN_CONFIDENCE, MAX_CONFIDENCE].

This is fully deterministic — no LLM, no randomness.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Baseline and limits
# ---------------------------------------------------------------------------

BASELINE_CONFIDENCE: float = 0.60

# Hard floor/ceiling — score is always clipped to this range
MIN_CONFIDENCE: float = 0.15
MAX_CONFIDENCE: float = 0.95

# ---------------------------------------------------------------------------
# Named adjustments (signs are applied explicitly in logic below)
# ---------------------------------------------------------------------------

ADJ_MODEL_AGREE_STRONG:    float = +0.12   # Both models agree with strong signal
ADJ_MODEL_AGREE_MODERATE:  float = +0.08   # Both agree, moderate signal
ADJ_MODEL_DISAGREE:        float = -0.10   # Models disagree

ADJ_EARNINGS_STABLE:       float = +0.08   # Stable, consistent earnings
ADJ_EARNINGS_MODERATE:     float = +0.02   # Moderate earnings stability
ADJ_EARNINGS_VOLATILE:     float = -0.10   # Volatile earnings
ADJ_EARNINGS_INSUFFICIENT: float = -0.05   # Not enough history

ADJ_RISK_LOW:              float = +0.06   # Low overall risk
ADJ_RISK_MODERATE:         float = +0.00   # Neutral
ADJ_RISK_HIGH:             float = -0.10   # High overall risk

ADJ_LOW_LEVERAGE:          float = +0.04   # D/E < 0.5
ADJ_HIGH_LEVERAGE:         float = -0.06   # D/E > 2.0

ADJ_DATA_COMPLETE:         float = +0.05   # Few / no missing fields
ADJ_DATA_POOR:             float = -0.08   # Many missing fields

ADJ_SCENARIO_RESILIENT:    float = +0.04   # Confidence stays high under stress
ADJ_SCENARIO_SENSITIVE:    float = -0.06   # Confidence drops significantly under stress

# D/E thresholds
LOW_LEVERAGE_DE:  float = 0.5
HIGH_LEVERAGE_DE: float = 2.0

# Missing fields threshold
MANY_MISSING_FIELDS: int = 5


def calculate_confidence(data: Dict[str, Any]) -> float:
    """
    Calculate a composite confidence score for a research analysis output.

    Combines adjustments from model agreement, earnings stability, risk level,
    leverage, data completeness, and scenario sensitivity. Logs each factor
    contributing to the final score.

    Args:
        data (dict): Combined analysis output. Keys (all optional):
            forecast, fundamentals, risk, scenario, insights

    Returns:
        float: Confidence score in [0.15, 0.95].
    """
    forecast     = data.get("forecast")     or {}
    fundamentals = data.get("fundamentals") or {}
    risk         = data.get("risk")         or {}
    scenario     = data.get("scenario")     or {}

    score   = BASELINE_CONFIDENCE
    factors = []

    # --- Factor 1: Forecast model agreement ---
    score, factors = _apply_model_agreement(score, factors, forecast)

    # --- Factor 2: Earnings stability ---
    score, factors = _apply_earnings_stability(score, factors, risk)

    # --- Factor 3: Overall risk level ---
    score, factors = _apply_risk_level(score, factors, risk)

    # --- Factor 4: Leverage ---
    score, factors = _apply_leverage(score, factors, fundamentals)

    # --- Factor 5: Data completeness ---
    score, factors = _apply_data_completeness(score, factors, fundamentals)

    # --- Factor 6: Scenario stress sensitivity ---
    score, factors = _apply_scenario_sensitivity(score, factors, scenario)

    final = round(max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, score)), 3)

    logger.info(
        "[confidence_score] baseline=%.2f | adjustments=%s | final=%.3f",
        BASELINE_CONFIDENCE,
        [(f["factor"], f["adjustment"]) for f in factors],
        final,
    )

    return final


def explain_confidence(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Return the confidence score with a full factor-by-factor breakdown.

    Useful for debugging and transparency reporting.

    Args:
        data (dict): Combined analysis output (same as calculate_confidence).

    Returns:
        dict:
            score (float): Final confidence score
            baseline (float): Starting baseline
            factors (list[dict]): Each factor's contribution
            interpretation (str): Human-readable summary
    """
    forecast     = data.get("forecast")     or {}
    fundamentals = data.get("fundamentals") or {}
    risk         = data.get("risk")         or {}
    scenario     = data.get("scenario")     or {}

    score   = BASELINE_CONFIDENCE
    factors = []

    score, factors = _apply_model_agreement(score, factors, forecast)
    score, factors = _apply_earnings_stability(score, factors, risk)
    score, factors = _apply_risk_level(score, factors, risk)
    score, factors = _apply_leverage(score, factors, fundamentals)
    score, factors = _apply_data_completeness(score, factors, fundamentals)
    score, factors = _apply_scenario_sensitivity(score, factors, scenario)

    final         = round(max(MIN_CONFIDENCE, min(MAX_CONFIDENCE, score)), 3)
    interpretation = _interpret(final)

    return {
        "score":          final,
        "baseline":       BASELINE_CONFIDENCE,
        "factors":        factors,
        "interpretation": interpretation,
    }


# ---------------------------------------------------------------------------
# Factor calculators
# ---------------------------------------------------------------------------

def _apply_model_agreement(
    score: float, factors: List, forecast: Dict
) -> tuple:
    if not forecast or forecast.get("supported") is False:
        factors.append(_factor("model_agreement", 0.0, "Forecast unavailable — no adjustment"))
        return score, factors

    from backend.utils.model_agreement import evaluate_model_agreement
    result = evaluate_model_agreement(forecast)
    adj    = result["confidence_adjustment"]
    note   = result["notes"]

    factors.append(_factor("model_agreement", adj, note))
    return score + adj, factors


def _apply_earnings_stability(
    score: float, factors: List, risk: Dict
) -> tuple:
    stab  = risk.get("earnings_stability") or {}
    cls   = stab.get("classification", "insufficient_data")
    score_ = stab.get("stability_score")

    if cls in ("very_stable", "stable"):
        adj  = ADJ_EARNINGS_STABLE
        note = f"Stable earnings history (classification={cls})"
    elif cls == "moderate":
        adj  = ADJ_EARNINGS_MODERATE
        note = f"Moderate earnings stability"
    elif cls in ("volatile", "highly_volatile"):
        adj  = ADJ_EARNINGS_VOLATILE
        note = f"Volatile earnings (classification={cls}) — reduces reliability"
    else:
        adj  = ADJ_EARNINGS_INSUFFICIENT
        note = "Insufficient earnings history for reliable assessment"

    factors.append(_factor("earnings_stability", adj, note))
    return score + adj, factors


def _apply_risk_level(
    score: float, factors: List, risk: Dict
) -> tuple:
    overall = risk.get("overall_risk", "")

    if overall == "low":
        adj  = ADJ_RISK_LOW
        note = "Low overall risk — increases score reliability"
    elif overall == "high":
        adj  = ADJ_RISK_HIGH
        note = "High overall risk — multiple elevated risk indicators"
    else:
        adj  = ADJ_RISK_MODERATE
        note = "Moderate risk level — neutral adjustment"

    factors.append(_factor("overall_risk", adj, note))
    return score + adj, factors


def _apply_leverage(
    score: float, factors: List, fundamentals: Dict
) -> tuple:
    lev = fundamentals.get("leverage") or {}
    de  = lev.get("debt_to_equity")

    if de is None:
        factors.append(_factor("leverage", 0.0, "D/E ratio unavailable — no adjustment"))
        return score, factors

    if de < LOW_LEVERAGE_DE:
        adj  = ADJ_LOW_LEVERAGE
        note = f"Low leverage (D/E={de:.2f}) — strengthens financial position"
    elif de > HIGH_LEVERAGE_DE:
        adj  = ADJ_HIGH_LEVERAGE
        note = f"High leverage (D/E={de:.2f}) — amplifies downside risk"
    else:
        adj  = 0.0
        note = f"Moderate leverage (D/E={de:.2f}) — neutral"

    factors.append(_factor("leverage", adj, note))
    return score + adj, factors


def _apply_data_completeness(
    score: float, factors: List, fundamentals: Dict
) -> tuple:
    raw     = fundamentals.get("raw_financials") or {}
    missing = [k for k, v in raw.items() if v is None]
    total   = len(raw)

    if total == 0:
        adj  = ADJ_DATA_POOR
        note = "No financial data found — very low data quality"
    elif len(missing) >= MANY_MISSING_FIELDS:
        adj  = ADJ_DATA_POOR
        note = f"{len(missing)}/{total} financial fields missing — incomplete data"
    elif len(missing) == 0:
        adj  = ADJ_DATA_COMPLETE
        note = "All financial fields available — high data quality"
    else:
        adj  = 0.0
        note = f"{len(missing)}/{total} fields missing — acceptable"

    factors.append(_factor("data_completeness", adj, note))
    return score + adj, factors


def _apply_scenario_sensitivity(
    score: float, factors: List, scenario: Dict
) -> tuple:
    fc_adj   = scenario.get("forecast_adjustment") or {}
    adj_conf = fc_adj.get("adjusted_confidence")

    if adj_conf is None:
        factors.append(_factor("scenario_sensitivity", 0.0, "No scenario data — no adjustment"))
        return score, factors

    if adj_conf >= 0.90:
        adj  = ADJ_SCENARIO_RESILIENT
        note = f"Scenario-resilient (adjusted confidence={adj_conf:.0%})"
    elif adj_conf < 0.80:
        adj  = ADJ_SCENARIO_SENSITIVE
        note = (
            f"High macro sensitivity (scenario confidence={adj_conf:.0%}) "
            "— outcome highly dependent on macro conditions"
        )
    else:
        adj  = 0.0
        note = f"Moderate scenario sensitivity (adjusted confidence={adj_conf:.0%})"

    factors.append(_factor("scenario_sensitivity", adj, note))
    return score + adj, factors


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _factor(name: str, adjustment: float, note: str) -> Dict[str, Any]:
    return {"factor": name, "adjustment": round(adjustment, 3), "note": note}


def _interpret(score: float) -> str:
    if score >= 0.80:
        return "High confidence — strong data quality and model agreement."
    if score >= 0.65:
        return "Moderate-high confidence — reliable signals, minor gaps."
    if score >= 0.50:
        return "Moderate confidence — some uncertainty factors present."
    if score >= 0.35:
        return "Low confidence — significant data gaps or risk factors."
    return "Very low confidence — treat all outputs with caution."
