"""
backend/api/routes/forecast.py

Forecast API endpoint for the Financial & Market Research Agent.

Wires the ticker validator and ensemble forecasting module to the HTTP layer.
Returns a structured JSON response or clear error messages.

Endpoint:
    GET /forecast/{ticker}
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException

from backend.app.config import Settings
from backend.app.dependencies import get_config
from backend.forecasting.utils import validate_ticker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/forecast", tags=["Forecasting"])


@router.get(
    "/{ticker}",
    summary="Stock Forecast",
    description=(
        "Returns a combined TFT + XGBoost forecast for the given stock ticker.\n\n"
        "**Supported tickers**: AAPL, MSFT, GOOGL, NVDA, TSLA, META, AMD, "
        "TCS.NS, INFY.NS, WIPRO.NS, HCLTECH.NS, TECHM.NS, LTIM.NS, PERSISTENT.NS\n\n"
        "Returns **404** if the ticker is not in the trained model universe.\n"
        "Returns **503** if ML model dependencies (torch / xgboost) are not installed."
    ),
    response_description="Structured forecast with trend, confidence, and model details",
)
async def get_forecast(
    ticker: str,
    config: Settings = Depends(get_config),
) -> Dict[str, Any]:
    """
    GET /forecast/{ticker}

    Args:
        ticker (str): Stock symbol (case-insensitive). E.g. AAPL, tsla, INFY.NS
        config (Settings): Injected app configuration (unused directly here;
                           models read config themselves via get_settings()).

    Returns:
        dict: Full ensemble forecast result including:
            - ticker, trend, confidence
            - forecast_horizon_days, expected_movement_percent
            - model_agreement, models_used
            - tft_output, xgb_output (raw model results)

    Raises:
        HTTPException 404: Ticker not in trained model universe
        HTTPException 503: Both ML models unavailable (dependencies missing)
        HTTPException 500: Unexpected internal error
    """
    # --- Step 1: Validate ticker (raises 404 if unsupported) ---
    canonical_ticker = validate_ticker(ticker)
    logger.info("Forecast requested for ticker: %s", canonical_ticker)

    # --- Step 2: Run ensemble forecast ---
    try:
        from backend.forecasting.ensemble import generate_forecast
        result = generate_forecast(canonical_ticker)
    except RuntimeError as exc:
        # Both models unavailable — missing dependencies
        logger.error("Forecast failed for %s: %s", canonical_ticker, exc)
        raise HTTPException(
            status_code=503,
            detail=(
                f"Forecasting models are not available: {exc}. "
                "Please ensure all ML dependencies are installed: "
                "pip install torch pytorch-forecasting xgboost yfinance"
            ),
        ) from exc
    except Exception as exc:  # pylint: disable=broad-except
        # Unexpected errors — log full traceback, return safe message
        logger.exception("Unexpected error during forecast for %s", canonical_ticker)
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred during forecasting: {type(exc).__name__}",
        ) from exc

    logger.info(
        "Forecast complete for %s: trend=%s confidence=%.4f agreement=%s",
        canonical_ticker,
        result["trend"],
        result["confidence"],
        result["model_agreement"],
    )
    return result
