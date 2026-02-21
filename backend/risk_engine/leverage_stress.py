"""
backend/risk_engine/leverage_stress.py

Leverage stress evaluator for the Scenario & Stress Testing Engine.

Models how rising interest costs and risk amplification under a given
macroeconomic scenario affect the financial stress level of a company
based on its current debt-to-equity ratio.

Primary use case: rate_hike and recession scenarios where leverage risk
is materially amplified.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# D/E thresholds (consistent with leverage_risk.py thresholds)
LOW_DE      = 0.5
MODERATE_DE = 2.0
HIGH_DE     = 4.0


def evaluate_leverage_under_stress(
    de_ratio: Optional[float],
    scenario: str,
) -> Dict[str, Any]:
    """
    Assess how leverage risk is amplified under a given macroeconomic scenario.

    Applies the scenario's risk_amplifier to the current D/E-based risk score
    and re-classifies the stress risk level accordingly.

    Args:
        de_ratio (float | None): Current debt-to-equity ratio. None = unavailable.
        scenario (str): Scenario key (e.g. 'rate_hike').

    Returns:
        dict:
            base_de_ratio (float | None): Input D/E ratio
            scenario (str): Applied scenario name
            risk_amplifier (float): Multiplier from scenario assumptions
            interest_cost_increase_pp (float): Additional interest cost (pp)
            base_risk_level (str): Risk level from D/E alone
            stressed_risk_level (str): Risk level after scenario amplification
            stressed_risk_score (float | None): Amplified numeric risk score (0–10)
            at_risk (bool): True if stressed risk level is 'high' or 'critical'
            notes (str): Explanation
    """
    from backend.risk_engine.scenario_assumptions import get_scenario

    assumptions = get_scenario(scenario)
    amplifier = assumptions.get("risk_amplifier", 1.0)
    interest_add = assumptions.get("interest_cost_impact_add", 0.0)

    # --- Base D/E risk score (0–10) ---
    base_score, base_level = _de_to_risk(de_ratio)

    if de_ratio is None:
        return {
            "base_de_ratio": None,
            "scenario": scenario,
            "risk_amplifier": amplifier,
            "interest_cost_increase_pp": round(interest_add * 100, 2),
            "base_risk_level": "unknown",
            "stressed_risk_level": "unknown",
            "stressed_risk_score": None,
            "at_risk": False,
            "notes": (
                f"D/E ratio unavailable — cannot compute stressed leverage risk. "
                f"Scenario '{scenario}' applies a {amplifier:.2f}x risk amplifier."
            ),
        }

    # --- Apply amplification ---
    stressed_score = min(10.0, round(base_score * amplifier, 2))
    _, stressed_level = _score_to_risk(stressed_score)

    at_risk = stressed_level in ("high", "critical")

    notes = (
        f"D/E of {de_ratio:.2f}x (base risk: {base_level}) amplified by {amplifier:.2f}x "
        f"under '{scenario}' scenario → stressed risk: {stressed_level} "
        f"(score: {stressed_score:.1f}/10). "
    )
    if interest_add > 0:
        notes += (
            f"Interest cost burden increases by approximately {interest_add*100:.1f}pp. "
        )
    if at_risk:
        notes += "⚠️ Company faces elevated debt servicing pressure under this scenario."

    logger.info(
        "Leverage stress [%s]: D/E=%.2f | base=%s → stressed=%s",
        scenario, de_ratio, base_level, stressed_level,
    )

    return {
        "base_de_ratio": de_ratio,
        "scenario": scenario,
        "risk_amplifier": amplifier,
        "interest_cost_increase_pp": round(interest_add * 100, 2),
        "base_risk_level": base_level,
        "stressed_risk_level": stressed_level,
        "stressed_risk_score": stressed_score,
        "at_risk": at_risk,
        "notes": notes,
    }


def _de_to_risk(de: Optional[float]) -> tuple[float, str]:
    """Map D/E ratio to a 0–10 base risk score and label."""
    if de is None:
        return 5.0, "unknown"
    if de > HIGH_DE:
        return 8.0, "critical"
    if de > MODERATE_DE:
        return 6.0, "high"
    if de > LOW_DE:
        return 3.5, "moderate"
    return 1.5, "low"


def _score_to_risk(score: float) -> tuple[float, str]:
    """Round a numeric score to the nearest risk level label."""
    if score >= 8:
        return score, "critical"
    if score >= 6:
        return score, "high"
    if score >= 3:
        return score, "moderate"
    return score, "low"
