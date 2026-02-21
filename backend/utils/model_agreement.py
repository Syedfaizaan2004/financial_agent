"""
backend/utils/model_agreement.py

Forecast model agreement evaluator.

Compares directional signals from the TFT and XGBoost sub-models within
the ensemble forecast output. Agreement between models increases
confidence; disagreement reduces it.

Agreement is determined by comparing:
  - Direction labels ('up' vs 'down')  — primary signal
  - Probability estimates (prob_up / prob_down) — secondary signal

This module is intentionally LLM-free and fully deterministic.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Bonus applied to confidence when both models agree on direction
AGREEMENT_BONUS: float = 0.08

# Penalty applied to confidence when models disagree
DISAGREEMENT_PENALTY: float = 0.10

# Probability threshold below which a signal is considered "weak"
WEAK_SIGNAL_THRESHOLD: float = 0.55

# Probability margin that counts as "strong" agreement
STRONG_AGREEMENT_MARGIN: float = 0.10


def evaluate_model_agreement(forecast: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate directional agreement between TFT and XGBoost forecast sub-models.

    Reads the ensemble forecast output and determines whether the two
    constituent models point in the same direction. Returns a structured
    dict with the agreement verdict and the confidence adjustment to apply.

    Args:
        forecast (dict): Ensemble forecast output. Expected keys (best-effort):
            tft_direction   (str)   — 'up' | 'down' | 'neutral'
            xgb_direction   (str)   — 'up' | 'down' | 'neutral'
            direction       (str)   — ensemble consensus direction
            prob_up         (float) — ensemble probability of upward move
            prob_down       (float) — ensemble probability of downward move
            model_scores    (dict)  — optional sub-model detail

    Returns:
        dict:
            agreement (bool)               — True if both models agree
            direction_match (bool)         — True if sub-model directions match
            tft_direction (str)            — extracted TFT direction
            xgb_direction (str)            — extracted XGBoost direction
            confidence_adjustment (float)  — +BONUS if agree, -PENALTY if not
            signal_strength (str)          — 'strong' | 'moderate' | 'weak'
            notes (str)                    — human-readable explanation
    """
    if not forecast or not isinstance(forecast, dict):
        return _no_forecast_result()

    # --- Extract sub-model directions ---
    tft_dir = _extract_direction(forecast, "tft_direction")
    xgb_dir = _extract_direction(forecast, "xgb_direction")

    # Fall back to model_scores sub-dict if top-level keys absent
    model_scores = forecast.get("model_scores") or {}
    if tft_dir == "unknown" and model_scores:
        tft_dir = _extract_direction(model_scores, "tft")
    if xgb_dir == "unknown" and model_scores:
        xgb_dir = _extract_direction(model_scores, "xgb")

    # --- Determine direction match ---
    # If either is unknown we can't fully assess agreement
    both_known     = tft_dir != "unknown" and xgb_dir != "unknown"
    direction_match = both_known and (tft_dir == xgb_dir)

    # --- Ensemble probability signal strength ---
    prob_up   = forecast.get("prob_up")   or forecast.get("probability_up")
    prob_down = forecast.get("prob_down") or forecast.get("probability_down")
    signal_strength = _assess_signal_strength(prob_up, prob_down)

    # --- Agreement verdict ---
    agreement = direction_match and signal_strength != "weak"

    # --- Confidence adjustment ---
    if agreement:
        adjustment = AGREEMENT_BONUS
        if signal_strength == "strong":
            adjustment += 0.04  # Extra bonus for strong consensus
    elif both_known and not direction_match:
        adjustment = -DISAGREEMENT_PENALTY
    else:
        adjustment = 0.0  # Insufficient data — neutral

    notes = _build_notes(tft_dir, xgb_dir, direction_match, signal_strength, both_known)

    logger.info(
        "[model_agreement] tft=%s xgb=%s | match=%s | strength=%s | adj=%.2f",
        tft_dir, xgb_dir, direction_match, signal_strength, adjustment,
    )

    return {
        "agreement":            agreement,
        "direction_match":      direction_match,
        "tft_direction":        tft_dir,
        "xgb_direction":        xgb_dir,
        "confidence_adjustment": round(adjustment, 3),
        "signal_strength":      signal_strength,
        "notes":                notes,
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _extract_direction(source: Dict[str, Any], key: str) -> str:
    val = source.get(key, "unknown")
    if val is None:
        return "unknown"
    v = str(val).lower().strip()
    if v in ("up", "upward", "bullish", "positive"):
        return "up"
    if v in ("down", "downward", "bearish", "negative"):
        return "down"
    if v in ("neutral", "flat", "sideways"):
        return "neutral"
    return "unknown"


def _assess_signal_strength(
    prob_up: Optional[float], prob_down: Optional[float]
) -> str:
    """Classify strength of the ensemble probability signal."""
    if prob_up is None and prob_down is None:
        return "weak"
    dominant = max(p for p in [prob_up or 0.0, prob_down or 0.0])
    if dominant >= WEAK_SIGNAL_THRESHOLD + STRONG_AGREEMENT_MARGIN:
        return "strong"
    if dominant >= WEAK_SIGNAL_THRESHOLD:
        return "moderate"
    return "weak"


def _build_notes(
    tft: str, xgb: str, match: bool, strength: str, both_known: bool
) -> str:
    if not both_known:
        return "Insufficient sub-model data to assess directional agreement."
    if match and strength == "strong":
        return f"Both models strongly agree: {tft.upper()}. High reliability signal."
    if match:
        return f"Both models agree on {tft.upper()} direction (moderate signal strength)."
    return (
        f"Model disagreement: TFT signals {tft.upper()}, XGBoost signals {xgb.upper()}. "
        "Treat directional forecast with caution."
    )


def _no_forecast_result() -> Dict[str, Any]:
    return {
        "agreement":            False,
        "direction_match":      False,
        "tft_direction":        "unknown",
        "xgb_direction":        "unknown",
        "confidence_adjustment": 0.0,
        "signal_strength":      "weak",
        "notes":                "No forecast data available — agreement cannot be assessed.",
    }
