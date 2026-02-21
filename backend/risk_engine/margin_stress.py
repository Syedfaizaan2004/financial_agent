"""
backend/risk_engine/margin_stress.py

Margin stress simulator for the Scenario & Stress Testing Engine.

Adjusts the current net profit margin downward by the scenario-defined
cost/demand pressure factor.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def simulate_margin_impact(
    current_margin: Optional[float],
    scenario: str,
) -> dict:
    """
    Compute stress-adjusted net profit margin under a macroeconomic scenario.

    The scenario adjustment is applied additively in percentage points:

        adjusted_margin = current_margin + scenario_margin_impact (both in %)

    Args:
        current_margin (float | None): Current trailing net profit margin in %
                                       (e.g. 23.5 = 23.5%). None = unavailable.
        scenario (str): Scenario key (e.g. 'high_inflation').

    Returns:
        dict:
            base_margin (float | None): Input margin
            scenario_adjustment (float): pp adjustment applied
            adjusted_margin (float | None): Stressed margin
            margin_state (str): 'healthy' | 'thin' | 'loss_making' | 'unknown'
            notes (str): Explanation
    """
    from backend.risk_engine.scenario_assumptions import get_scenario

    assumptions = get_scenario(scenario)
    adjustment_fraction = assumptions.get("margin_impact", 0.0)
    # Convert fraction → percentage points (e.g. -0.05 → -5pp)
    adjustment_pp = round(adjustment_fraction * 100, 2)

    if current_margin is None:
        return {
            "base_margin": None,
            "scenario_adjustment_pp": adjustment_pp,
            "adjusted_margin": None,
            "margin_state": "unknown",
            "notes": (
                f"Scenario '{scenario}' applies a {adjustment_pp:+.1f}pp margin compression. "
                "Current margin was unavailable — adjusted value cannot be computed."
            ),
        }

    adjusted = round(current_margin + adjustment_pp, 2)

    if adjusted > 15:
        state = "healthy"
    elif adjusted > 5:
        state = "thin"
    elif adjusted >= 0:
        state = "very_thin"
    else:
        state = "loss_making"

    notes = (
        f"Net margin of {current_margin:.1f}% compressed by {adjustment_pp:+.1f}pp "
        f"under '{scenario}' scenario → stressed margin: {adjusted:.1f}%."
    )
    if state == "loss_making":
        notes += " ⚠️ Company would operate at a loss under this scenario."
    elif state == "very_thin":
        notes += " ⚠️ Margin would be critically thin — any further pressure creates losses."

    logger.info("Margin stress [%s]: base=%.1f%% → adjusted=%.1f%%", scenario, current_margin, adjusted)

    return {
        "base_margin": current_margin,
        "scenario_adjustment_pp": adjustment_pp,
        "adjusted_margin": adjusted,
        "margin_state": state,
        "notes": notes,
    }
