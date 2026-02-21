"""
backend/agent/memo_generator.py

Investment Memo Generator for the AI Research Agent.

Generates professional investment memos from structured analysis data.
Supports multiple LLM providers (Groq, Gemini, OpenAI-compatible local)
with automatic fallback to a rule-based generator when LLM is disabled
or when the API call fails.

Provider selection is driven by the application settings:
    settings.LLM_PROVIDER  — 'groq' | 'gemini' | 'local' | 'disabled'
    settings.LLM_API_KEY   — API key (required for cloud providers)
    settings.LLM_MODEL     — Model name (provider-specific)

Design principles:
    - LLM output is grounded: prompt contains only actual metric data
    - LLM path is always wrapped in try/except → falls back on any error
    - Fallback produces identical schema as LLM path (no schema differences)
    - Bull/bear cases are extracted from synthesized insights, not invented
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_TEMPLATE_PATH = pathlib.Path(__file__).parent / "prompts" / "memo_template.txt"

# Supported provider keys
_GROQ_PROVIDER   = "groq"
_GEMINI_PROVIDER = "gemini"
_LOCAL_PROVIDER  = "local"
_DISABLED        = "disabled"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_investment_memo(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a structured investment memo from workflow output data.

    Tries LLM generation first; falls back to rule-based on any failure.
    Both paths produce identical output schemas.

    Args:
        data (dict): Full workflow output containing keys:
            ticker, insights, fundamentals, risk, forecast,
            peer_comparison, scenario.

    Returns:
        dict: Investment memo with keys:
            ticker, executive_summary, bull_case, bear_case,
            key_strengths, key_risks, outlook, confidence, analyst_note,
            generated_by ('llm:<provider>' or 'rule_based_fallback').
    """
    ticker = data.get("ticker", "UNKNOWN")
    logger.info("[memo_generator] Generating memo for %s", ticker)

    provider = _get_provider()
    logger.info("[memo_generator] LLM provider: %s", provider)

    # --- Attempt LLM generation ---
    if provider != _DISABLED:
        try:
            memo = _generate_llm_memo(data, provider)
            memo["generated_by"] = f"llm:{provider}"
            logger.info("[memo_generator] LLM memo generated for %s via %s", ticker, provider)
            return memo
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "[memo_generator] LLM generation failed for %s (%s): %s — using fallback",
                ticker, provider, exc,
            )

    # --- Rule-based fallback ---
    from backend.agent.memo_fallback import generate_fallback_memo
    return generate_fallback_memo(data)


