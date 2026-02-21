"""
backend/risk_engine/forecast_stress.py

Forecast stress adjuster for the Scenario & Stress Testing Engine.

Takes an existing forecast dict (from the ensemble forecasting module or a
manually supplied baseline) and applies scenario-aware adjustments to:
  - expected price movement %
  - forecast confidence score

Design principle: adjustments are applied as scalar multipliers / additive
offsets — no statistical models, no random sampling.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def adjust_forecast_under_scenario(
    forecast: Dict[str, Any],
    scenario: str,
) -> Dict[str, Any]:
    """
    Apply macroeconomic stress adjustments to a baseline forecast dict.

    The forecast dict is expected to contain (at a minimum):
        expected_movement (float): Predicted % price change (can be None)
        confidence (float): Confidence score [0, 1] (can be None)

    Adjustments applied:
        expected_movement → movement + scenario_movement_impact (pp)
        confidence        → confidence × scenario_confidence_factor

    Args:
        forecast (dict): Baseline forecast output (from ensemble or manual).
        scenario (str): Scenario key (e.g. 'recession').

    Returns:
        dict:
            base_expected_movement (float | None)
            adjusted_expected_movement (float | None)
            base_confidence (float | None)
            adjusted_confidence (float | None)
            scenario (str)
            movement_adjustment (float): pp applied
            confidence_factor (float): multiplier applied
            direction (str): 'bullish' | 'bearish' | 'neutral' | 'unknown'
            notes (str)
    """
    from backend.risk_engine.scenario_assumptions import get_scenario

    assumptions = get_scenario(scenario)
    movement_adj     = assumptions.get("movement_impact", 0.0)
    confidence_factor = assumptions.get("confidence_factor", 1.0)

    base_movement: Optional[float] = forecast.get("expected_movement")
    base_confidence: Optional[float] = forecast.get("confidence")

    # --- Adjust movement ---
    if base_movement is not None:
        # Convert fraction movement to pp adjustment (movement already in %)
        movement_adj_pp = movement_adj * 100
        adjusted_movement = round(base_movement + movement_adj_pp, 2)
    else:
        adjusted_movement = None
        movement_adj_pp = movement_adj * 100

    # --- Adjust confidence ---
    if base_confidence is not None:
        adjusted_confidence = round(
            max(0.0, min(1.0, base_confidence * confidence_factor)), 4
        )
    else:
        adjusted_confidence = None

    # --- Direction classification ---
    if adjusted_movement is None:
        direction = "unknown"
    elif adjusted_movement > 1.0:
        direction = "bullish"
    elif adjusted_movement < -1.0:
        direction = "bearish"
    else:
        direction = "neutral"

    notes = _build_notes(
        scenario, base_movement, adjusted_movement,
        base_confidence, adjusted_confidence, confidence_factor,
    )

    logger.info(
        "Forecast stress [%s]: movement %s→%s | confidence %s→%s",
        scenario, base_movement, adjusted_movement, base_confidence, adjusted_confidence,
    )

    return {
        "base_expected_movement": base_movement,
        "adjusted_expected_movement": adjusted_movement,
        "base_confidence": base_confidence,
        "adjusted_confidence": adjusted_confidence,
        "scenario": scenario,
        "movement_adjustment_pp": round(movement_adj_pp, 2),
        "confidence_factor": confidence_factor,
        "direction": direction,
        "notes": notes,
    }


def _build_notes(
    scenario: str,
    base_mv: Optional[float],
    adj_mv: Optional[float],
    base_cf: Optional[float],
    adj_cf: Optional[float],
    cf_factor: float,
) -> str:
    parts = [f"Under the '{scenario}' scenario:"]
    if base_mv is not None and adj_mv is not None:
        parts.append(
            f"expected price movement revised from {base_mv:+.1f}% to {adj_mv:+.1f}%"
        )
    if base_cf is not None and adj_cf is not None:
        pct_change = round((cf_factor - 1) * 100, 1)
        parts.append(
            f"forecast confidence reduced by {abs(pct_change):.0f}% "
            f"({base_cf:.2f} → {adj_cf:.2f})"
        )
    return "; ".join(parts) + "."
