"""
backend/api/routes/compare.py

Peer comparison API endpoint for the Financial & Market Research Agent.

Endpoint:
    GET /compare/{ticker}
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/compare", tags=["Peer Comparison"])


@router.get(
    "/{ticker}",
    summary="Peer Comparison",
    description=(
        "Returns a full quantitative peer comparison for the given stock ticker.\n\n"
        "**Includes per-metric positioning vs peer group average**:\n"
        "- Valuation: PE ratio, Price-to-Book\n"
        "- Profitability: Net margin, ROE\n"
        "- Growth: Revenue growth YoY\n"
        "- Leverage: Debt-to-Equity\n\n"
        "Returns **404** if no peer group is defined for the ticker.\n"
        "Returns **503** if yfinance is not available.\n"
        "Returns **500** on unexpected errors."
    ),
    response_description="Structured peer comparison with positioning labels and summary insights",
)
async def get_comparison(ticker: str) -> Dict[str, Any]:
    """
    GET /compare/{ticker}

    Looks up the ticker's peer group, fetches metrics for all companies,
    and returns quantitative positioning for each key financial metric.

    Args:
        ticker (str): Stock symbol (case-insensitive). E.g. AAPL, TSLA, TCS.NS

    Returns:
        dict: Structured peer comparison result.

    Raises:
        HTTPException 404: No peer group defined for ticker
        HTTPException 503: yfinance not installed
        HTTPException 500: Unexpected analysis error
    """
    canonical = ticker.upper().strip()
    logger.info("Peer comparison requested for: %s", canonical)

    # Step 1: Resolve peer group
    from backend.core.peer_fetcher import get_peer_group
    peers = get_peer_group(canonical)

    if not peers:
        return {
            "ticker": canonical,
            "peer_group": [],
            "message": (
                f"No peer group is currently defined for '{canonical}'. "
                "The comparison engine covers major US tech, Indian IT, and EV tickers. "
                "Contact your administrator to extend the peer map."
            ),
            "valuation_comparison": {},
            "profitability_comparison": {},
            "growth_comparison": {},
            "leverage_comparison": {},
            "summary": [],
        }

    # Step 2: Run comparison
    try:
        from backend.core.peer_comparison import compare_with_peers
        result = compare_with_peers(canonical, peers)
    except RuntimeError as exc:
        error_msg = str(exc)
        if "yfinance" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="Market data provider (yfinance) not available. pip install yfinance",
            ) from exc
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("Peer comparison failed for %s", canonical)
        raise HTTPException(
            status_code=500,
            detail=f"Comparison error: {type(exc).__name__}: {exc}",
        ) from exc

    logger.info(
        "Peer comparison complete for %s vs %d peers | summary_count=%d",
        canonical, len(peers), len(result.get("summary", [])),
    )
    return result
