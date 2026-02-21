"""
backend/agent/tools.py

Agent-callable tool wrappers for the AI Research Agent.

Each function wraps one analysis module and returns a normalized dict that
the agent orchestrator and synthesizer can process uniformly.

Design rules:
  - Every tool returns {"ok": bool, "data": dict | None, "error": str | None}
  - Tools never raise — errors are captured and returned in the envelope
  - All tools accept validated uppercase tickers (caller's responsibility)
  - Tools are stateless — no cross-tool caching here
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Response envelope helper
# ---------------------------------------------------------------------------

def _ok(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"ok": True, "data": data, "error": None}


def _err(msg: str) -> Dict[str, Any]:
    return {"ok": False, "data": None, "error": msg}


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def get_forecast(ticker: str) -> Dict[str, Any]:
    """
    Retrieve the ensemble price-direction forecast for a stock ticker.

    Calls the TFT + XGBoost ensemble module. Returns a 'not_supported'
    envelope if the ticker is outside the model universe.

    Args:
        ticker (str): Validated uppercase stock symbol.

    Returns:
        dict: Tool response envelope:
            ok    (bool)    : True if forecast was produced
            data  (dict)    : Forecast output dict, or None
            error (str|None): Error description on failure
    """
    logger.info("[tool:get_forecast] %s", ticker)
    try:
        from backend.forecasting.utils import is_supported_ticker
        if not is_supported_ticker(ticker):
            return _ok({
                "supported": False,
                "message": f"'{ticker}' is outside the forecasting model universe.",
            })
        from backend.forecasting.ensemble import generate_forecast
        result = generate_forecast(ticker)
        result["supported"] = True
        return _ok(result)
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("[tool:get_forecast] %s — %s", ticker, exc)
        return _err(f"Forecast failed: {type(exc).__name__}: {exc}")


def get_fundamentals(ticker: str) -> Dict[str, Any]:
    """
    Retrieve fundamental financial analysis for a stock ticker.

    Calls the full financial analyzer pipeline (KPIs, growth, strength).

    Args:
        ticker (str): Validated uppercase stock symbol.

    Returns:
        dict: Tool response envelope with fundamental analysis output.
    """
    logger.info("[tool:get_fundamentals] %s", ticker)
    try:
        from backend.core.financial_analyzer import analyze_company_fundamentals
        return _ok(analyze_company_fundamentals(ticker))
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("[tool:get_fundamentals] %s — %s", ticker, exc)
        return _err(f"Fundamentals failed: {type(exc).__name__}: {exc}")


def get_risk_analysis(ticker: str) -> Dict[str, Any]:
    """
    Retrieve the full risk intelligence report for a stock ticker.

    Covers leverage, liquidity, earnings stability, cash flow, and
    hidden compound risks.

    Args:
        ticker (str): Validated uppercase stock symbol.

    Returns:
        dict: Tool response envelope with risk analysis output.
    """
    logger.info("[tool:get_risk_analysis] %s", ticker)
    try:
        from backend.risk_engine.risk_analysis import analyze_company_risks
        return _ok(analyze_company_risks(ticker))
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("[tool:get_risk_analysis] %s — %s", ticker, exc)
        return _err(f"Risk analysis failed: {type(exc).__name__}: {exc}")


def get_peer_comparison(ticker: str) -> Dict[str, Any]:
    """
    Retrieve quantitative peer comparison for a stock ticker.

    Fetches peers from the curated peer map and runs metric-by-metric
    positioning (valuation, profitability, growth, leverage).

    Args:
        ticker (str): Validated uppercase stock symbol.

    Returns:
        dict: Tool response envelope with comparison output.
    """
    logger.info("[tool:get_peer_comparison] %s", ticker)
    try:
        from backend.core.peer_fetcher import get_peer_group
        from backend.core.peer_comparison import compare_with_peers
        peers = get_peer_group(ticker)
        if not peers:
            return _ok({
                "peer_group": [],
                "summary": [f"No peer group defined for '{ticker}'."],
            })
        return _ok(compare_with_peers(ticker, peers))
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("[tool:get_peer_comparison] %s — %s", ticker, exc)
        return _err(f"Peer comparison failed: {type(exc).__name__}: {exc}")


def run_scenario(ticker: str, scenario: str = "recession") -> Dict[str, Any]:
    """
    Run a macroeconomic scenario stress test for a stock ticker.

    Supported scenarios: high_inflation, recession, rate_hike, growth_slowdown.

    Args:
        ticker (str): Validated uppercase stock symbol.
        scenario (str): Scenario key (default: 'recession').

    Returns:
        dict: Tool response envelope with scenario analysis output.
    """
    logger.info("[tool:run_scenario] %s / %s", ticker, scenario)
    try:
        from backend.risk_engine.scenario_engine import run_scenario_analysis
        return _ok(run_scenario_analysis(ticker, scenario))
    except ValueError as exc:
        return _err(f"Invalid scenario: {exc}")
    except Exception as exc:  # pylint: disable=broad-except
        logger.error("[tool:run_scenario] %s/%s — %s", ticker, scenario, exc)
        return _err(f"Scenario analysis failed: {type(exc).__name__}: {exc}")
