"""
backend/core/peer_fetcher.py

Peer group lookup utility for the Peer Comparison Engine.

Provides a curated, extensible peer map.  The map covers the 14 tickers in
the model universe plus common additions. Return an empty list for unknown
tickers — callers must handle this gracefully.

Extension note:
    Add entries to PEER_MAP to expand coverage. Keys are uppercase tickers;
    values are lists of direct competitor / sector peers. Keep peer lists to
    3–6 tickers for meaningful comparison.
"""

from __future__ import annotations

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Peer map (curated, extensible)
# ---------------------------------------------------------------------------
PEER_MAP: Dict[str, List[str]] = {
    # US Tech — mega-cap
    "AAPL":  ["MSFT", "GOOGL", "META", "AMZN", "NVDA"],
    "MSFT":  ["AAPL", "GOOGL", "AMZN", "META", "NVDA"],
    "GOOGL": ["META", "MSFT", "AMZN", "SNAP", "PINS"],
    "META":  ["GOOGL", "SNAP", "PINS", "TWTR", "MSFT"],
    "AMZN":  ["MSFT", "GOOGL", "AAPL", "WMT", "TGT"],
    "NVDA":  ["AMD", "INTC", "QCOM", "TSM", "AVGO"],
    "AMD":   ["NVDA", "INTC", "QCOM", "ARM", "MU"],
    # US EV / Auto
    "TSLA":  ["GM", "F", "RIVN", "NIO", "LCID"],
    # Indian IT — NSE-listed
    "TCS.NS":        ["INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS", "LTIM.NS"],
    "INFY.NS":       ["TCS.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS", "PERSISTENT.NS"],
    "WIPRO.NS":      ["TCS.NS", "INFY.NS", "HCLTECH.NS", "TECHM.NS", "LTIM.NS"],
    "HCLTECH.NS":    ["TCS.NS", "INFY.NS", "WIPRO.NS", "TECHM.NS", "LTIM.NS"],
    "TECHM.NS":      ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "LTIM.NS"],
    "LTIM.NS":       ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "PERSISTENT.NS"],
    "PERSISTENT.NS": ["INFY.NS", "LTIM.NS", "COFORGE.NS", "MPHASIS.NS", "KPIT.NS"],
    # US Financials
    "JPM":   ["BAC", "WFC", "GS", "MS", "C"],
    "BAC":   ["JPM", "WFC", "C", "USB", "PNC"],
    # Market indices / ETFs — no peers
}


def get_peer_group(ticker: str) -> List[str]:
    """
    Return the curated peer group for the given ticker.

    Performs a case-insensitive lookup against the PEER_MAP. If the ticker
    is not in the map, returns an empty list (callers should handle this).

    Args:
        ticker (str): Stock symbol (case-insensitive).

    Returns:
        list[str]: Peer ticker symbols, or [] if ticker is unknown.
    """
    canonical = ticker.upper().strip()
    peers = PEER_MAP.get(canonical, [])
    if peers:
        logger.info("Peer group for %s: %s", canonical, peers)
    else:
        logger.info("No peer group found for %s", canonical)
    return peers
