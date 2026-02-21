"""
backend/core/plain_answer.py

Generates a 2-3 sentence plain-language answer to the user's structured query,
using the synthesized analytical results.
"""

import json
import logging
from typing import Dict, Any

from backend.agent.memo_generator import _call_llm, _get_provider

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """
You are a helpful and concise financial assistant. The user has asked the following financial research query.
Using the provided technical analysis data, answer their exact question in exactly 2 to 3 sentences. 

Rules:
1. Use simple, plain English that a retail investor would understand.
2. DO NOT use jargon, complex financial acronyms, or long paragraphs.
3. Your answer must be based purely on the Analysis Data provided. Do not hallucinate external facts.
4. Keep it directly relevant to what was asked. Focus on the bottom line.
5. Return your output STRICTLY as a JSON object matching this schema, with no markdown formatting:
{{
  "answer": "your 2-3 sentence explanation here"
}}

User Query: "{query}"

Analysis Data:
{analysis_text}
"""

def generate_plain_answer(query: str, analysis: Dict[str, Any]) -> str:
    """
    Generate a simple, plain-language answer explaining the results for the user's query.
    """
    logger.info("[plain_answer] Generating plain answer for query: %s", query)
    
    provider = _get_provider()
    
    tickers = analysis.get("tickers", [analysis.get("ticker", "UNKNOWN")])
    if not tickers:
        tickers = [analysis.get("ticker", "UNKNOWN")]
    t_str = " and ".join(tickers)
    
    intent = analysis.get("intent", "overview")
    insights = analysis.get("insights", {})

    def _get_fallback_text() -> str:
        if intent in ("compare", "compare_peers") and len(tickers) > 1:
            return f"Based on our quantitative data, comparing {t_str} reveals differing fundamental profiles. A full comparative explanation requires an active LLM provider."
        elif intent == "bullbear":
            return f"The bull and bear thesis for {t_str} requires an LLM to synthesize the underlying data into plain language."
        elif intent == "hidden_risks":
            return f"Hidden risk analysis for {t_str} found some signals, but requires an active LLM provider for detailed interpretation."
        elif intent == "forecast_only":
            trend = insights.get("forecast_trend", "unavailable")
            return f"Our quantitative model currently signals a {trend} price trend for {t_str}. Enable an LLM for further context."
        else:
            outlook = insights.get("outlook", "neutral").replace('_', ' ')
            return f"Based on the processed analysis, the overall structural outlook for {t_str} is currently assessed as {outlook}."
    
    # Fallback if no LLM
    if provider == "disabled":
        return _get_fallback_text()
        
    # Serialize the minimal amount of data needed to give context
    context_data = {
        "tickers": tickers,
        "intent": intent,
        "strengths": insights.get("strengths", []),
        "risks": insights.get("risks", []),
        "outlook": insights.get("outlook", "neutral"),
        "scenario_impact": insights.get("scenario_impact", ""),
        "peer_comparison_summary": (analysis.get("raw_data", {}).get("peer_comparison") or {}).get("summary", [])
    }
    
    prompt = PROMPT_TEMPLATE.format(
        query=query,
        analysis_text=json.dumps(context_data, indent=2)
    )
    
    try:
        response_text = _call_llm(provider, prompt)
        
        # Parse JSON
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            
        parsed = json.loads(cleaned)
        answer = parsed.get("answer", "")
        
        if not answer:
            raise ValueError("LLM returned an empty answer")
            
        return answer
        
    except Exception as e:
        logger.warning("[plain_answer] LLM plain answer generation failed: %s", e)
        return _get_fallback_text()
