"""
backend/risk_engine/leverage_risk.py

Leverage risk analyzer for the Risk Intelligence Engine.

Evaluates balance-sheet debt levels and equity relationship to classify
the company's financial leverage risk using quantitative thresholds.

Thresholds (industry-standard benchmarks):
  D/E < 0.5  → low leverage
  D/E 0.5–2  → moderate leverage
  D/E 2–4    → high leverage
  D/E > 4    → critical leverage
  Debt > equity → debt dominates capital structure
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
LOW_DE        = 0.5
MODERATE_DE   = 2.0
HIGH_DE       = 4.0
LOW_DA        = 0.3
MODERATE_DA   = 0.6


def assess_leverage_risk(
    financials: Dict[str, Any],
    kpis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Assess financial leverage risk from balance sheet data.

    Analyses:
    - Debt-to-equity (D/E) ratio — primary leverage indicator
    - Debt-to-assets (D/A) ratio — asset coverage of debt
    - Whether total debt exceeds shareholder equity (capital structure)
    - Interest coverage proxy (operating income / debt)

    Args:
        financials (dict): Output of fetch_financial_statements().
        kpis (dict): Output of calculate_kpis().

    Returns:
        dict:
            risk_level (str): 'low' | 'moderate' | 'high' | 'critical'
            risk_score (int): Numeric 0–10 (10 = highest risk)
            details (str): Human-readable explanation
            flags (list[str]): Specific leverage concerns detected
            debt_to_equity (float | None)
            debt_to_assets (float | None)
    """
    flags: list[str] = []
    risk_points = 0  # Accumulate to derive risk_level

    de_ratio  = kpis.get("debt_to_equity")
    da_ratio  = kpis.get("debt_to_assets")
    total_debt = financials.get("total_debt")
    equity     = financials.get("shareholder_equity")
    op_income  = financials.get("operating_income")

    # --- D/E ratio analysis ---
    if de_ratio is not None:
        if de_ratio > HIGH_DE:
            flags.append(f"critical D/E ratio of {de_ratio:.2f}x — extremely high leverage")
            risk_points += 4
        elif de_ratio > MODERATE_DE:
            flags.append(f"high D/E ratio of {de_ratio:.2f}x — elevated leverage risk")
            risk_points += 2
        elif de_ratio > LOW_DE:
            flags.append(f"moderate D/E ratio of {de_ratio:.2f}x")
            risk_points += 1
        else:
            flags.append(f"low D/E ratio of {de_ratio:.2f}x — well-managed leverage")
    else:
        flags.append("D/E ratio unavailable — leverage cannot be fully assessed")
        risk_points += 1  # Unknown is a mild risk

    # --- D/A ratio analysis ---
    if da_ratio is not None:
        if da_ratio > MODERATE_DA:
            flags.append(f"high debt-to-assets of {da_ratio:.2f} — >60% of assets financed by debt")
            risk_points += 2
        elif da_ratio > LOW_DA:
            flags.append(f"moderate debt-to-assets of {da_ratio:.2f}")
            risk_points += 1

    # --- Debt vs equity absolute comparison ---
    if total_debt is not None and equity is not None:
        if equity <= 0:
            flags.append("negative or zero shareholder equity — debt entirely dominates capital")
            risk_points += 3
        elif total_debt > equity:
            flags.append(
                f"total debt (${total_debt:,.0f}) exceeds shareholder equity (${equity:,.0f})"
            )
            risk_points += 2

    # --- Interest coverage proxy: operating income / total debt ---
    if op_income is not None and total_debt is not None and total_debt > 0:
        ic_proxy = op_income / total_debt
        if ic_proxy < 0.05:
            flags.append(
                f"very low interest coverage proxy ({ic_proxy:.2f}) — operating income "
                "barely covers debt service"
            )
            risk_points += 2
        elif ic_proxy < 0.15:
            flags.append(f"low interest coverage proxy ({ic_proxy:.2f})")
            risk_points += 1

    # --- Classify risk level ---
    risk_level, risk_score = _classify(risk_points, max_points=11)

    details = (
        f"Leverage assessment: D/E={de_ratio:.2f}x, D/A={da_ratio:.2f}. "
        if (de_ratio is not None and da_ratio is not None)
        else "Partial leverage data available. "
    )
    details += f"Risk level: {risk_level}. " + " | ".join(flags[:2])

    logger.info("Leverage risk for ticker: %s | score=%d/10", risk_level, risk_score)

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "details": details,
        "flags": flags,
        "debt_to_equity": de_ratio,
        "debt_to_assets": da_ratio,
    }


def _classify(points: int, max_points: int) -> tuple[str, int]:
    """Map accumulated risk points to a (risk_level, 0–10 score) pair."""
    ratio = points / max_points
    score = round(ratio * 10)
    if ratio >= 0.7:
        return "critical", min(score, 10)
    if ratio >= 0.45:
        return "high", min(score, 10)
    if ratio >= 0.2:
        return "moderate", min(score, 10)
    return "low", min(score, 10)
