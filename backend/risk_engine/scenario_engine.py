"""
backend/risk_engine/scenario_engine.py

Main Scenario & Stress Testing pipeline for the Financial & Market Research Agent.

Orchestrates all stress sub-modules to produce a comprehensive scenario
analysis report for a given ticker and macroeconomic scenario.

Pipeline:
  1. Fetch financial statements + KPIs
  2. Retrieve baseline forecast (best-effort via ensemble; None if unavailable)
  3. Apply revenue stress
  4. Apply margin stress
  5. Evaluate leverage under stress
  6. Adjust forecast under scenario
  7. Compute overall risk outlook
  8. Generate summary insights
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def run_scenario_analysis(ticker: str, scenario: str) -> Dict[str, Any]:
    """
    Run the complete scenario stress test for a ticker and macroeconomic scenario.

    Each sub-module failure is isolated — partial results degrade gracefully
    rather than propagating exceptions.

    Args:
        ticker (str): Validated uppercase stock symbol (e.g. 'AAPL').
        scenario (str): Scenario key — one of: high_inflation, recession,
                        rate_hike, growth_slowdown.

    Returns:
        dict: Structured scenario analysis result (see module docstring).

    Raises:
        ValueError: If the scenario key is invalid.
        RuntimeError: If financial data cannot be fetched at all.
    """
    from backend.risk_engine.scenario_assumptions import get_scenario, VALID_SCENARIOS

    # Validate scenario early — fast fail before any I/O
    try:
        assumptions = get_scenario(scenario)
    except ValueError:
        raise ValueError(
            f"Unknown scenario '{scenario}'. "
            f"Choose from: {', '.join(VALID_SCENARIOS)}"
        )

    errors: List[str] = []
    logger.info("=== Scenario analysis: %s / %s ===", ticker, scenario)

    # -----------------------------------------------------------------------
    # Step 1: Fetch financials + KPIs
    # -----------------------------------------------------------------------
    from backend.data.financials import fetch_financial_statements
    from backend.core.kpi_calculator import calculate_kpis

    try:
        financials = fetch_financial_statements(ticker)
    except Exception as exc:
        raise RuntimeError(
            f"Cannot run scenario analysis without financial data for '{ticker}': {exc}"
        ) from exc

    try:
        kpis = calculate_kpis(financials)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("KPI calculation failed for scenario analysis: %s", exc)
        kpis = {}
        errors.append(f"KPI calculation: {exc}")

    # Extract key baseline values
    base_revenue_growth: Optional[float] = kpis.get("revenue_growth_yoy") or financials.get("revenue_growth_yoy")
    base_net_margin: Optional[float]     = kpis.get("net_profit_margin")
    de_ratio: Optional[float]            = kpis.get("debt_to_equity")

    # -----------------------------------------------------------------------
    # Step 2: Attempt baseline forecast (best-effort; not required)
    # -----------------------------------------------------------------------
    baseline_forecast: Dict[str, Any] = {}
    try:
        from backend.forecasting.ensemble import generate_forecast
        from backend.forecasting.utils import is_supported_ticker
        if is_supported_ticker(ticker):
            raw_forecast = generate_forecast(ticker)
            # Normalise to expected_movement + confidence
            baseline_forecast = {
                "expected_movement": raw_forecast.get("expected_movement"),
                "confidence": raw_forecast.get("confidence"),
            }
            logger.info(
                "Baseline forecast loaded for %s: movement=%s confidence=%s",
                ticker,
                baseline_forecast.get("expected_movement"),
                baseline_forecast.get("confidence"),
            )
        else:
            logger.info("Ticker %s not in forecasting universe — skipping forecast stress", ticker)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("Baseline forecast unavailable for %s: %s", ticker, exc)
        errors.append(f"Forecast baseline: {exc}")

    # -----------------------------------------------------------------------
    # Step 3: Revenue stress
    # -----------------------------------------------------------------------
    from backend.risk_engine.revenue_stress import simulate_revenue_impact
    try:
        revenue_stress = simulate_revenue_impact(base_revenue_growth, scenario)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Revenue stress failed: %s", exc)
        revenue_stress = {"adjusted_growth": None, "notes": str(exc)}
        errors.append(f"Revenue stress: {exc}")

    # -----------------------------------------------------------------------
    # Step 4: Margin stress
    # -----------------------------------------------------------------------
    from backend.risk_engine.margin_stress import simulate_margin_impact
    try:
        margin_stress = simulate_margin_impact(base_net_margin, scenario)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Margin stress failed: %s", exc)
        margin_stress = {"adjusted_margin": None, "notes": str(exc)}
        errors.append(f"Margin stress: {exc}")

    # -----------------------------------------------------------------------
    # Step 5: Leverage stress
    # -----------------------------------------------------------------------
    from backend.risk_engine.leverage_stress import evaluate_leverage_under_stress
    try:
        leverage_stress = evaluate_leverage_under_stress(de_ratio, scenario)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Leverage stress failed: %s", exc)
        leverage_stress = {"stressed_risk_level": "unknown", "notes": str(exc)}
        errors.append(f"Leverage stress: {exc}")

    # -----------------------------------------------------------------------
    # Step 6: Forecast stress
    # -----------------------------------------------------------------------
    from backend.risk_engine.forecast_stress import adjust_forecast_under_scenario
    try:
        if baseline_forecast:
            forecast_adjustment = adjust_forecast_under_scenario(baseline_forecast, scenario)
        else:
            # No forecast data — synthesise a stub with scenario movement hint
            movement_hint = assumptions.get("movement_impact", 0.0) * 100
            forecast_adjustment = {
                "base_expected_movement": None,
                "adjusted_expected_movement": round(movement_hint, 2),
                "base_confidence": None,
                "adjusted_confidence": None,
                "direction": "bearish" if movement_hint < 0 else "bullish",
                "notes": (
                    f"No baseline forecast available. Under '{scenario}', "
                    f"directional bias is {movement_hint:+.1f}%."
                ),
            }
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("Forecast stress failed: %s", exc)
        forecast_adjustment = {"direction": "unknown", "notes": str(exc)}
        errors.append(f"Forecast stress: {exc}")

    # -----------------------------------------------------------------------
    # Step 7: Risk outlook + summary
    # -----------------------------------------------------------------------
    risk_outlook = _build_risk_outlook(
        scenario, assumptions, revenue_stress, margin_stress, leverage_stress,
    )
    summary = _build_summary(
        scenario, revenue_stress, margin_stress, leverage_stress, forecast_adjustment,
    )

    logger.info(
        "Scenario analysis complete for %s/%s | outlook: %s",
        ticker, scenario, risk_outlook,
    )

    return {
        "ticker": ticker,
        "scenario": scenario,
        "scenario_label": assumptions.get("label", scenario),
        "scenario_description": assumptions.get("description", ""),
        "revenue_stress": revenue_stress,
        "margin_stress": margin_stress,
        "leverage_stress": leverage_stress,
        "forecast_adjustment": forecast_adjustment,
        "risk_outlook": risk_outlook,
        "summary": summary,
        "analysis_errors": errors,
    }


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _build_risk_outlook(
    scenario: str,
    assumptions: Dict[str, Any],
    revenue: Dict[str, Any],
    margin: Dict[str, Any],
    leverage: Dict[str, Any],
) -> str:
    """Produce a one-line risk outlook string from stress results."""
    label = assumptions.get("label", scenario)
    level = leverage.get("stressed_risk_level", "moderate")
    at_risk = leverage.get("at_risk", False)

    adj_growth = revenue.get("adjusted_growth")
    margin_state = margin.get("margin_state", "unknown")

    if at_risk and margin_state in ("loss_making", "very_thin"):
        return f"severe risk amplification under {label} — earnings and debt servicing both threatened"
    if at_risk:
        return f"elevated leverage risk under {label} — debt servicing pressure increases materially"
    if adj_growth is not None and adj_growth < 0:
        return f"revenue likely to contract under {label} — earnings outlook deteriorates"
    if margin_state in ("loss_making", "very_thin"):
        return f"margin compression under {label} creates profitability risk"
    return f"moderate risk increase expected under {label} — monitor closely"


def _build_summary(
    scenario: str,
    revenue: Dict[str, Any],
    margin: Dict[str, Any],
    leverage: Dict[str, Any],
    forecast: Dict[str, Any],
) -> List[str]:
    """Generate a list of human-readable scenario insights."""
    points: List[str] = []

    adj_growth = revenue.get("adjusted_growth")
    if adj_growth is not None:
        if adj_growth < 0:
            points.append(f"revenue expected to decline to {adj_growth:.1f}% growth under this scenario")
        else:
            points.append(f"revenue growth moderates to {adj_growth:.1f}% under this scenario")

    adj_margin = margin.get("adjusted_margin")
    margin_state = margin.get("margin_state", "unknown")
    if adj_margin is not None:
        if margin_state == "loss_making":
            points.append(f"profit margins compress to {adj_margin:.1f}% — operating loss territory")
        elif margin_state == "very_thin":
            points.append(f"margins thin to {adj_margin:.1f}% — minimal buffer against further shocks")
        else:
            points.append(f"net margin adjusts to {adj_margin:.1f}% under cost and demand pressure")

    stressed_level = leverage.get("stressed_risk_level", "unknown")
    at_risk = leverage.get("at_risk", False)
    if stressed_level != "unknown":
        if at_risk:
            points.append(
                f"leverage risk escalates to '{stressed_level}' — "
                "increased debt servicing burden under this scenario"
            )
        else:
            points.append(f"leverage stress remains at '{stressed_level}' — manageable under this scenario")

    direction = forecast.get("direction", "unknown")
    adj_confidence = forecast.get("adjusted_confidence")
    if direction in ("bearish", "bullish"):
        cf_str = f" (confidence: {adj_confidence:.0%})" if adj_confidence else ""
        points.append(f"forecast outlook turns {direction} under this scenario{cf_str}")
    elif direction == "neutral":
        points.append("forecast directional bias remains broadly neutral under this scenario")

    if not points:
        points.append(f"limited quantitative data available to assess '{scenario}' impact")

    return points
