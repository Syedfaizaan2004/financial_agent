"""
backend/risk_engine/scenario_assumptions.py

Scenario assumption constants for the Stress Testing Engine.

Defines deterministic adjustment factors for each supported macroeconomic
scenario. All factors are expressed as fractions (e.g. -0.05 = -5%).

Supported scenarios:
  high_inflation  — Rising input costs, softening consumer demand
  recession       — Sharp revenue decline, earnings compression
  rate_hike       — Higher debt servicing burden for leveraged firms
  growth_slowdown — Subdued revenue growth, valuation multiple compression

Design notes:
  - No random values: adjustments are deterministic and documented
  - All values are conservative (calibrated to moderate historical episodes)
  - Higher-severity variants can be added as new scenario keys
  - Factors are multiplicative unless noted as additive (suffix _add)

Factor naming conventions:
  *_impact          : Fractional change applied multiplicatively to a base value
  *_add             : Absolute additive change (e.g. percentage points)
  confidence_factor : Multiplier for forecast confidence (1.0 = no change)
  risk_amplifier    : Multiplier applied to the leverage risk score
"""

from __future__ import annotations

from typing import Any, Dict

# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------
SCENARIOS: Dict[str, Dict[str, Any]] = {

    # -----------------------------------------------------------------------
    # HIGH INFLATION
    # Rising producer costs eat into margins; consumers pull back.
    # Historical reference: 1970s stagflation, 2021–2022 inflation surge.
    # -----------------------------------------------------------------------
    "high_inflation": {
        "label": "High Inflation",
        "description": (
            "Elevated input costs and consumer price pressures compress margins "
            "and reduce real purchasing power, dampening revenue growth."
        ),
        # Revenue growth reduced (demand softening)
        "revenue_growth_impact":  -0.03,    # −3pp on YoY revenue growth
        # Gross/net margins directly compressed by input cost inflation
        "margin_impact":          -0.05,    # −5pp on net margin
        # Forecast sentiment lowered; outlook is uncertain
        "confidence_factor":       0.90,    # 10% confidence reduction
        # Expected price movement discounted
        "movement_impact":        -0.02,    # −2pp on expected movement %
        # Leverage risk amplified if firm has floating-rate debt
        "risk_amplifier":          1.15,    # 15% leverage risk increase
        # Interest cost rises (approximation; precise impact depends on fixed vs floating)
        "interest_cost_impact_add": 0.01,   # +1pp additional interest cost ratio
    },

    # -----------------------------------------------------------------------
    # RECESSION
    # Broad economic contraction; revenue falls, earnings under severe pressure.
    # Historical reference: 2008 GFC, 2001 dot-com bust.
    # -----------------------------------------------------------------------
    "recession": {
        "label": "Recession",
        "description": (
            "A macroeconomic contraction leading to broad revenue declines, "
            "earnings compression, and heightened credit risk."
        ),
        "revenue_growth_impact":  -0.10,    # −10pp on revenue growth
        "margin_impact":          -0.08,    # −8pp on net margin
        "confidence_factor":       0.75,    # 25% confidence reduction
        "movement_impact":        -0.08,    # −8pp on expected movement %
        "risk_amplifier":          1.40,    # 40% leverage risk increase
        "interest_cost_impact_add": 0.02,   # +2pp interest cost (credit spread widening)
    },

    # -----------------------------------------------------------------------
    # INTEREST RATE HIKE
    # Central bank tightening; leveraged firms face higher debt service costs.
    # Historical reference: 2022 Fed rate cycle, 1994 bond market massacre.
    # -----------------------------------------------------------------------
    "rate_hike": {
        "label": "Interest Rate Hike",
        "description": (
            "Aggressive central bank rate increases raise borrowing costs, "
            "pressuring leveraged companies and compressing valuation multiples."
        ),
        "revenue_growth_impact":  -0.02,    # −2pp (indirect: consumer credit tightens)
        "margin_impact":          -0.02,    # −2pp (higher financing costs)
        "confidence_factor":       0.88,    # 12% confidence reduction
        "movement_impact":        -0.03,    # −3pp expected movement
        "risk_amplifier":          1.30,    # 30% leverage risk increase
        "interest_cost_impact_add": 0.04,   # +4pp interest cost (primary driver)
    },

    # -----------------------------------------------------------------------
    # GROWTH SLOWDOWN
    # Economic deceleration without full recession; growth underwhelms.
    # Historical reference: 2015–2016 China slowdown, 2019 trade war.
    # -----------------------------------------------------------------------
    "growth_slowdown": {
        "label": "Growth Slowdown",
        "description": (
            "A decelerating economic environment where revenue growth moderates, "
            "valuation multiples compress, and earnings expectations reset lower."
        ),
        "revenue_growth_impact":  -0.04,    # −4pp on revenue growth
        "margin_impact":          -0.02,    # −2pp on net margin
        "confidence_factor":       0.92,    # 8% confidence reduction
        "movement_impact":        -0.03,    # −3pp expected movement
        "risk_amplifier":          1.10,    # 10% leverage risk increase
        "interest_cost_impact_add": 0.005,  # +0.5pp (minor cost pressure)
    },
}

VALID_SCENARIOS = list(SCENARIOS.keys())


def get_scenario(scenario_name: str) -> Dict[str, Any]:
    """
    Return the assumption dict for a named scenario.

    Args:
        scenario_name (str): One of the VALID_SCENARIOS keys (case-insensitive).

    Returns:
        dict: Scenario assumption factors.

    Raises:
        ValueError: If the scenario name is not recognised.
    """
    key = scenario_name.lower().strip().replace(" ", "_")
    if key not in SCENARIOS:
        raise ValueError(
            f"Unknown scenario '{scenario_name}'. "
            f"Supported scenarios: {', '.join(VALID_SCENARIOS)}"
        )
    return SCENARIOS[key]
