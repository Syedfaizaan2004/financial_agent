import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

def compare_companies_workflow(tickers: List[str]) -> Dict[str, Any]:
    from backend.agent.tools import get_peer_comparison
    
    if not tickers:
        return {"workflow": "compare", "error": "No tickers provided."}
        
    base_ticker = tickers[0]
    result = get_peer_comparison(base_ticker)
    
    return {
        "workflow": "compare",
        "ticker": base_ticker,
        "tickers": tickers,
        "peer_comparison": result.get("data") if result.get("ok") else None,
        "tool_errors": [result.get("error")] if not result.get("ok") else []
    }

def bull_bear_workflow(ticker: str) -> Dict[str, Any]:
    from backend.agent.memo_generator import generate_investment_memo
    from backend.agent.tools import get_fundamentals
    
    fund_result = get_fundamentals(ticker)
    memo_data = {
        "ticker": ticker,
        "fundamentals": fund_result.get("data") if fund_result.get("ok") else None,
        "insights": {"outlook": "neutral"} # Minimal required insights
    }
    
    memo = generate_investment_memo(memo_data)
    
    return {
        "workflow": "bullbear",
        "ticker": ticker,
        "bull_case": memo.get("bull_case", "Bull case not available."),
        "bear_case": memo.get("bear_case", "Bear case not available."),
        "memo": memo,
        "tool_errors": [fund_result.get("error")] if not fund_result.get("ok") else []
    }

def hidden_risks_workflow(ticker: str) -> Dict[str, Any]:
    from backend.agent.tools import get_risk_analysis
    
    risk_result = get_risk_analysis(ticker)
    risk_data = risk_result.get("data", {}) if risk_result.get("ok") else {}
    
    # Extract hidden/overlooked risks if available, otherwise fallback to key risks
    hidden_risks = risk_data.get("hidden_risks", risk_data.get("key_risks", []))
    
    return {
        "workflow": "hidden_risks",
        "ticker": ticker,
        "hidden_risks": hidden_risks,
        "risk_data": risk_data,
        "tool_errors": [risk_result.get("error")] if not risk_result.get("ok") else []
    }

def next_analysis_workflow(user_id: str, ticker: str) -> Dict[str, Any]:
    # Placeholder for personalized next steps based on memory
    from backend.memory.manager import get_user_memory
    
    memory = get_user_memory(user_id) if user_id else {}
    
    # Generate some suggested next steps
    next_steps = [
        f"Compare {ticker} with its closest peers",
        f"Run a scenario stress test for {ticker} under recession",
        f"Review the full investment memo for {ticker}"
    ]
    
    return {
        "workflow": "next_analysis",
        "ticker": ticker,
        "user_id": user_id,
        "suggested_next_steps": next_steps,
        "tool_errors": []
    }
