"""
backend/risk_engine/liquidity_risk.py

Liquidity risk analyzer for the Risk Intelligence Engine.

Evaluates a company's short-term ability to meet its financial obligations
using the current ratio and operating cash flow sign.

Thresholds:
  Current ratio < 1.0  → high liquidity risk (current liabilities > assets)
  Current ratio 1.0–1.5 → moderate liquidity risk
  Current ratio > 1.5  → adequate liquidity
  Negative operating cash flow → cash burn risk
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
CRITICAL_CR  = 0.75   # Critical liquidity threshold
LOW_CR       = 1.0    # Weak liquidity threshold
MODERATE_CR  = 1.5    # Adequate liquidity threshold
STRONG_CR    = 2.0    # Strong liquidity threshold


def assess_liquidity_risk(
    financials: Dict[str, Any],
    kpis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Assess short-term liquidity risk from balance sheet and cash flow data.

    Analyses:
    - Current ratio (current assets / current liabilities)
    - Free cash flow sign (positive = cash-generative)
    - Working capital (current assets - current liabilities)

    Args:
        financials (dict): Output of fetch_financial_statements().
        kpis (dict): Output of calculate_kpis().

    Returns:
        dict:
            risk_level (str): 'low' | 'moderate' | 'high' | 'critical'
            risk_score (int): 0–10 (10 = highest risk)
            details (str): Human-readable explanation
            flags (list[str]): Specific liquidity concerns detected
            current_ratio (float | None)
            working_capital (float | None)
    """
    flags: list[str] = []
    risk_points = 0

    current_ratio       = kpis.get("current_ratio")
    current_assets      = financials.get("current_assets")
    current_liabilities = financials.get("current_liabilities")
    free_cash_flow      = financials.get("free_cash_flow")

    # --- Working capital ---
    working_capital: Optional[float] = None
    if current_assets is not None and current_liabilities is not None:
        working_capital = current_assets - current_liabilities

    # --- Current ratio analysis ---
    if current_ratio is not None:
        if current_ratio < CRITICAL_CR:
            flags.append(
                f"critical current ratio of {current_ratio:.2f}x — "
                "current assets cover less than 75% of current liabilities"
            )
            risk_points += 4
        elif current_ratio < LOW_CR:
            flags.append(
                f"weak current ratio of {current_ratio:.2f}x — "
                "current liabilities exceed current assets"
            )
            risk_points += 3
        elif current_ratio < MODERATE_CR:
            flags.append(
                f"below-average current ratio of {current_ratio:.2f}x — "
                "liquidity is adequate but thin"
            )
            risk_points += 1
        else:
            flags.append(f"healthy current ratio of {current_ratio:.2f}x")
    else:
        flags.append("current ratio unavailable — liquidity assessment is limited")
        risk_points += 1

    # --- Working capital check ---
    if working_capital is not None:
        if working_capital < 0:
            flags.append(
                f"negative working capital (${working_capital:,.0f}) — "
                "operating cycle cannot be self-funded from current assets"
            )
            risk_points += 2

    # --- Free cash flow check ---
    if free_cash_flow is not None:
        if free_cash_flow < 0:
            flags.append(
                f"negative free cash flow (${free_cash_flow:,.0f}) — "
                "company is consuming more cash than it generates"
            )
            risk_points += 2
        else:
            flags.append(f"positive free cash flow (${free_cash_flow:,.0f}) — supports liquidity")
    else:
        flags.append("free cash flow data unavailable")

    # --- Classify ---
    risk_level, risk_score = _classify(risk_points, max_points=9)

    details = (
        f"Current ratio: {current_ratio:.2f}x. " if current_ratio is not None else ""
    )
    details += (
        f"Working capital: ${working_capital:,.0f}. "
        if working_capital is not None else ""
    )
    details += f"Liquidity risk: {risk_level}."

    logger.info("Liquidity risk: %s | score=%d/10", risk_level, risk_score)

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "details": details,
        "flags": flags,
        "current_ratio": current_ratio,
        "working_capital": working_capital,
    }


def _classify(points: int, max_points: int) -> tuple[str, int]:
    """Map accumulated risk points to (risk_level, 0–10 score)."""
    ratio = points / max_points
    score = round(ratio * 10)
    if ratio >= 0.7:
        return "critical", min(score, 10)
    if ratio >= 0.45:
        return "high", min(score, 10)
    if ratio >= 0.2:
        return "moderate", min(score, 10)
    return "low", min(score, 10)
