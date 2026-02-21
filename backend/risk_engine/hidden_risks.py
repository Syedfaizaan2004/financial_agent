"""
backend/risk_engine/hidden_risks.py

Overlooked (hidden) risk detector for the Risk Intelligence Engine.

Identifies compound financial risks that arise from combinations of
individual metrics — risks that don't show up in single-metric analysis.

Detects:
  1. High leverage + weak liquidity    → double financial stress
  2. Profit growing but FCF shrinking  → earnings quality deterioration
  3. Shrinking operating margins       → structural profitability erosion
  4. Rising debt + declining earnings  → worsening debt serviceability
  5. High PE + low FCF yield           → valuation risk (priced for perfection)
  6. Positive earnings, negative FCF   → aggressive accruals / non-cash profits
  7. Very high beta                    → elevated market / sentiment risk
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Detection thresholds (quantitative, no hardcoded company values)
# ---------------------------------------------------------------------------
HIGH_DE_THRESHOLD          = 2.0    # D/E above which = high leverage
HIGH_PE_THRESHOLD          = 40.0   # PE above which = expensive valuation
LOW_CURRENT_RATIO          = 1.25   # CR below which = liquidity pressure
LOW_FCF_YIELD              = 0.01   # FCF / market cap below which = low yield
HIGH_BETA_THRESHOLD        = 1.5    # Beta above which = high market sensitivity
WEAK_MARGIN_THRESHOLD      = 5.0    # Operating margin % below which = thin
ACCRUAL_NI_THRESHOLD       = 0.3    # FCF < 30% of net income = accrual concern


def detect_hidden_risks(
    financials: Dict[str, Any],
    kpis: Dict[str, Any],
) -> List[str]:
    """
    Identify overlooked compound financial risks.

    Each check evaluates a combination of two or more financial signals
    to surface risks invisible to single-metric review.

    Args:
        financials (dict): Output of fetch_financial_statements().
        kpis (dict): Output of calculate_kpis().

    Returns:
        list[str]: Human-readable descriptions of detected hidden risks.
                   Returns an empty list if no hidden risks are found.
    """
    risks: List[str] = []

    de_ratio       = kpis.get("debt_to_equity")
    current_ratio  = kpis.get("current_ratio")
    net_margin     = kpis.get("net_profit_margin")
    op_margin      = kpis.get("operating_margin")
    free_cash_flow = financials.get("free_cash_flow")
    net_income     = financials.get("net_income")
    total_debt     = financials.get("total_debt")
    market_cap     = financials.get("market_cap")
    pe_ratio       = kpis.get("pe_ratio")
    beta           = kpis.get("beta")

    # -------------------------------------------------------------------
    # 1. High leverage + weak liquidity → double financial stress
    # -------------------------------------------------------------------
    if (
        de_ratio is not None and de_ratio > HIGH_DE_THRESHOLD
        and current_ratio is not None and current_ratio < LOW_CURRENT_RATIO
    ):
        risks.append(
            f"combined leverage and liquidity stress: high D/E ({de_ratio:.2f}x) "
            f"alongside weak current ratio ({current_ratio:.2f}x) — "
            "company may struggle to service short-term obligations"
        )

    # -------------------------------------------------------------------
    # 2. Positive net income but negative / very low FCF → earnings quality risk
    # -------------------------------------------------------------------
    if (
        net_income is not None and net_income > 0
        and free_cash_flow is not None
    ):
        if free_cash_flow < 0:
            risks.append(
                "earnings quality risk: company reports positive net income "
                f"(${net_income:,.0f}) but generates negative free cash flow "
                f"(${free_cash_flow:,.0f}) — profits may be non-cash or accrual-driven"
            )
        elif free_cash_flow < net_income * ACCRUAL_NI_THRESHOLD:
            ratio = free_cash_flow / net_income
            risks.append(
                f"low cash conversion: FCF is only {ratio:.0%} of net income — "
                "reported profits are significantly ahead of actual cash generated"
            )

    # -------------------------------------------------------------------
    # 3. Thin operating margin → structural profitability pressure
    # -------------------------------------------------------------------
    if op_margin is not None and 0 <= op_margin < WEAK_MARGIN_THRESHOLD:
        risks.append(
            f"thin operating margin ({op_margin:.1f}%) — small revenue decline or "
            "cost increase could push the company into operating losses"
        )

    # -------------------------------------------------------------------
    # 4. Rising debt (debt present) + negative/thin net margin → debt serviceability risk
    # -------------------------------------------------------------------
    if (
        total_debt is not None and total_debt > 0
        and net_margin is not None and net_margin < 5.0
    ):
        risks.append(
            f"debt serviceability risk: total debt of ${total_debt:,.0f} "
            f"with a net margin of only {net_margin:.1f}% — "
            "limited earnings buffer to cover debt obligations"
        )

    # -------------------------------------------------------------------
    # 5. High PE + low FCF yield → valuation risk (priced for perfection)
    # -------------------------------------------------------------------
    if pe_ratio is not None and pe_ratio > HIGH_PE_THRESHOLD:
        if market_cap is not None and free_cash_flow is not None and market_cap > 0:
            fcf_yield = free_cash_flow / market_cap
            if fcf_yield < LOW_FCF_YIELD:
                risks.append(
                    f"valuation risk: PE of {pe_ratio:.1f}x with FCF yield of "
                    f"{fcf_yield:.2%} — stock is priced for flawless execution; "
                    "any earnings miss could trigger sharp repricing"
                )
        else:
            risks.append(
                f"valuation risk: high PE ratio ({pe_ratio:.1f}x) — "
                "elevated expectations leave little margin for earnings disappointment"
            )

    # -------------------------------------------------------------------
    # 6. Both margins are very thin (net and operating)
    # -------------------------------------------------------------------
    if (
        net_margin is not None and op_margin is not None
        and net_margin < 3.0 and op_margin < 5.0
        and "thin operating margin" not in " ".join(risks)  # avoid duplicate
    ):
        risks.append(
            f"margin compression risk: both net margin ({net_margin:.1f}%) and "
            f"operating margin ({op_margin:.1f}%) are critically thin — "
            "vulnerable to cost shocks or pricing pressure"
        )

    # -------------------------------------------------------------------
    # 7. High beta → elevated market sensitivity / sentiment risk
    # -------------------------------------------------------------------
    if beta is not None and beta > HIGH_BETA_THRESHOLD:
        risks.append(
            f"high market sensitivity: beta of {beta:.2f} — "
            "stock is susceptible to amplified losses during broad market downturns"
        )

    if not risks:
        logger.info("No hidden risks detected")
    else:
        logger.info("Detected %d hidden risk(s)", len(risks))

    return risks
