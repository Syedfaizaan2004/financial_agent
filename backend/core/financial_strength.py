"""
backend/core/financial_strength.py

Financial strength evaluator for the Financial Analysis Engine.

Takes a computed KPIs dictionary and applies rule-based thresholds to
produce a list of identified financial strengths and weaknesses.

Rules are based on widely-used fundamental analysis benchmarks:
  - Current ratio < 1.0         → weak liquidity risk
  - Debt-to-equity > 2.0        → high leverage risk
  - Net profit margin > 15%     → strong profitability
  - ROE > 15%                   → strong return on equity
  - ROA > 5%                    → efficient asset usage
  - Asset turnover > 1.0        → high operational efficiency
  - Free cash flow > 0          → positive cash generation
  - Operating margin > 20%      → strong operational profitability
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Rule thresholds
# ---------------------------------------------------------------------------

THRESHOLDS = {
    "strong_net_margin":         15.0,    # Net profit margin % above which = strong
    "strong_operating_margin":   20.0,    # Operating margin % above which = strong
    "strong_roe":                15.0,    # ROE % above which = strong
    "strong_roa":                 5.0,    # ROA % above which = efficient
    "high_leverage_dte":          2.0,    # Debt-to-equity above which = risky
    "critical_leverage_dte":      4.0,    # Debt-to-equity above which = very risky
    "weak_liquidity_cr":          1.0,    # Current ratio below which = weak
    "adequate_liquidity_cr":      1.5,    # Current ratio above which = adequate
    "strong_asset_turnover":      1.0,    # Asset turnover above which = efficient
    "positive_fcf":               0.0,    # Free cash flow above which = healthy
}


def _check(value: Optional[float], threshold: float, above: bool = True) -> bool:
    """Return True if value satisfies the threshold condition."""
    if value is None:
        return False
    return (value > threshold) if above else (value < threshold)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_financial_strength(kpis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate financial strengths and weaknesses based on KPI thresholds.

    Applies rule-based analysis to produce an actionable summary of what
    the company is doing well and where risks lie.

    Args:
        kpis (dict): Computed KPIs from calculate_kpis().
            Must contain keys: net_profit_margin, operating_margin, roe, roa,
            asset_turnover, current_ratio, debt_to_equity, free_cash_flow.

    Returns:
        dict:
            strengths (list[str]): Identified positive financial attributes
            weaknesses (list[str]): Identified financial risks or concerns
            overall_score (int): Simple 0–10 score (5 = neutral baseline)
            score_rationale (str): Brief explanation of the score
    """
    strengths:  List[str] = []
    weaknesses: List[str] = []
    score = 5  # neutral baseline

    t = THRESHOLDS
    net_margin      = kpis.get("net_profit_margin")
    op_margin       = kpis.get("operating_margin")
    roe             = kpis.get("roe")
    roa             = kpis.get("roa")
    asset_turnover  = kpis.get("asset_turnover")
    current_ratio   = kpis.get("current_ratio")
    debt_to_equity  = kpis.get("debt_to_equity")
    debt_to_assets  = kpis.get("debt_to_assets")
    free_cash_flow  = kpis.get("free_cash_flow")

    # -----------------------------------------------------------------------
    # Profitability checks
    # -----------------------------------------------------------------------
    if _check(net_margin, t["strong_net_margin"]):
        strengths.append(f"strong net profit margin ({net_margin:.1f}%)")
        score += 1
    elif net_margin is not None and net_margin < 0:
        weaknesses.append(f"negative net profit margin ({net_margin:.1f}%)")
        score -= 1

    if _check(op_margin, t["strong_operating_margin"]):
        strengths.append(f"strong operating margin ({op_margin:.1f}%)")
        score += 1
    elif op_margin is not None and op_margin < 5:
        weaknesses.append(f"thin operating margin ({op_margin:.1f}%)")
        score -= 1

    if _check(roe, t["strong_roe"]):
        strengths.append(f"high return on equity ({roe:.1f}%)")
        score += 1
    elif roe is not None and roe < 0:
        weaknesses.append(f"negative return on equity ({roe:.1f}%)")
        score -= 1

    if _check(roa, t["strong_roa"]):
        strengths.append(f"efficient asset use — ROA {roa:.1f}%")
        score += 1
    elif roa is not None and roa < 0:
        weaknesses.append(f"negative return on assets ({roa:.1f}%)")
        score -= 1

    # -----------------------------------------------------------------------
    # Efficiency check
    # -----------------------------------------------------------------------
    if _check(asset_turnover, t["strong_asset_turnover"]):
        strengths.append(f"high asset turnover ({asset_turnover:.2f}x)")
        score += 1
    elif asset_turnover is not None and asset_turnover < 0.3:
        weaknesses.append(f"low asset turnover ({asset_turnover:.2f}x)")
        score -= 1

    # -----------------------------------------------------------------------
    # Liquidity check
    # -----------------------------------------------------------------------
    if _check(current_ratio, t["adequate_liquidity_cr"]):
        strengths.append(f"adequate liquidity — current ratio {current_ratio:.2f}x")
        score += 1
    elif _check(current_ratio, t["weak_liquidity_cr"], above=False):
        weaknesses.append(
            f"weak liquidity — current ratio {current_ratio:.2f}x "
            "(current liabilities exceed current assets)"
        )
        score -= 2

    # -----------------------------------------------------------------------
    # Leverage check
    # -----------------------------------------------------------------------
    if debt_to_equity is not None:
        if debt_to_equity > t["critical_leverage_dte"]:
            weaknesses.append(
                f"very high leverage risk — D/E ratio {debt_to_equity:.2f}x"
            )
            score -= 2
        elif debt_to_equity > t["high_leverage_dte"]:
            weaknesses.append(f"elevated leverage — D/E ratio {debt_to_equity:.2f}x")
            score -= 1
        elif debt_to_equity < 0.5:
            strengths.append(f"low financial leverage — D/E ratio {debt_to_equity:.2f}x")
            score += 1

    # -----------------------------------------------------------------------
    # Cash flow check
    # -----------------------------------------------------------------------
    if _check(free_cash_flow, t["positive_fcf"]):
        strengths.append(
            f"positive free cash flow (${free_cash_flow:,.0f})"
            if free_cash_flow is not None else "positive free cash flow"
        )
        score += 1
    elif free_cash_flow is not None and free_cash_flow < 0:
        weaknesses.append(
            f"negative free cash flow (${free_cash_flow:,.0f})"
        )
        score -= 1

    # -----------------------------------------------------------------------
    # Clamp and summarise score
    # -----------------------------------------------------------------------
    overall_score = max(0, min(10, score))

    if overall_score >= 8:
        score_rationale = "Financially strong across most key metrics."
    elif overall_score >= 6:
        score_rationale = "Generally healthy with minor areas of concern."
    elif overall_score >= 4:
        score_rationale = "Mixed financial profile — monitor key risk areas."
    elif overall_score >= 2:
        score_rationale = "Notable financial weaknesses that warrant caution."
    else:
        score_rationale = "Significant financial risks detected across multiple metrics."

    logger.info(
        "Financial strength score for ticker: %d/10 | strengths=%d | weaknesses=%d",
        overall_score, len(strengths), len(weaknesses),
    )

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "overall_score": overall_score,
        "score_rationale": score_rationale,
    }
