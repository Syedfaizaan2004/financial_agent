"""
backend/risk_engine/revenue_stress.py

Revenue stress simulator for the Scenario & Stress Testing Engine.

Applies scenario-specific growth adjustment factors to a base revenue
growth rate to produce a stress-tested revenue outlook.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def simulate_revenue_impact(
    base_growth: Optional[float],
    scenario: str,
) -> dict:
    """
    Compute stress-adjusted revenue growth under a given macroeconomic scenario.

    The scenario 'revenue_growth_impact' is stored as a fraction (e.g. -0.10).
    It is converted to percentage points (×100) and applied additively, because
    base_growth is expressed in % (e.g. 8.5 = 8.5%):

        adjustment_pp   = revenue_growth_impact × 100    (e.g. -0.10 → -10pp)
        adjusted_growth = base_growth + adjustment_pp

    Args:
        base_growth (float | None): Trailing YoY revenue growth in %
                                    (e.g. 8.5 = 8.5%). None = data unavailable.
        scenario (str): Scenario key (e.g. 'recession').

    Returns:
        dict:
            base_growth (float | None): Input growth rate (%)
            scenario_adjustment_pp (float): pp adjustment applied
            adjusted_growth (float | None): Stressed growth rate (%)
            growth_direction (str): 'growing' | 'declining' | 'flat' | 'unknown'
            notes (str): Explanation of the adjustment
    """
    from backend.risk_engine.scenario_assumptions import get_scenario

    assumptions   = get_scenario(scenario)
    # Convert fraction → percentage points  (e.g. -0.10 → -10pp)
    adjustment_pp = round(assumptions.get("revenue_growth_impact", 0.0) * 100, 2)

    if base_growth is None:
        logger.warning("base_growth is None for revenue stress — returning None for adjusted")
        return {
            "base_growth": None,
            "scenario_adjustment_pp": adjustment_pp,
            "adjusted_growth": None,
            "growth_direction": "unknown",
            "notes": (
                f"Scenario '{scenario}' applies a {adjustment_pp:+.1f}pp revenue growth adjustment. "
                "Base growth was unavailable — absolute adjusted value cannot be computed."
            ),
        }

    adjusted = round(base_growth + adjustment_pp, 2)

    # Thresholds are in the same % scale as base_growth
    if adjusted > 2.0:
        direction = "growing"
    elif adjusted < -1.0:
        direction = "declining"
    else:
        direction = "flat"

    notes = (
        f"Base revenue growth of {base_growth:.2f}% adjusted by {adjustment_pp:+.1f}pp "
        f"under '{scenario}' scenario → stressed growth: {adjusted:.2f}%."
    )
    logger.info("Revenue stress [%s]: base=%.2f%% → adjusted=%.2f%%", scenario, base_growth, adjusted)

    return {
        "base_growth": base_growth,
        "scenario_adjustment_pp": adjustment_pp,
        "adjusted_growth": adjusted,
        "growth_direction": direction,
        "notes": notes,
    }
