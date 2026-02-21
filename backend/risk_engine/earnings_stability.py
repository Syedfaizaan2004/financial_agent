"""
backend/risk_engine/earnings_stability.py

Earnings stability analyzer for the Risk Intelligence Engine.

Fetches up to 4 years of annual net income data and evaluates:
  - Earnings volatility (coefficient of variation)
  - Trend direction (is earnings growing or declining?)
  - Consistency (how many positive-growth years vs total?)

Stability score: 0.0 (highly volatile) → 1.0 (very stable)

Classifications:
  score >= 0.75 → stable
  score >= 0.50 → moderately_stable
  score >= 0.25 → moderately_volatile
  score <  0.25 → highly_volatile
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def assess_earnings_stability(ticker: str) -> Dict[str, Any]:
    """
    Evaluate historical earnings stability for the given ticker.

    Fetches up to 4 years of annual net income from yfinance and computes
    a composite stability score based on volatility and trend consistency.

    Args:
        ticker (str): Validated uppercase stock symbol (e.g. 'AAPL').

    Returns:
        dict:
            stability_score (float | None): 0.0–1.0 (1.0 = perfectly stable)
            classification (str): 'stable' | 'moderately_stable' | 'moderately_volatile' | 'highly_volatile'
            earnings_series (list[float | None]): Annual net incomes, most-recent first
            yoy_changes (list[float]): YoY % change in net income
            positive_growth_years (int): Years with positive earnings growth
            total_years_analyzed (int)
            volatility_cv (float | None): Coefficient of variation (std/mean)
            trend (str): 'improving' | 'declining' | 'mixed' | 'insufficient_data'
            flags (list[str]): Specific stability concerns
            risk_level (str): 'low' | 'moderate' | 'high'

    Raises:
        RuntimeError: If yfinance is not installed.
    """
    try:
        import yfinance as yf
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError(
            "yfinance is required for earnings stability analysis. "
            "Install it with: pip install yfinance"
        ) from exc

    logger.info("Assessing earnings stability for: %s", ticker)

    flags: list[str] = []

    # Fetch annual income statement
    try:
        stock = yf.Ticker(ticker)
        income_stmt = stock.financials
    except Exception as exc:
        logger.warning("Could not fetch income statement for %s: %s", ticker, exc)
        income_stmt = None

    # Extract net income series (most-recent first)
    earnings_series: List[Optional[float]] = []
    if income_stmt is not None and not income_stmt.empty:
        for idx in income_stmt.index:
            if "net income" in str(idx).lower():
                row = income_stmt.loc[idx]
                for val in row.iloc[:4]:
                    try:
                        v = float(val)
                        earnings_series.append(None if pd.isna(v) else v)
                    except (TypeError, ValueError):
                        earnings_series.append(None)
                break

    # Filter valid (non-None) values
    valid_earnings = [e for e in earnings_series if e is not None]
    total_years = len(valid_earnings)

    if total_years < 2:
        return {
            "stability_score": None,
            "classification": "insufficient_data",
            "earnings_series": earnings_series,
            "yoy_changes": [],
            "positive_growth_years": 0,
            "total_years_analyzed": total_years,
            "volatility_cv": None,
            "trend": "insufficient_data",
            "flags": ["Fewer than 2 years of earnings data available"],
            "risk_level": "moderate",
        }

    # --- YoY changes ---
    yoy_changes: List[float] = []
    for i in range(len(valid_earnings) - 1):
        curr, prev = valid_earnings[i], valid_earnings[i + 1]
        if prev and prev != 0:
            yoy_changes.append(round((curr - prev) / abs(prev) * 100, 2))

    positive_growth_years = sum(1 for g in yoy_changes if g > 0)

    # --- Coefficient of Variation (volatility measure) ---
    mean_earnings = sum(valid_earnings) / total_years
    variance = sum((e - mean_earnings) ** 2 for e in valid_earnings) / total_years
    std_earnings = math.sqrt(variance)
    volatility_cv: Optional[float] = None
    if mean_earnings != 0:
        volatility_cv = round(abs(std_earnings / mean_earnings), 4)

    # --- Trend direction ---
    if len(yoy_changes) >= 2:
        # Compare first half trend vs recent (most-recent is index 0)
        recent_changes  = yoy_changes[:len(yoy_changes) // 2 + 1]
        improving_count = sum(1 for g in recent_changes if g > 0)
        if improving_count == len(recent_changes):
            trend = "improving"
        elif improving_count == 0:
            trend = "declining"
        else:
            trend = "mixed"
    elif len(yoy_changes) == 1:
        trend = "improving" if yoy_changes[0] > 0 else "declining"
    else:
        trend = "insufficient_data"

    # --- Flags ---
    if volatility_cv is not None:
        if volatility_cv > 0.5:
            flags.append(f"high earnings volatility (CV={volatility_cv:.2f})")
        elif volatility_cv > 0.25:
            flags.append(f"moderate earnings volatility (CV={volatility_cv:.2f})")

    if trend == "declining":
        flags.append("earnings have been declining")
    if mean_earnings < 0:
        flags.append("average earnings are negative — ongoing losses")

    consecutive_negative = sum(1 for e in valid_earnings if e < 0)
    if consecutive_negative >= 2:
        flags.append(f"{consecutive_negative} of {total_years} years showed negative earnings")

    # --- Stability score (0–1) ---
    score = 1.0
    # Penalise for high CV
    if volatility_cv is not None:
        cv_penalty = min(volatility_cv * 0.4, 0.4)   # max 40% penalty
        score -= cv_penalty
    # Penalise for declining trend
    if trend == "declining":
        score -= 0.2
    elif trend == "mixed":
        score -= 0.1
    # Penalise for low proportion of positive growth years
    if yoy_changes:
        growth_ratio = positive_growth_years / len(yoy_changes)
        score -= (1 - growth_ratio) * 0.2
    # Penalise for negative average earnings
    if mean_earnings < 0:
        score -= 0.2

    stability_score = round(max(0.0, min(1.0, score)), 4)

    # --- Classification ---
    if stability_score >= 0.75:
        classification = "stable"
        risk_level = "low"
    elif stability_score >= 0.50:
        classification = "moderately_stable"
        risk_level = "moderate"
    elif stability_score >= 0.25:
        classification = "moderately_volatile"
        risk_level = "moderate"
    else:
        classification = "highly_volatile"
        risk_level = "high"

    logger.info(
        "Earnings stability for %s: score=%.2f | %s | trend=%s",
        ticker, stability_score, classification, trend,
    )

    return {
        "stability_score": stability_score,
        "classification": classification,
        "earnings_series": valid_earnings,
        "yoy_changes": yoy_changes,
        "positive_growth_years": positive_growth_years,
        "total_years_analyzed": total_years,
        "volatility_cv": volatility_cv,
        "trend": trend,
        "flags": flags,
        "risk_level": risk_level,
    }