def generate_bull_bear_cases(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract bull and bear cases from structured workflow output.

    Standalone function for cases where only bull/bear separation is needed
    (e.g. updating an existing memo). Uses the same deterministic logic
    as the fallback generator.

    Args:
        data (dict): Workflow output (same schema as generate_investment_memo).

    Returns:
        dict:
            bull_case (list[str]): Bullish arguments (max 4)
            bear_case (list[str]): Bearish risks (max 4)
    """
    from backend.agent.memo_fallback import (
        _build_bull_case,
        _build_bear_case,
        _dedup,
    )

    insights = data.get("insights") or {}
    peer     = data.get("peer_comparison") or {}
    scenario = data.get("scenario") or {}
    risk     = data.get("risk") or {}
    fund     = data.get("fundamentals") or {}

    bull = _build_bull_case(
        strengths=insights.get("strengths", []),
        opportunities=insights.get("opportunities", []),
        forecast_trend=insights.get("forecast_trend", "unavailable"),
        peer_summary=peer.get("summary", []),
        fundamentals=fund,
    )
    bear = _build_bear_case(
        risks=insights.get("risks", []),
        scenario=scenario,
        risk_data=risk,
        forecast_trend=insights.get("forecast_trend", "unavailable"),
    )
    return {
        "bull_case": bull[:4],
        "bear_case": bear[:4],
    }


# ---------------------------------------------------------------------------
# LLM routing
# ---------------------------------------------------------------------------

def _get_provider() -> str:
    """Read provider from settings; default to 'disabled' if not configured."""
    try:
        from backend.app.config import get_settings
        settings = get_settings()
        return (getattr(settings, "LLM_PROVIDER", "") or _DISABLED).lower().strip()
    except Exception:  # pylint: disable=broad-except
        return _DISABLED


def _get_api_key(provider: str) -> Optional[str]:
    try:
        from backend.app.config import get_settings
        settings = get_settings()
        if provider == _GROQ_PROVIDER:
            return getattr(settings, "GROQ_API_KEY", None) or getattr(settings, "LLM_API_KEY", None)
        elif provider == _GEMINI_PROVIDER:
            return getattr(settings, "GEMINI_API_KEY", None) or getattr(settings, "LLM_API_KEY", None)
        return getattr(settings, "LLM_API_KEY", None)
    except Exception:  # pylint: disable=broad-except
        return None


def _get_model(provider: str) -> str:
    try:
        from backend.app.config import get_settings
        return getattr(get_settings(), "LLM_MODEL", None) or _default_model(provider)
    except Exception:  # pylint: disable=broad-except
        return _default_model(provider)


def _default_model(provider: str) -> str:
    defaults = {
        _GROQ_PROVIDER:   "llama-3.3-70b-versatile",
        _GEMINI_PROVIDER: "gemini-1.5-flash",
        _LOCAL_PROVIDER:  "mistral",
    }
    return defaults.get(provider, "gpt-3.5-turbo")


def _generate_llm_memo(data: Dict[str, Any], provider: str) -> Dict[str, Any]:
    """Route to the correct LLM backend and parse the JSON response."""
    prompt   = _build_prompt(data)
    response = _call_llm(provider, prompt)
    return _parse_llm_response(response, data)


def _build_prompt(data: Dict[str, Any]) -> str:
    """Render the memo template with structured data."""
    template = _TEMPLATE_PATH.read_text(encoding="utf-8")
    # Serialise only the safe portions (no raw financials to keep token count low)
    summary = {
        "ticker":       data.get("ticker"),
        "insights":     data.get("insights") or {},
        "risk_outlook": (data.get("scenario") or {}).get("risk_outlook", ""),
        "peer_summary": (data.get("peer_comparison") or {}).get("summary", []),
        "scenario":     (data.get("scenario") or {}).get("scenario", ""),
        "key_metrics":  (data.get("insights") or {}).get("key_metrics", {}),
    }
    return template.format(structured_data=json.dumps(summary, indent=2))


def _call_llm(provider: str, prompt: str) -> str:
    """Dispatch to the appropriate LLM client."""
    if provider == _GROQ_PROVIDER:
        return _call_groq(prompt)
    if provider == _GEMINI_PROVIDER:
        return _call_gemini(prompt)
    if provider == _LOCAL_PROVIDER:
        return _call_local(prompt)
    raise ValueError(f"Unsupported LLM provider: '{provider}'")


def _call_groq(prompt: str) -> str:
    """Call Groq API (OpenAI-compatible endpoint)."""
    import httpx  # type: ignore[import-untyped]
    api_key = _get_api_key(_GROQ_PROVIDER)
    if not api_key:
        raise RuntimeError("GROQ API key not set (GROQ_API_KEY)")

    model = _get_model(_GROQ_PROVIDER)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,
        "max_tokens": 800,
        # NOTE: json_object mode requires 'JSON' in the message; simpler to parse manually.
    }
    r = httpx.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _call_gemini(prompt: str) -> str:
    """Call Google Gemini API."""
    import httpx  # type: ignore[import-untyped]
    api_key = _get_api_key(_GEMINI_PROVIDER)
    if not api_key:
        raise RuntimeError("Gemini API key not set (GEMINI_API_KEY)")

    model   = _get_model(_GEMINI_PROVIDER)
    url     = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 800,
        },
    }
    r = httpx.post(url, json=payload, timeout=25)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _call_local(prompt: str) -> str:
    """Call a local Ollama-compatible endpoint."""
    import httpx  # type: ignore[import-untyped]
    model = _get_model(_LOCAL_PROVIDER)
    payload = {
        "model":  model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }
    r = httpx.post("http://localhost:11434/api/generate", json=payload, timeout=60)
    r.raise_for_status()
    return r.json().get("response", "{}")


def _parse_llm_response(raw: str, original_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse JSON from LLM response text.

    Strips markdown fences if present, then parses JSON.
    Falls back to the rule-based generator on any parse error.
    """
    cleaned = raw.strip()
    # Strip ```json ... ``` if model added them despite prompt instructions
    if cleaned.startswith("```"):
        lines   = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.warning("[memo_generator] JSON parse failed: %s — falling back", exc)
        from backend.agent.memo_fallback import generate_fallback_memo
        return generate_fallback_memo(original_data)

    # Merge with fallback to fill any missing keys
    from backend.agent.memo_fallback import generate_fallback_memo
    fallback = generate_fallback_memo(original_data)

    merged = {**fallback, **parsed}
    # Ensure ticker is always correct (LLM might hallucinate it)
    merged["ticker"] = original_data.get("ticker", fallback.get("ticker", "UNKNOWN"))

    # Validate outlook
    _VALID = {"positive", "moderately_positive", "neutral", "cautious", "negative"}
    if merged.get("outlook") not in _VALID:
        merged["outlook"] = fallback.get("outlook", "neutral")

    return merged
