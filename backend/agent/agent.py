"""
backend/agent/agent.py

Main AI Research Agent orchestrator.

Ties together intent detection, ticker extraction, workflow selection,
and result formatting into a single callable entry point.

Pipeline:
  1. Detect intent from user query
  2. Extract ticker symbol from query
  3. Route to appropriate workflow
  4. Return structured agent response

Workflow routing table:
  quick_research  → workflows.quick_research()
  deep_research   → workflows.deep_research()
  compare_peers   → workflows.deep_research() (peer-focused)
  scenario_stress → run scenario tool directly + synthesize
  forecast_only   → forecast tool only + minimal synthesis
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Scenario keyword → scenario type mapping
# ---------------------------------------------------------------------------
_SCENARIO_MAP = {
    "recession":      "recession",
    "inflation":      "high_inflation",
    "rate hike":      "rate_hike",
    "interest rate":  "rate_hike",
    "growth slowdown": "growth_slowdown",
    "slowdown":       "growth_slowdown",
}


def run_research_agent(
    query: str,
    user_id: str = "default",
    mode: str = "quick",
    analysis_type: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run the AI Research Agent for a natural-language query.

    Detects intent, extracts ticker, selects workflow, runs tools,
    applies user personalization, and returns a structured response.

    Args:
        query (str): Raw user research query.
        user_id (str): Optional user identifier for personalization.
                       Defaults to 'default' (anonymous user).

    Returns:
        dict:
            query (str): Original query
            ticker (str | None): Extracted ticker
            intent (str): Detected intent
            intent_confidence (str): 'high' | 'low' | 'fallback'
            workflow (str): Workflow used
            confidence (float): Composite confidence score 0.0–1.0
            contradictions (list): Detected conflicting signals
            uncertainties (list): Uncertainty / data quality flags
            insights (dict): Synthesized insights
            investment_memo (dict | None): Investment memo (deep_research only)
            raw_data (dict): Full raw tool output data
            agent_errors (list[str]): Non-fatal errors
            status (str): 'ok' | 'partial' | 'failed'

    Raises:
        ValueError: If the query is empty.
    """
    t0_agent = time.perf_counter()

    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    from backend.utils.cache import get_cached_result, cache_result, key_agent
    from backend.agent.intent import detect_intent, extract_ticker
    from backend.agent import workflows
    from backend.agent.tools import get_forecast, run_scenario
    from backend.agent.synthesizer import synthesize_insights
    from backend.agent.utils import extract_tickers

    # -----------------------------------------------------------------------
    # Step 0: Intent + ticker detection & Caching
    # -----------------------------------------------------------------------
    intent_result = detect_intent(query)
    intent        = analysis_type if analysis_type else intent_result["intent"]
    confidence    = "override" if analysis_type else intent_result["confidence"]

    tickers = extract_tickers(query)
    if not tickers:
        single_ticker = extract_ticker(query)
        if single_ticker:
            tickers = [single_ticker]
            
    ticker = tickers[0] if tickers else None

    # Check caches (General TTL)
    cached_response: Optional[Dict[str, Any]] = None

    if ticker:
        canonical_search = ticker.upper().strip()
        # General TTL Cache Check (include mode to prevent quick/deep collisions)
        cache_key_val = f"{intent}:{mode}"
        cached_response = get_cached_result(key_agent(canonical_search, cache_key_val))

    if cached_response:
        elapsed_agent = (time.perf_counter() - t0_agent) * 1000
        logger.info("[agent] Cache HIT for %s | ms=%.2f", ticker_candidate, elapsed_agent)
        # Add metadata for UI
        cached_response["_performance"] = {
            "total_ms": round(elapsed_agent, 2),
            "source": "cache"
        }
        return cached_response

    # -----------------------------------------------------------------------
    # Step 1: Load user preferences (non-blocking)
    # -----------------------------------------------------------------------
    user_prefs: Dict[str, Any] = {}
    try:
        from backend.db.session import SessionLocal
        from backend.memory.crud import get_preferences
        with SessionLocal() as _db:
            user_prefs = get_preferences(_db, user_id=user_id)
    except Exception as _mem_exc:  # pylint: disable=broad-except
        logger.warning("[agent] Memory lookup failed for %s: %s", user_id, _mem_exc)

    logger.info(
        "[agent] Query='%.80s' | intent=%s (conf=%s) | mode=%s | tickers=%s",
        query, intent, confidence, mode, tickers,
    )

    # -----------------------------------------------------------------------
    # Step 2: Validate ticker
    # -----------------------------------------------------------------------
    agent_errors = []
    if not ticker:
        return _no_ticker_response(query, intent, confidence)

    canonical = ticker.upper().strip()

    # -----------------------------------------------------------------------
    # Step 3: Detect scenario (for scenario_stress intent)
    # -----------------------------------------------------------------------
    scenario = _detect_scenario(query)

    # -----------------------------------------------------------------------
    # Step 4: Route to workflow
    # -----------------------------------------------------------------------
    raw_data: Dict[str, Any] = {}
    insights: Dict[str, Any] = {}
    investment_memo: Dict[str, Any] = {}
    company_snapshot: list = []
    workflow_used = ""
    final_tickers = tickers

    # Always use quick mode if explicitly requested, unless it's a specific analysis type that requires deep execution
    if mode == "quick" and not analysis_type:
        result       = workflows.quick_research(canonical)
        raw_data     = {"fundamentals": result["fundamentals"], "risk": result["risk"]}
        insights     = result["insights"]
        company_snapshot = result.get("company_snapshot", [])
        investment_memo = {}
        agent_errors.extend(result.get("tool_errors", []))
        workflow_used = "quick_research"
    else:
        if intent == "forecast_only":
            fc_result  = get_forecast(canonical)
            fc_data    = fc_result["data"] if fc_result["ok"] else None
            if not fc_result["ok"]:
                agent_errors.append(fc_result["error"])
            raw_data["forecast"] = fc_data
            insights = synthesize_insights(ticker=canonical, forecast=fc_data)
            investment_memo: Dict[str, Any] = {}
            workflow_used = "forecast_only"
    
        elif intent == "scenario_stress" or intent == "scenario":
            scen_result = run_scenario(canonical, scenario)
            scen_data   = scen_result["data"] if scen_result["ok"] else None
            if not scen_result["ok"]:
                agent_errors.append(scen_result["error"])
            # Also grab quick fundamentals for context
            quick = workflows.quick_research(canonical)
            raw_data = {
                "scenario": scen_data,
                "fundamentals": quick.get("fundamentals"),
                "risk": quick.get("risk"),
            }
            insights = synthesize_insights(
                ticker=canonical,
                fundamentals=raw_data["fundamentals"],
                risk=raw_data["risk"],
                scenario=scen_data,
            )
            company_snapshot = quick.get("company_snapshot", [])
            investment_memo = {}
            workflow_used = f"scenario_stress:{scenario}"
            
        elif intent in ("compare_peers", "compare"):
            result = workflows.compare_companies_workflow(tickers, mode=mode) if len(tickers) > 1 else workflows.compare_companies_workflow([canonical], mode=mode)
            
            raw_data = {"peer_comparison": result.get("peer_comparison")}
            insights = result.get("insights", {})
            company_snapshot = result.get("company_snapshot", [])
            agent_errors.extend(result.get("tool_errors", []))
            workflow_used = "compare_peers"
            final_tickers = result.get("tickers", tickers)
            
        elif intent == "bullbear":
            result = workflows.bull_bear_workflow(canonical, mode=mode)
            raw_data = {"memo": result.get("memo")}
            insights = result.get("insights", {})
            company_snapshot = result.get("company_snapshot", [])
            investment_memo = result.get("memo") or {}
            agent_errors.extend(result.get("tool_errors", []))
            workflow_used = "bullbear"
            
        elif intent == "hidden_risks":
            result = workflows.hidden_risks_workflow(canonical, mode=mode)
            raw_data = {"risk_data": result.get("risk_data")}
            insights = result.get("insights", {})
            company_snapshot = result.get("company_snapshot", [])
            agent_errors.extend(result.get("tool_errors", []))
            workflow_used = "hidden_risks"
            
        elif intent == "next_analysis":
            result = workflows.next_analysis_workflow(user_id, canonical, mode=mode)
            raw_data = {}
            insights = result.get("insights", {})
            company_snapshot = result.get("company_snapshot", [])
            agent_errors.extend(result.get("tool_errors", []))
            workflow_used = "next_analysis"
    
        else: # deep_research
            result       = workflows.deep_research(canonical, scenario=scenario)
            raw_data     = {k: result[k] for k in
                            ("forecast", "fundamentals", "risk", "peer_comparison", "scenario")}
            insights     = result["insights"]
            company_snapshot = result.get("company_snapshot", [])
            investment_memo = result.get("investment_memo") or {}
            agent_errors.extend(result.get("tool_errors", []))
            workflow_used = "deep_research"

    # -----------------------------------------------------------------------
    # Step 5: Apply personalization
    # -----------------------------------------------------------------------
    if user_prefs:
        try:
            from backend.memory.personalization import apply_user_preferences
            response_for_personalization = {
                "ticker":    canonical,
                "workflow":  workflow_used,
                "insights":  insights,
                "raw_data":  raw_data,
            }
            personalized = apply_user_preferences(response_for_personalization, user_prefs)
            insights = personalized.get("insights", insights)
        except Exception as _p_exc:  # pylint: disable=broad-except
            logger.warning("[agent] Personalization failed: %s", _p_exc)

    # -----------------------------------------------------------------------
    # Step 6: Generate next-analysis recommendations
    # -----------------------------------------------------------------------
    next_analysis: list = []
    if workflow_used != "next_analysis":
        try:
            from backend.memory.recommendations import suggest_next_analysis
            response_snapshot = {
                "ticker":   canonical,
                "workflow": workflow_used,
                "insights":  insights,
                "raw_data": raw_data,
            }
            next_analysis = suggest_next_analysis(user_prefs, response_snapshot)
        except Exception as _r_exc:  # pylint: disable=broad-except
            logger.warning("[agent] Recommendations failed: %s", _r_exc)
    else:
        next_analysis = insights.get("suggested_next_steps", [])

    # -----------------------------------------------------------------------
    # Step 7: Store query in session memory (non-blocking)
    # -----------------------------------------------------------------------
    try:
        from backend.memory.session_memory import store_last_query
        store_last_query(user_id=user_id, query=query, ticker=canonical, intent=intent)
    except Exception as _sq_exc:  # pylint: disable=broad-except
        logger.warning("[agent] Session query store failed: %s", _sq_exc)

    # -----------------------------------------------------------------------
    # Step 8: Determine status
    # -----------------------------------------------------------------------
    status = "ok"
    if agent_errors:
        status = "partial" if raw_data else "failed"

    logger.info(
        "[agent] Complete for %s | intent=%s | workflow=%s | status=%s",
        canonical, intent, workflow_used, status,
    )

    elapsed_total = (time.perf_counter() - t0_agent) * 1000

    # -----------------------------------------------------------------------
    # Step 9: Generate Plain-Language Answer
    # -----------------------------------------------------------------------
    plain_answer = ""
    try:
        from backend.core.plain_answer import generate_plain_answer
        plain_answer = generate_plain_answer(query, {
            "tickers": final_tickers,
            "ticker": canonical,
            "intent": intent,
            "insights": insights,
            "raw_data": raw_data
        })
    except Exception as pa_exc:  # pylint: disable=broad-except
        logger.warning("[agent] Plain answer generation failed: %s", pa_exc)

    try:
        from backend.agent.memo_generator import _get_provider, _get_model
        provider = _get_provider()
        model = _get_model(provider) if provider != "disabled" else "none"
    except Exception:
        provider = "unknown"
        model = "unknown"

    response = {
        "query":             query,
        "user_id":           user_id,
        "ticker":            canonical,
        "intent":            intent,
        "intent_confidence": confidence,
        "workflow":          workflow_used,
        "confidence":        insights.get("confidence", 0.60),
        "contradictions":    insights.get("contradictions", []),
        "uncertainties":     insights.get("uncertainties", []),
        "company_snapshot":  company_snapshot,
        "plain_answer":      plain_answer,
        "insights":          insights,
        "investment_memo":   investment_memo,
        "raw_data":          raw_data,
        "next_analysis":     next_analysis,
        "agent_errors":      agent_errors,
        "status":            status,
        "llm_provider":      provider,
        "llm_model":         model,
        "_performance": {
            "total_ms": round(elapsed_total, 2),
            "source": "live"
        }
    }

    # Store in general TTL cache
    try:
        cache_key_val = f"{workflow_used}:{mode}"
        cache_result(key_agent(canonical, cache_key_val), response, ttl=180)
    except Exception as _ce:
        logger.warning("[agent] Cache store failed: %s", _ce)

    return response


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _detect_scenario(query: str) -> str:
    """Extract scenario from query; defaults to 'recession'."""
    q = query.lower()
    for phrase, scenario in _SCENARIO_MAP.items():
        if phrase in q:
            return scenario
    return "recession"


def _no_ticker_response(
    query: str, intent: str, confidence: str
) -> Dict[str, Any]:
    """Return a structured response when no ticker could be extracted."""
    return {
        "query": query,
        "ticker": None,
        "intent": intent,
        "intent_confidence": confidence,
        "workflow": "none",
        "insights": {
            "ticker": None,
            "strengths": [],
            "risks": [],
            "opportunities": [],
            "outlook": "unknown",
            "forecast_trend": "unavailable",
            "key_metrics": {},
            "scenario_impact": "",
            "peer_positioning": "",
        },
        "raw_data": {},
        "agent_errors": [
            "Could not extract a stock ticker from the query. "
            "Please include a ticker symbol (e.g. 'AAPL', 'TSLA', 'TCS.NS')."
        ],
        "status": "failed",
    }
