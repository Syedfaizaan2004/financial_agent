"""
backend/api/routes/scenario.py

Scenario & Stress Testing API endpoint for the Financial & Market Research Agent.

Endpoint:
    GET /scenario/{ticker}?type=recession
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query

from backend.risk_engine.scenario_assumptions import VALID_SCENARIOS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/scenario", tags=["Scenario Analysis"])

_SCENARIO_DESCRIPTIONS = {
    "high_inflation":  "Rising input costs and softening consumer demand compress margins and revenue growth.",
    "recession":       "Broad economic contraction — revenue declines, earnings compress, credit risk rises.",
    "rate_hike":       "Central bank tightening raises borrowing costs, pressuring leveraged companies.",
    "growth_slowdown": "Economic deceleration — subdued revenue growth, valuation multiple compression.",
}


@router.get(
    "/{ticker}",
    summary="Scenario & Stress Testing",
    description=(
        "Simulates the impact of a macroeconomic scenario on a company's "
        "revenue growth, margins, leverage risk, and forecast outlook.\n\n"
        "**Supported scenarios** (`?type=`):\n"
        "- `high_inflation` — margin compression and demand softening\n"
        "- `recession` — revenue & earnings contraction\n"
        "- `rate_hike` — higher borrowing costs for leveraged firms\n"
        "- `growth_slowdown` — subdued growth and valuation pressure\n\n"
        "Returns **400** for invalid scenario names.\n"
        "Returns **503** if market data (yfinance) is not available.\n"
        "Returns **500** on unexpected errors."
    ),
    response_description="Structured scenario stress test report",
)
async def get_scenario_analysis(
    ticker: str,
    type: str = Query(  # noqa: A002
        default="recession",
        description=(
            f"Macroeconomic scenario to simulate. "
            f"One of: {', '.join(VALID_SCENARIOS)}"
        ),
        alias="type",
    ),
) -> Dict[str, Any]:
    """
    GET /scenario/{ticker}?type=<scenario>

    Runs the full scenario stress pipeline and returns:
      - Revenue growth adjusted for scenario conditions
      - Net margin compressed by scenario cost/demand factors
      - Leverage risk amplified by scenario multiplier
      - Forecast expectation and confidence adjusted
      - Overall risk outlook summary

    Args:
        ticker (str): Stock symbol (case-insensitive).
        type (str): Scenario key (default: 'recession').

    Returns:
        dict: Scenario analysis report.
    """
    canonical = ticker.upper().strip()
    scenario  = type.lower().strip()

    logger.info("Scenario analysis requested: %s / %s", canonical, scenario)

    # Validate scenario
    if scenario not in VALID_SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unknown scenario '{scenario}'. "
                f"Supported: {', '.join(VALID_SCENARIOS)}"
            ),
        )

    try:
        from backend.risk_engine.scenario_engine import run_scenario_analysis
        result = run_scenario_analysis(canonical, scenario)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        error_msg = str(exc)
        if "yfinance" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="Market data provider (yfinance) not available. pip install yfinance",
            ) from exc
        raise HTTPException(
            status_code=404,
            detail=f"No financial data available for '{canonical}': {error_msg}",
        ) from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Scenario analysis failed for %s/%s", canonical, scenario)
        raise HTTPException(
            status_code=500,
            detail=f"Scenario analysis error: {type(exc).__name__}: {exc}",
        ) from exc

    logger.info(
        "Scenario complete for %s/%s | outlook: %s",
        canonical, scenario, result.get("risk_outlook", ""),
    )
    return result
