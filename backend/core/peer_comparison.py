"""
backend/core/peer_comparison.py

Peer comparison engine for the Financial & Market Research Agent.

Fetches metrics for the target company + its peers and computes quantitative
positioning for each key metric (valuation, profitability, growth, leverage).

Ranking logic:
  For each metric the target is ranked against its peer group. The 'position'
  label is derived from where the target sits relative to the peer average:

  Valuation (PE, P/B) — lower is better:
    > +20% above peer avg  → "premium_valuation"
    < -20% below peer avg  → "undervalued_vs_peers"
    otherwise              → "in_line_with_peers"

  Profitability (net_margin, ROE) — higher is better:
    > +10% above avg       → "above_peers"
    > +5% above avg        → "slightly_above_peers"
    < -10% below avg       → "below_peers"
    < -5% below avg        → "slightly_below_peers"
    otherwise              → "in_line_with_peers"

  Growth (revenue_growth) — higher is better (same thresholds as profitability)

  Leverage (debt_to_equity) — lower is better:
    > +30% above peer avg  → "higher_leverage_than_peers"
    < -30% below peer avg  → "lower_leverage_than_peers"
    otherwise              → "similar_leverage"
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Threshold constants
# ---------------------------------------------------------------------------
VALUATION_PREMIUM_PCT    = 0.20   # 20% above peer avg = premium
VALUATION_DISCOUNT_PCT   = 0.20   # 20% below peer avg = undervalued
PROFIT_OUTPERFORM_PCT    = 0.10   # 10 absolute pp above avg = above peers
PROFIT_SLIGHT_PCT        = 0.05   # 5 absolute pp above avg = slightly above
LEVERAGE_HIGH_PCT        = 0.30   # 30% above peer avg D/E = higher leverage
LEVERAGE_LOW_PCT         = 0.30   # 30% below peer avg D/E = lower leverage


def _peer_avg(
    metrics: Dict[str, Dict[str, Any]],
    tickers: List[str],
    field: str,
) -> Optional[float]:
    """Compute the average value of `field` across `tickers`, ignoring None."""
    values = [
        metrics[t][field]
        for t in tickers
        if t in metrics and metrics[t].get(field) is not None
    ]
    return round(sum(values) / len(values), 4) if values else None


def _rank_lower_is_better(
    target_val: Optional[float],
    peer_avg: Optional[float],
    premium_pct: float,
    discount_pct: float,
) -> str:
    """Rank a metric where lower values are better (e.g. PE, D/E)."""
    if target_val is None or peer_avg is None or peer_avg == 0:
        return "unavailable"
    diff_pct = (target_val - peer_avg) / abs(peer_avg)
    if diff_pct > premium_pct:
        return "premium_valuation"
    if diff_pct < -discount_pct:
        return "undervalued_vs_peers"
    return "in_line_with_peers"


def _rank_higher_is_better(
    target_val: Optional[float],
    peer_avg: Optional[float],
    strong_threshold: float,
    slight_threshold: float,
) -> str:
    """Rank a metric where higher values are better (e.g. net margin, ROE)."""
    if target_val is None or peer_avg is None:
        return "unavailable"
    diff = target_val - peer_avg          # absolute percentage point diff
    if diff > strong_threshold:
        return "above_peers"
    if diff > slight_threshold:
        return "slightly_above_peers"
    if diff < -strong_threshold:
        return "below_peers"
    if diff < -slight_threshold:
        return "slightly_below_peers"
    return "in_line_with_peers"


def _rank_leverage(
    target_val: Optional[float],
    peer_avg: Optional[float],
) -> str:
    """Rank D/E — context-aware: high leverage is a risk signal."""
    if target_val is None or peer_avg is None or peer_avg == 0:
        return "unavailable"
    diff_pct = (target_val - peer_avg) / abs(peer_avg)
    if diff_pct > LEVERAGE_HIGH_PCT:
        return "higher_leverage_than_peers"
    if diff_pct < -LEVERAGE_LOW_PCT:
        return "lower_leverage_than_peers"
    return "similar_leverage_to_peers"


def _metric_block(
    target_val: Optional[float],
    peer_avg: Optional[float],
    position: str,
    field: str,
    all_peer_values: Dict[str, Optional[float]],
) -> Dict[str, Any]:
    """Build the per-metric comparison dict."""
    return {
        "target": target_val,
        "peer_avg": round(peer_avg, 4) if peer_avg is not None else None,
        "position": position,
        "peer_values": {k: v for k, v in all_peer_values.items() if v is not None},
    }


def compare_with_peers(
    target: str,
    peers: List[str],
) -> Dict[str, Any]:
    """
    Run a full quantitative peer comparison for the target ticker.

    Fetches metrics for the target + all peers, then computes per-metric
    positioning relative to the peer group average.

    Args:
        target (str): Validated uppercase target ticker.
        peers (list[str]): List of peer ticker symbols (can be empty).

    Returns:
        dict:
            target (str)
            peer_group (list[str])
            valuation_comparison: pe_ratio, price_to_book
            profitability_comparison: net_margin, roe
            growth_comparison: revenue_growth
            leverage_comparison: debt_to_equity
            summary (list[str]): Human-readable positioning insights
            analysis_notes (list[str]): Warnings (e.g. missing peer data)
    """
    if not peers:
        return {
            "target": target,
            "peer_group": [],
            "valuation_comparison": {},
            "profitability_comparison": {},
            "growth_comparison": {},
            "leverage_comparison": {},
            "summary": ["No peer group defined for this ticker — comparison not available."],
            "analysis_notes": [],
        }

    from backend.core.peer_metrics import fetch_peer_metrics

    all_tickers = [target] + peers
    metrics = fetch_peer_metrics(all_tickers)
    analysis_notes: list[str] = []

    target_m = metrics.get(target, {})
    if not target_m.get("data_available"):
        analysis_notes.append(f"Could not retrieve metrics for target ticker '{target}'")

    # Filter peers that have data
    available_peers = [p for p in peers if metrics.get(p, {}).get("data_available")]
    missing_peers   = [p for p in peers if p not in available_peers]
    if missing_peers:
        analysis_notes.append(f"No data available for peers: {', '.join(missing_peers)}")

    def _peer_vals(field: str) -> Dict[str, Optional[float]]:
        return {p: metrics[p].get(field) for p in available_peers if p in metrics}

    # -----------------------------------------------------------------------
    # Compute peer averages
    # -----------------------------------------------------------------------
    avg_pe       = _peer_avg(metrics, available_peers, "pe_ratio")
    avg_pb       = _peer_avg(metrics, available_peers, "price_to_book")
    avg_margin   = _peer_avg(metrics, available_peers, "net_margin")
    avg_roe      = _peer_avg(metrics, available_peers, "roe")
    avg_growth   = _peer_avg(metrics, available_peers, "revenue_growth")
    avg_de       = _peer_avg(metrics, available_peers, "debt_to_equity")

    # -----------------------------------------------------------------------
    # Rank each metric
    # -----------------------------------------------------------------------
    pe_position  = _rank_lower_is_better(
        target_m.get("pe_ratio"), avg_pe,
        VALUATION_PREMIUM_PCT, VALUATION_DISCOUNT_PCT,
    )
    pb_position  = _rank_lower_is_better(
        target_m.get("price_to_book"), avg_pb,
        VALUATION_PREMIUM_PCT, VALUATION_DISCOUNT_PCT,
    )
    margin_pos   = _rank_higher_is_better(
        target_m.get("net_margin"), avg_margin,
        PROFIT_OUTPERFORM_PCT * 10,   # 1pp threshold scaled to % units
        PROFIT_SLIGHT_PCT * 10,
    )
    roe_pos      = _rank_higher_is_better(
        target_m.get("roe"), avg_roe,
        PROFIT_OUTPERFORM_PCT * 10,
        PROFIT_SLIGHT_PCT * 10,
    )
    growth_pos   = _rank_higher_is_better(
        target_m.get("revenue_growth"), avg_growth,
        PROFIT_OUTPERFORM_PCT * 10,
        PROFIT_SLIGHT_PCT * 10,
    )
    leverage_pos = _rank_leverage(target_m.get("debt_to_equity"), avg_de)

    # -----------------------------------------------------------------------
    # Build comparison sections
    # -----------------------------------------------------------------------
    valuation_comparison = {
        "pe_ratio":      _metric_block(target_m.get("pe_ratio"),      avg_pe,     pe_position,  "pe_ratio",      _peer_vals("pe_ratio")),
        "price_to_book": _metric_block(target_m.get("price_to_book"), avg_pb,     pb_position,  "price_to_book", _peer_vals("price_to_book")),
    }
    profitability_comparison = {
        "net_margin": _metric_block(target_m.get("net_margin"), avg_margin, margin_pos, "net_margin", _peer_vals("net_margin")),
        "roe":        _metric_block(target_m.get("roe"),        avg_roe,    roe_pos,    "roe",        _peer_vals("roe")),
    }
    growth_comparison = {
        "revenue_growth": _metric_block(target_m.get("revenue_growth"), avg_growth, growth_pos, "revenue_growth", _peer_vals("revenue_growth")),
    }
    leverage_comparison = {
        "debt_to_equity": _metric_block(target_m.get("debt_to_equity"), avg_de, leverage_pos, "debt_to_equity", _peer_vals("debt_to_equity")),
    }

    # -----------------------------------------------------------------------
    # Generate summary insights
    # -----------------------------------------------------------------------
    summary = _build_summary(
        target, pe_position, pb_position, margin_pos, roe_pos, growth_pos, leverage_pos,
    )

    logger.info(
        "Peer comparison for %s vs %s: margin=%s | growth=%s | PE=%s",
        target, peers, margin_pos, growth_pos, pe_position,
    )

    return {
        "target": target,
        "target_company_name": target_m.get("company_name", target),
        "peer_group": peers,
        "available_peers": available_peers,
        "valuation_comparison": valuation_comparison,
        "profitability_comparison": profitability_comparison,
        "growth_comparison": growth_comparison,
        "leverage_comparison": leverage_comparison,
        "summary": summary,
        "analysis_notes": analysis_notes,
    }


def _build_summary(
    target: str,
    pe_pos: str,
    pb_pos: str,
    margin_pos: str,
    roe_pos: str,
    growth_pos: str,
    leverage_pos: str,
) -> List[str]:
    """Convert position labels into concise human-readable insights."""
    insights: List[str] = []

    # Valuation
    if pe_pos == "undervalued_vs_peers":
        insights.append("trades at a discount to peers on PE basis — potentially undervalued")
    elif pe_pos == "premium_valuation":
        insights.append("commands a valuation premium over peers — higher growth expectations priced in")

    # Profitability
    if margin_pos in ("above_peers", "slightly_above_peers"):
        insights.append("more profitable than peer group average (net margin)")
    elif margin_pos in ("below_peers", "slightly_below_peers"):
        insights.append("lower profitability vs peer average — margin improvement needed")

    if roe_pos in ("above_peers", "slightly_above_peers"):
        insights.append("superior return on equity vs peers — efficient capital allocation")
    elif roe_pos in ("below_peers", "slightly_below_peers"):
        insights.append("below-average return on equity vs peers")

    # Growth
    if growth_pos in ("above_peers", "slightly_above_peers"):
        insights.append("revenue growth outpacing peer group")
    elif growth_pos in ("below_peers", "slightly_below_peers"):
        insights.append("revenue growth lagging behind peers")

    # Leverage
    if leverage_pos == "higher_leverage_than_peers":
        insights.append("carries more debt than peers — leverage risk relative to sector")
    elif leverage_pos == "lower_leverage_than_peers":
        insights.append("lower leverage than peers — stronger balance sheet relative positioning")

    if not insights:
        insights.append("performance broadly in line with peer group across key metrics")

    return insights
