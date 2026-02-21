"""
backend/agent/intent.py

Keyword-based intent detection for the AI Research Agent.

Classifies a natural-language query into one of five intent types using
a scored keyword matching approach. No LLM or NLP libraries required.

Intent types:
  quick_research   — basic fundamentals + risk summary (fast)
  deep_research    — full multi-tool analysis (thorough)
  compare_peers    — peer comparison focus
  scenario_stress  — scenario / stress testing focus
  forecast_only    — price forecast focus

Detection strategy:
  Each intent has a list of trigger keywords. The query is lowercased,
  and the intent with the highest keyword match count wins. Ties are
  broken by intent priority order. Falls back to 'quick_research'.
"""

from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intent keyword tables
# ---------------------------------------------------------------------------
_INTENT_KEYWORDS: Dict[str, List[str]] = {
    "forecast_only": [
        "forecast", "predict", "prediction", "price target",
        "direction", "movement", "will it go up", "will it rise",
        "outlook price", "xgboost", "tft", "model",
    ],
    "compare_peers": [
        "compare", "comparison", "versus", " vs ", "peers", "competitors",
        "relative", "better than", "sector comparison", "benchmark",
        "how does it compare", "against peers", "compare companies"
    ],
    "scenario_stress": [
        "scenario", "stress", "recession", "inflation", "rate hike",
        "interest rate", "downturn", "growth slowdown", "macro",
        "what if", "impact of", "sensitivity", "base case",
    ],
    "deep_research": [
        "deep", "comprehensive", "full analysis", "detailed", "complete",
        "everything about", "thorough", "in depth", "analyst report",
        "research report", "all metrics", "complete picture",
    ],
    "quick_research": [
        "quick", "summary", "brief", "overview", "basics",
        "what is", "give me", "tell me", "show me", "key metrics",
        "snapshot", "at a glance",
    ],
    "bullbear": [
        "bull vs bear", "bull and bear", "bull case", "bear case",
        "bull/bear", "thesis", "arguments for and against"
    ],
    "hidden_risks": [
        "hidden risks", "overlooked risks", "nuanced risks",
        "what am i missing", "blind spots", "exotic risks",
        "tail risks"
    ],
    "next_analysis": [
        "next analysis", "suggest next steps", "what should i analyze next",
        "recommendation", "what to do next", "follow up"
    ]
}

# Priority order (higher priority = earlier in list)
_PRIORITY_ORDER = [
    "next_analysis",
    "hidden_risks",
    "bullbear",
    "scenario_stress",
    "compare_peers",
    "forecast_only",
    "deep_research",
    "quick_research",
]


def detect_intent(query: str) -> Dict[str, Any]:
    """
    Classify a natural-language research query into an intent type.

    Uses scored keyword matching — the intent with the most keyword hits wins.
    Ties are broken by intent priority order.

    Args:
        query (str): Raw user input string.

    Returns:
        dict:
            intent (str): Detected intent type
            confidence (str): 'high' (≥2 hits) | 'low' (1 hit) | 'fallback' (0 hits)
            matched_keywords (list[str]): Keywords that triggered the intent
            scores (dict[str, int]): Hit counts per intent
    """
    if not query or not query.strip():
        return _make_result("quick_research", "fallback", [], {})

    normalized = query.lower()
    # Tokenise loosely — keep spaces for phrase matching
    scores: Dict[str, int] = {intent: 0 for intent in _INTENT_KEYWORDS}
    matched: Dict[str, List[str]] = {intent: [] for intent in _INTENT_KEYWORDS}

    for intent, keywords in _INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in normalized:
                scores[intent] += 1
                matched[intent].append(kw)

    # Find best intent respecting priority on ties
    best_intent = "quick_research"
    best_score  = 0
    for intent in _PRIORITY_ORDER:
        if scores[intent] > best_score:
            best_score  = scores[intent]
            best_intent = intent
        elif scores[intent] == best_score and best_score > 0:
            # Same score — lower-priority intent already set; keep it
            pass

    confidence = (
        "high"     if best_score >= 2 else
        "low"      if best_score == 1 else
        "fallback"
    )

    logger.info(
        "Intent detected: %s (confidence=%s, score=%d) for query: '%.60s'",
        best_intent, confidence, best_score, query,
    )

    return _make_result(best_intent, confidence, matched[best_intent], scores)


# ---------------------------------------------------------------------------
# Company name → ticker mapping (common well-known names users type)
# ---------------------------------------------------------------------------
_COMPANY_NAME_MAP: Dict[str, str] = {
    # US mega-cap tech
    "google":    "GOOGL",
    "alphabet":  "GOOGL",
    "apple":     "AAPL",
    "microsoft": "MSFT",
    "amazon":    "AMZN",
    "meta":      "META",
    "facebook":  "META",
    "nvidia":    "NVDA",
    "netflix":   "NFLX",
    "tesla":     "TSLA",
    "amd":       "AMD",
    "intel":     "INTC",
    "qualcomm":  "QCOM",
    # US financials
    "jpmorgan":  "JPM",
    "jp morgan": "JPM",
    "goldman":   "GS",
    "bank of america": "BAC",
    "wells fargo": "WFC",
    # US autos / EV
    "gm":        "GM",
    "ford":      "F",
    "rivian":    "RIVN",
    "lucid":     "LCID",
    "nio":       "NIO",
    # Indian IT
    "tcs":       "TCS.NS",
    "infosys":   "INFY.NS",
    "wipro":     "WIPRO.NS",
    "hcl":       "HCLTECH.NS",
    "tech mahindra": "TECHM.NS",
    "persistent": "PERSISTENT.NS",
    # Retail / e-commerce
    "walmart":   "WMT",
    "target":    "TGT",
    # Semiconductors
    "broadcom":  "AVGO",
    "tsmc":      "TSM",
}


