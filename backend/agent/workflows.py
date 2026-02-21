"""
backend/agent/workflows.py

Research workflow orchestrators for the AI Research Agent.

Defines two workflows that select and sequence tool calls based on
the depth of analysis required:

  quick_research — fundamentals + risk summary (2 tool calls, fast)
  deep_research  — forecast + fundamentals + risk + peers + scenario + memo (6 steps)

Each workflow returns a structured dict containing raw tool data and a
synthesized insight report.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def quick_research(ticker: str) -> Dict[str, Any]:
    """
    Run the Quick Research workflow for a ticker.

    Calls two tools:
      1. get_fundamentals — core financial ratios, growth, strength
      2. get_risk_analysis — risk level and key risk signals

    Synthesizes findings into a concise structured insight report.
    Fast enough for near-real-time chat responses.

    Args:
        ticker (str): Validated uppercase stock symbol (e.g. 'AAPL').

    Returns:
        dict:
            workflow (str): 'quick_research'
            ticker (str)
            fundamentals (dict | None): Raw fundamentals data
            risk (dict | None): Raw risk data
            insights (dict): Synthesized insight report
            tool_errors (list[str]): Any tool-level errors
    """
    from backend.agent.tools import get_fundamentals, get_risk_analysis
    from backend.agent.synthesizer import synthesize_insights
    from backend.core.company_snapshot import generate_company_snapshot

    logger.info("[workflow:quick_research] Starting for %s", ticker)
    tool_errors = []

    # --- Tool calls ---
    fund_result = get_fundamentals(ticker)
    risk_result = get_risk_analysis(ticker)
    
    # Generate Snapshot
    snapshot_result = generate_company_snapshot(ticker)
    snapshot = snapshot_result.get("snapshot", [])

    fund_data = fund_result["data"] if fund_result["ok"] else None
    risk_data = risk_result["data"] if risk_result["ok"] else None

    if not fund_result["ok"]:
        tool_errors.append(f"fundamentals: {fund_result['error']}")
    if not risk_result["ok"]:
        tool_errors.append(f"risk: {risk_result['error']}")

    # --- Synthesize ---
    insights = synthesize_insights(
        ticker=ticker,
        fundamentals=fund_data,
        risk=risk_data,
    )

    logger.info(
        "[workflow:quick_research] Done for %s | outlook=%s",
        ticker, insights.get("outlook"),
    )

    return {
        "workflow": "quick_research",
        "ticker": ticker,
        "fundamentals": fund_data,
        "risk": risk_data,
        "insights": insights,
        "company_snapshot": snapshot,
        "tool_errors": tool_errors,
    }


def deep_research(
    ticker: str,
    scenario: str = "recession",
) -> Dict[str, Any]:
    """
    Run the Deep Research workflow for a ticker.

    Calls five tools sequentially:
      1. get_forecast       — price direction forecast (best-effort)
      2. get_fundamentals   — financial analysis
      3. get_risk_analysis  — risk intelligence
      4. get_peer_comparison — peer positioning
      5. run_scenario       — macroeconomic stress test

    All tools are independently fault-tolerant. Missing outputs are passed
    as None to the synthesizer, which handles them gracefully.

    Args:
        ticker (str): Validated uppercase stock symbol.
        scenario (str): Scenario for stress testing (default: 'recession').

    Returns:
        dict:
            workflow (str): 'deep_research'
            ticker (str)
            forecast (dict | None)
            fundamentals (dict | None)
            risk (dict | None)
            peer_comparison (dict | None)
            scenario (dict | None)
            insights (dict): Synthesized insight report
            investment_memo (dict): Investment memo (LLM or rule-based)
            tool_errors (list[str])
    """
    from backend.agent.tools import (
        get_forecast,
        get_fundamentals,
        get_risk_analysis,
        get_peer_comparison,
        run_scenario,
    )
    from backend.agent.synthesizer import synthesize_insights
    from backend.core.company_snapshot import generate_company_snapshot

    logger.info("[workflow:deep_research] Starting for %s | scenario=%s", ticker, scenario)
    tool_errors = []
    
    # Generate Snapshot
    snapshot_result = generate_company_snapshot(ticker)
    snapshot = snapshot_result.get("snapshot", [])

    # --- Step 1: Forecast ---
    fc_result   = get_forecast(ticker)
    fc_data     = fc_result["data"] if fc_result["ok"] else None
    if not fc_result["ok"]:
        tool_errors.append(f"forecast: {fc_result['error']}")

    # --- Step 2: Fundamentals ---
    fund_result = get_fundamentals(ticker)
    fund_data   = fund_result["data"] if fund_result["ok"] else None
    if not fund_result["ok"]:
        tool_errors.append(f"fundamentals: {fund_result['error']}")

    # --- Step 3: Risk ---
    risk_result = get_risk_analysis(ticker)
    risk_data   = risk_result["data"] if risk_result["ok"] else None
    if not risk_result["ok"]:
        tool_errors.append(f"risk: {risk_result['error']}")

    # --- Step 4: Peer comparison ---
    peer_result = get_peer_comparison(ticker)
    peer_data   = peer_result["data"] if peer_result["ok"] else None
    if not peer_result["ok"]:
        tool_errors.append(f"peer_comparison: {peer_result['error']}")

    # --- Step 5: Scenario ---
    scen_result = run_scenario(ticker, scenario)
    scen_data   = scen_result["data"] if scen_result["ok"] else None
    if not scen_result["ok"]:
        tool_errors.append(f"scenario: {scen_result['error']}")

    # --- Synthesize all outputs ---
    insights = synthesize_insights(
        ticker=ticker,
        fundamentals=fund_data,
        risk=risk_data,
        forecast=fc_data,
        peer=peer_data,
        scenario=scen_data,
    )

    # --- Step 6: Investment memo ---
    memo_data = {
        "ticker":           ticker,
        "insights":         insights,
        "fundamentals":     fund_data,
        "risk":             risk_data,
        "forecast":         fc_data,
        "peer_comparison":  peer_data,
        "scenario":         scen_data,
    }
    try:
        from backend.agent.memo_generator import generate_investment_memo
        investment_memo = generate_investment_memo(memo_data)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("[workflow:deep_research] Memo generation failed for %s: %s", ticker, exc)
        tool_errors.append(f"memo: {exc}")
        investment_memo = {}

    logger.info(
        "[workflow:deep_research] Done for %s | outlook=%s | memo=%s | errors=%d",
        ticker, insights.get("outlook"),
        investment_memo.get("generated_by", "none"), len(tool_errors),
    )

    return {
        "workflow": "deep_research",
        "ticker": ticker,
        "forecast": fc_data,
        "fundamentals": fund_data,
        "risk": risk_data,
        "peer_comparison": peer_data,
        "scenario": scen_data,
        "insights": insights,
        "company_snapshot": snapshot,
        "investment_memo": investment_memo,
        "tool_errors": tool_errors,
    }


def compare_companies_workflow(tickers: list[str], mode: str = "quick") -> Dict[str, Any]:
    from backend.agent.tools import get_peer_comparison
    from backend.agent.workflows import quick_research, deep_research
    from backend.core.company_snapshot import generate_company_snapshot
    logger.info("[workflow:compare_companies] Starting for %s | mode=%s", tickers, mode)
    tool_errors = []
    
    # Use the first ticker as base, others as peers
    base_ticker = tickers[0]
    
    # Get base research so UI cards render correctly
    base_result = deep_research(base_ticker) if mode == "deep" else quick_research(base_ticker)
    tool_errors.extend(base_result.get("tool_errors", []))
    insights = base_result.get("insights", {})
    
    peer_result = get_peer_comparison(base_ticker)
    peer_data = peer_result["data"] if peer_result["ok"] else None
    if not peer_result["ok"]:
        tool_errors.append(f"peer_comparison: {peer_result['error']}")
        
    insights["peer_comparison"] = peer_data
        
    # If the user asked for a broad comparison and only 1 ticker was extracted, append top 2 peers
    if len(tickers) == 1 and peer_data and peer_data.get("peer_group"):
        tickers.extend(peer_data["peer_group"][:2])
        
    # Generate Snapshot
    snapshot_result = generate_company_snapshot(tickers)
    
    return {
        "workflow": "compare_companies",
        "tickers": tickers,
        "peer_comparison": peer_data,
        "insights": insights,
        "company_snapshot": snapshot_result.get("snapshot", []),
        "tool_errors": tool_errors
    }



def bull_bear_workflow(ticker: str, mode: str = "quick") -> Dict[str, Any]:
    from backend.agent.memo_generator import generate_investment_memo
    from backend.agent.workflows import quick_research, deep_research
    
    logger.info("[workflow:bull_bear] Starting for %s | mode=%s", ticker, mode)
    tool_errors = []
    
    base_result = deep_research(ticker) if mode == "deep" else quick_research(ticker)
    tool_errors.extend(base_result.get("tool_errors", []))
    fund_data = base_result.get("fundamentals")
    insights = base_result.get("insights", {})
        
    memo_data = {
        "ticker": ticker, 
        "fundamentals": fund_data,
        "insights": insights,
        "risk": base_result.get("risk"),
        "scenario": base_result.get("scenario"),
        "forecast": base_result.get("forecast"),
        "peer_comparison": base_result.get("peer_comparison")
    }
    try:
        memo = generate_investment_memo(memo_data)
        insights["bull_case"] = memo.get("bull_case")
        insights["bear_case"] = memo.get("bear_case")
    except Exception as exc:
        logger.warning("[workflow:bull_bear] Memo generation failed: %s", exc)
        tool_errors.append(f"memo: {exc}")
        memo = {}
        
    return {
        "workflow": "bull_bear",
        "ticker": ticker,
        "memo": memo,
        "insights": insights,
        "company_snapshot": base_result.get("company_snapshot", []),
        "tool_errors": tool_errors
    }


def hidden_risks_workflow(ticker: str, mode: str = "quick") -> Dict[str, Any]:
    from backend.agent.workflows import quick_research, deep_research
    logger.info("[workflow:hidden_risks] Starting for %s | mode=%s", ticker, mode)
    tool_errors = []
    
    base_result = deep_research(ticker) if mode == "deep" else quick_research(ticker)
    tool_errors.extend(base_result.get("tool_errors", []))
    insights = base_result.get("insights", {})
    risk_data = base_result.get("risk")
        
    hidden_risks = risk_data.get("hidden_risks") if risk_data else []
    insights["hidden_risks"] = hidden_risks
    
    return {
        "workflow": "hidden_risks",
        "ticker": ticker,
        "risk_data": risk_data,
        "insights": insights,
        "company_snapshot": base_result.get("company_snapshot", []),
        "tool_errors": tool_errors
    }


def next_analysis_workflow(user_id: str, ticker: str, mode: str = "quick") -> Dict[str, Any]:
    from backend.memory.recommendations import suggest_next_analysis
    from backend.agent.workflows import quick_research, deep_research
    logger.info("[workflow:next_analysis] Starting for %s | mode=%s", ticker, mode)
    
    tool_errors = []
    base_result = deep_research(ticker) if mode == "deep" else quick_research(ticker)
    tool_errors.extend(base_result.get("tool_errors", []))
    insights = base_result.get("insights", {})
    
    # For now, just a placeholder lookup until integrated heavily with user memory
    suggested_steps = suggest_next_analysis({}, {"ticker": ticker, "workflow": "quick_research", "insights": insights, "raw_data": base_result.get("fundamentals", {})})
    
    insights["suggested_next_steps"] = suggested_steps
    
    return {
        "workflow": "next_analysis",
        "ticker": ticker,
        "insights": insights,
        "company_snapshot": base_result.get("company_snapshot", []),
        "tool_errors": tool_errors
    }
