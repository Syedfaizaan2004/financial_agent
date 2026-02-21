"""
backend/core/company_snapshot.py

Generates a concise 5-bullet company snapshot using yfinance data and the LLM.
"""

import json
import logging
from typing import Dict, Any, Union

import yfinance as yf

from backend.agent.memo_generator import _call_llm, _get_provider

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """
You are an expert financial analyst. Please summarize the following company information into exactly 5 concise bullet points.
If there are multiple companies, compare their core businesses and competitive positions.
The points must cover:
1. Core business
2. Revenue drivers
3. Strategic advantage (or strength)
4. Competitive position
5. Major exposure risks

Do not include marketing language. Keep it highly factual and decision-relevant.
Return the output strictly in JSON format matching this schema:
{{
  "snapshot": [
    "bullet 1",
    "bullet 2",
    "bullet 3",
    "bullet 4",
    "bullet 5"
  ]
}}

Company Info:
{info_text}
"""

def generate_company_snapshot(tickers: Union[str, list[str]]) -> Dict[str, Any]:
    """
    Fetch company info using yfinance and generate a 5-bullet snapshot.
    Supports a single ticker or a list of tickers.
    """
    if isinstance(tickers, str):
        tickers = [tickers]
        
    logger.info("[company_snapshot] Generating snapshot for %s", tickers)
    
    # 1. Fetch info from yfinance
    summary_text = ""
    fallback_bullets = []
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Build prompt payload
            summary_text += (
                f"--- {ticker} ---\n"
                f"Business Summary: {info.get('longBusinessSummary', 'N/A')}\n"
                f"Sector: {info.get('sector', 'N/A')}\n"
                f"Industry: {info.get('industry', 'N/A')}\n\n"
            )
            fallback_bullets.append(f"{ticker} operates in the {info.get('sector', 'Unknown')} sector and is part of the {info.get('industry', 'Unknown')} industry.")
        except Exception as e:
            logger.warning("[company_snapshot] Failed to fetch yfinance data for %s: %s", ticker, e)
            fallback_bullets.append(f"Core business data for {ticker} is currently unavailable.")

    # 2. Call LLM
    provider = _get_provider()
    if provider == "disabled":
        # Fallback if LLM is disabled
        bullets = fallback_bullets
        if len(tickers) == 1:
            bullets.extend([
                "Detailed revenue drivers require an active LLM for processing.",
                "Strategic and competitive analysis is unavailable in offline mode.",
                "Major exposure risks are not assessed."
            ])
        else:
            bullets.extend([
                "Detailed cross-company comparison requires an active LLM.",
                "Strategic advantages cannot be actively contrasted offline.",
                "Major exposure risks are not fully assessed."
            ])
        return {"snapshot": bullets[:5]}
        
    prompt = PROMPT_TEMPLATE.format(info_text=summary_text)
    
    try:
        response_text = _call_llm(provider, prompt)
        
        # Parse JSON
        cleaned = response_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            
        parsed = json.loads(cleaned)
        snapshot = parsed.get("snapshot", [])
        
        # Ensure it's roughly 5 items
        if not snapshot or not isinstance(snapshot, list):
            raise ValueError("Invalid LLM response format for snapshot")
            
        return {"snapshot": snapshot[:5]}
        
    except Exception as e:
        logger.warning("[company_snapshot] LLM snapshot generation failed: %s", e)
        # Fallback if LLM fails
        bullets = fallback_bullets.copy()
        if len(tickers) == 1:
            bullets.extend([
                "Detailed revenue drivers require an active LLM for processing.",
                "Strategic and competitive analysis is unavailable in offline mode.",
                "Major exposure risks are not assessed."
            ])
        else:
            bullets.extend([
                "Detailed cross-company comparison requires an active LLM.",
                "Strategic advantages cannot be actively contrasted offline.",
                "Major exposure risks are not fully assessed."
            ])
        return {"snapshot": bullets[:5]}
