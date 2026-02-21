"""
backend/demo/flow.py

Guided demo flow steps for the Financial Research Agent presentation.

Provides a structured sequence of demo steps that a presenter can
follow to showcase all platform capabilities in a logical order.

Each step includes:
  - id: unique step identifier
  - title: display title
  - description: what to demonstrate
  - feature: which UI component / API to highlight
  - query: example query to run (if applicable)
  - hint: short text for the audience
"""

from __future__ import annotations

from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Demo step definitions
# ---------------------------------------------------------------------------

DEMO_STEPS: List[Dict[str, Any]] = [
    {
        "step":        1,
        "id":          "overview",
        "title":       "AI Research Overview",
        "description": "Run a quick research query to show the AI agent pipeline in action.",
        "feature":     "AIInsightsPanel + SummaryCards",
        "query":       "Quick summary of AAPL",
        "hint":        "The agent detects intent, extracts the ticker, and orchestrates 4 analysis tools automatically.",
        "ticker":      "AAPL",
        "workflow":    "quick_research",
    },
    {
        "step":        2,
        "id":          "risk_transparency",
        "title":       "Risk & Transparency",
        "description": "Show risk classification, confidence score, and contradiction detection.",
        "feature":     "ConfidenceIndicator + RiskAlerts",
        "query":       "Analyze risks for TSLA",
        "hint":        "Confidence score explains how reliable this analysis is. Contradictions flag signals that conflict.",
        "ticker":      "TSLA",
        "workflow":    "quick_research",
    },
    {
        "step":        3,
        "id":          "forecast",
        "title":       "Quantitative Forecast",
        "description": "Demonstrate TFT & XGBoost ensemble forecast with uncertainty bands.",
        "feature":     "ForecastBand",
        "query":       "Forecast for MSFT",
        "hint":        "The model ensemble produces directional probability with an uncertainty band — wider = less certain.",
        "ticker":      "MSFT",
        "workflow":    "forecast_only",
    },
    {
        "step":        4,
        "id":          "scenario",
        "title":       "Scenario Stress Testing",
        "description": "Run a recession scenario to show macro impact analysis.",
        "feature":     "ScenarioSelector",
        "query":       "What happens to AAPL in a recession?",
        "hint":        "Scenario engine adjusts revenue growth, margin, and risk outlook under macro stress conditions.",
        "ticker":      "AAPL",
        "workflow":    "scenario_stress",
    },
    {
        "step":        5,
        "id":          "peer_comparison",
        "title":       "Peer Comparison",
        "description": "Compare AAPL against MSFT, GOOGL and other sector peers.",
        "feature":     "PeerComparison",
        "query":       "Compare Apple and Microsoft",
        "hint":        "Peer benchmarking highlights metrics where the company outperforms or lags its competitors.",
        "ticker":      "AAPL",
        "workflow":    "compare_peers",
    },
    {
        "step":        6,
        "id":          "deep_research",
        "title":       "Full Deep Research",
        "description": "Show the complete 5-tool deep research pipeline with investment memo.",
        "feature":     "Full dashboard + InvestmentMemo",
        "query":       "Deep analysis of MSFT including risks and peers",
        "hint":        "Deep research runs all 5 tools in sequence: forecast → fundamentals → risk → peers → scenario.",
        "ticker":      "MSFT",
        "workflow":    "deep_research",
    },
    {
        "step":        7,
        "id":          "personalization",
        "title":       "Personalized Insights",
        "description": "Switch to conservative profile and show adapted insights.",
        "feature":     "PersonalizedInsights + PreferencesPanel",
        "query":       "Quick summary of AAPL",
        "hint":        "The memory system adapts research emphasis based on risk profile, time horizon, and preferred metrics.",
        "ticker":      "AAPL",
        "workflow":    "quick_research",
    },
]


def get_demo_steps() -> List[Dict[str, Any]]:
    """
    Return the full ordered list of demo flow steps.

    Returns:
        list[dict]: Each dict has step, id, title, description, feature,
                    query, hint, ticker, workflow fields.
    """
    return DEMO_STEPS


def get_demo_step(step_id: str) -> Dict[str, Any] | None:
    """
    Retrieve a specific demo step by its id.

    Args:
        step_id (str): Step id (e.g. 'forecast', 'scenario').

    Returns:
        dict | None: Step definition or None if not found.
    """
    return next((s for s in DEMO_STEPS if s["id"] == step_id), None)


def get_demo_queries() -> List[str]:
    """Return all demo query strings in order."""
    return [s["query"] for s in DEMO_STEPS]


def get_demo_tickers_from_flow() -> List[str]:
    """Return unique tickers referenced in the demo flow."""
    seen, result = set(), []
    for s in DEMO_STEPS:
        t = s["ticker"]
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result