def extract_ticker(query: str) -> Optional[str]:
    """
    Attempt to extract a stock ticker symbol from a query string.

    Four-pass extraction strategy:
      1. Explicit preposition patterns  — "for AAPL", "analyze MSFT", "about TSLA"
      2. Company name lookup            — "google" → GOOGL, "apple" → AAPL
      3. Exchange-suffix tokens          — TCS.NS, INFY.BO
      4. Standalone uppercase tokens     — 2-5 char word not in non-ticker blocklist

    Pass 4 uses a large non-ticker blocklist that includes common English words
    AND intent/modifier words (QUICK, SHOW, GIVE, DEEP, FULL, etc.) that
    previously caused false positives.

    Args:
        query (str): Raw user query.

    Returns:
        str | None: Extracted ticker symbol or None if not found.
    """
    query_stripped = query.strip()
    query_lower    = query_stripped.lower()

    # --- Pass 1: Explicit preposition patterns (case-insensitive) ---
    # Allows an optional secondary preposition so patterns like:
    #   "summary of Apple" → keyword=summary, optional_prep=of, candidate=Apple
    #   "analysis of MSFT" → keyword=analysis, optional_prep=of, candidate=MSFT
    #   "research on TSLA" → keyword=research, optional_prep=on, candidate=TSLA
    explicit = re.search(
        r"\b(?:for|analyze|about|on|of|check|research|forecast|compare|analysis|summary|report)\s+"
        r"(?:(?:of|for|on|about|the)\s+)?"    # optional secondary preposition
        r"([A-Z]{1,10}(?:\.[A-Z]{1,3})?)\b",
        query_stripped,
        re.IGNORECASE,
    )
    if explicit:
        candidate = explicit.group(1).upper()
        # Normalize through company name map first (handles "google" → "GOOGL", "apple" → "AAPL")
        candidate_mapped = _COMPANY_NAME_MAP.get(candidate.lower())
        if candidate_mapped:
            return candidate_mapped
        # Reject known non-ticker words produced by the optional prep group
        _P1_BLOCKLIST = {
            "OF", "FOR", "ON", "ABOUT", "THE", "AN", "A",
            "QUICK", "DEEP", "FULL", "BRIEF", "SUMMARY", "RESEARCH",
            "ANALYSIS", "REPORT", "FORECAST", "COMPARE", "STRING",
        }
        if len(candidate) <= 6 and candidate not in _P1_BLOCKLIST:
            return candidate

    # --- Pass 2: Company name lookup ---
    # Sort by length descending so "jp morgan" matches before "morgan"
    for name, ticker in sorted(_COMPANY_NAME_MAP.items(), key=lambda x: -len(x[0])):
        if name in query_lower:
            return ticker

    # --- Pass 3: Exchange-suffix tokens (e.g. TCS.NS, INFY.BO) ---
    exchange_match = re.search(r"\b([A-Z]{2,10}\.[A-Z]{2,3})\b", query_stripped, re.IGNORECASE)
    if exchange_match:
        return exchange_match.group(1).upper()

    # --- Pass 4: Standalone uppercase word of 2-5 chars ---
    # Large blocklist: common English words + intent/modifier words
    _NON_TICKERS = {
        # Articles, prepositions, conjunctions
        "FOR", "THE", "AND", "OR", "BUT", "ME", "MY", "IS", "IN",
        "ON", "OF", "TO", "AT", "DO", "US", "IT", "AN", "BE", "BY",
        "NO", "SO", "UP", "AS", "IF", "GO", "HE", "WE", "YET",
        # Intent / modifier words from query vocabulary
        "QUICK", "SHOW", "GIVE", "TELL", "DEEP", "FULL", "BRIEF",
        "KEY", "ALL", "NEW", "GET", "RUN", "HOW", "WHY", "WHAT",
        "WHO", "CAN", "ARE", "WAS", "HAS", "HAD", "ITS", "ANY",
        "NOT", "WITH", "FROM", "OVER", "THEN", "THAN", "ALSO",
        "WILL", "HAVE", "BEEN", "DOES", "JUST", "VERY", "MORE",
        "INTO", "WELL", "SOME", "THAT", "THIS", "WHEN", "LIKE",
        "HIGH", "RISK", "DATA", "BASE", "CASE", "SHOW", "LIST",
        "HELP", "GIVE", "FIND", "MAKE", "LOOK", "TAKE", "COME",
        "KNOW", "NEED", "WANT", "GOOD",
    }

    tokens = query_stripped.split()
    for token in tokens:
        cleaned = re.sub(r"[^A-Z]", "", token.upper())
        if 2 <= len(cleaned) <= 5 and cleaned.isalpha() and cleaned not in _NON_TICKERS:
            return cleaned

    return None


def _make_result(
    intent: str,
    confidence: str,
    keywords: List[str],
    scores: Dict[str, int],
) -> Dict[str, Any]:
    return {
        "intent": intent,
        "confidence": confidence,
        "matched_keywords": keywords,
        "scores": scores,
    }
