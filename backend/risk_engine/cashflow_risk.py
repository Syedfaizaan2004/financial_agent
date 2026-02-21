"""
backend/risk_engine/cashflow_risk.py

Cash flow risk analyzer for the Risk Intelligence Engine.

Evaluates the quality and sustainability of a company's cash generation
by examining free cash flow, the earnings-to-cash-flow relationship,
and operating cash flow trends.

Key signals:
  - Negative FCF         → paying out more cash than generated
  - Earnings >> Cash flow → aggressive accrual accounting / earnings quality risk
  - Low FCF/Net income   → profit not converting to usable cash
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
FCF_EARNINGS_RATIO_LOW    = 0.5   # FCF < 50% of net income → earnings quality concern
FCF_EARNINGS_RATIO_STRONG = 1.0   # FCF > net income → excellent cash conversion


def assess_cashflow_risk(financials: Dict[str, Any]) -> Dict[str, Any]:
    """
    Assess cash flow risk based on free cash flow and earnings conversion.

    Analyses:
    - Free cash flow sign and magnitude
    - FCF as a proportion of net income (earnings quality)
    - Operating income vs free cash flow mismatch (hidden accruals)

    Args:
        financials (dict): Output of fetch_financial_statements().

    Returns:
        dict:
            risk_level (str): 'low' | 'moderate' | 'high' | 'critical'
            risk_score (int): 0–10 (10 = highest risk)
            details (str): Human-readable explanation
            flags (list[str]): Specific cash flow concerns
            fcf_to_net_income_ratio (float | None): FCF / Net Income
            free_cash_flow (float | None)
    """
    flags: list[str] = []
    risk_points = 0

    free_cash_flow = financials.get("free_cash_flow")
    net_income     = financials.get("net_income")
    op_income      = financials.get("operating_income")

    # --- FCF sign check ---
    if free_cash_flow is not None:
        if free_cash_flow < 0:
            flags.append(
                f"negative free cash flow (${free_cash_flow:,.0f}) — "
                "company is burning more cash than it generates"
            )
            risk_points += 3
        elif free_cash_flow == 0:
            flags.append("zero free cash flow — no cash surplus generated")
            risk_points += 1
        else:
            flags.append(f"positive free cash flow (${free_cash_flow:,.0f}) — healthy cash generation")
    else:
        flags.append("free cash flow data unavailable")
        risk_points += 1

    # --- FCF / Net income ratio (earnings quality) ---
    fcf_to_ni_ratio: Optional[float] = None
    if free_cash_flow is not None and net_income is not None and net_income != 0:
        fcf_to_ni_ratio = round(free_cash_flow / net_income, 4)

        if fcf_to_ni_ratio < 0:
            flags.append(
                f"negative FCF-to-earnings ratio ({fcf_to_ni_ratio:.2f}) — "
                "profits are not translating to real cash"
            )
            risk_points += 3
        elif fcf_to_ni_ratio < FCF_EARNINGS_RATIO_LOW:
            flags.append(
                f"low FCF-to-earnings ratio ({fcf_to_ni_ratio:.2f}) — "
                "only {:.0f}% of reported earnings converted to free cash flow".format(
                    fcf_to_ni_ratio * 100
                )
            )
            risk_points += 2
        elif fcf_to_ni_ratio >= FCF_EARNINGS_RATIO_STRONG:
            flags.append(
                f"strong cash conversion — FCF exceeds net income (ratio: {fcf_to_ni_ratio:.2f})"
            )
    elif net_income is not None and net_income <= 0:
        flags.append("net income is non-positive — earnings quality ratio not meaningful")
        if free_cash_flow is None or free_cash_flow <= 0:
            risk_points += 2

    # --- Operating income vs FCF mismatch ---
    if op_income is not None and free_cash_flow is not None:
        if op_income > 0 and free_cash_flow < 0:
            flags.append(
                "operating income is positive but FCF is negative — "
                "possible large capex burden or working capital drain"
            )
            risk_points += 2
        elif op_income > 0 and free_cash_flow < op_income * 0.3:
            flags.append(
                f"FCF (${free_cash_flow:,.0f}) is significantly below operating income "
                f"(${op_income:,.0f}) — high capex or accruals consuming earnings"
            )
            risk_points += 1

    # --- Classify ---
    risk_level, risk_score = _classify(risk_points, max_points=9)

    details = (
        f"FCF: ${free_cash_flow:,.0f}. " if free_cash_flow is not None else "FCF unavailable. "
    )
    if fcf_to_ni_ratio is not None:
        details += f"FCF/Net Income: {fcf_to_ni_ratio:.2f}. "
    details += f"Cash flow risk: {risk_level}."

    logger.info("Cash flow risk: %s | score=%d/10", risk_level, risk_score)

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "details": details,
        "flags": flags,
        "fcf_to_net_income_ratio": fcf_to_ni_ratio,
        "free_cash_flow": free_cash_flow,
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
