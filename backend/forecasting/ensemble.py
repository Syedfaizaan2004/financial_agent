"""
backend/forecasting/ensemble.py

Ensemble forecasting module for the Financial & Market Research Agent.

Combines TFT and XGBoost model outputs into a single, structured forecast.
If one model is unavailable (e.g. dependencies not installed), the ensemble
degrades gracefully and returns output from the available model only.

Confidence calculation:
  - Base confidence = average of TFT raw_prediction and XGBoost prob_up
  - Boosted by +0.05 when both models agree on direction
  - Reduced by -0.05 when models disagree (capped to [0.0, 0.99])
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def generate_forecast(ticker: str) -> Dict[str, Any]:
    """
    Generate a combined forecast for the given ticker using TFT + XGBoost.

    The function runs both models independently, handles individual model
    failures gracefully, and combines their outputs into a structured result.

    Args:
        ticker (str): Validated uppercase stock symbol (e.g. 'AAPL').

    Returns:
        dict: Structured forecast result containing:
            ticker (str)
            trend (str): 'upward' | 'downward' | 'neutral'
            confidence (float): Combined model confidence [0.0, 0.99]
            forecast_horizon_days (int)
            expected_movement_percent (float)
            model_agreement (bool): True if both models predict same direction
            models_used (list[str]): Which models contributed to this forecast
            tft_output (dict | None): Raw TFT prediction (or None if unavailable)
            xgb_output (dict | None): Raw XGBoost prediction (or None if unavailable)

    Raises:
        RuntimeError: If both models fail — at least one must succeed.
    """
    tft_result: Optional[Dict[str, Any]] = None
    xgb_result: Optional[Dict[str, Any]] = None
    models_used: list[str] = []

    # --- Run TFT inference (non-fatal failure) ---
    try:
        from backend.forecasting.tft.inference import predict_tft
        tft_result = predict_tft(ticker)
        models_used.append("TFT")
        logger.info("TFT inference succeeded for %s: trend=%s", ticker, tft_result["trend"])
    except RuntimeError as e:
        logger.warning("TFT model unavailable for %s: %s", ticker, e)
    except Exception as e:  # pylint: disable=broad-except
        logger.error("TFT inference error for %s: %s", ticker, e)

    # --- Run XGBoost inference (non-fatal failure) ---
    try:
        from backend.forecasting.xgboost.inference import predict_xgb
        xgb_result = predict_xgb(ticker)
        models_used.append("XGBoost")
        logger.info(
            "XGBoost inference succeeded for %s: prob_up=%.4f",
            ticker, xgb_result["prob_up"],
        )
    except RuntimeError as e:
        logger.warning("XGBoost model unavailable for %s: %s", ticker, e)
    except Exception as e:  # pylint: disable=broad-except
        logger.error("XGBoost inference error for %s: %s", ticker, e)

    # --- Require at least one model ---
    if tft_result is None and xgb_result is None:
        raise RuntimeError(
            "Both TFT and XGBoost models are unavailable. "
            "Ensure torch + pytorch-forecasting and xgboost are installed."
        )

    # -------------------------------------------------------------------
    # Combine outputs
    # -------------------------------------------------------------------

    # Determine trend direction from available models
    tft_direction = tft_result["trend"] if tft_result else None
    xgb_direction = xgb_result["predicted_direction"] if xgb_result else None

    # Resolve primary trend
    if tft_direction and xgb_direction:
        # Both available: agree → use agreed direction; disagree → TFT leads
        trend = tft_direction if tft_direction == xgb_direction else tft_direction
        model_agreement = tft_direction == xgb_direction
    elif tft_direction:
        trend = tft_direction
        model_agreement = False   # Only one model, no agreement possible
    else:
        trend = xgb_direction    # type: ignore[assignment]  (guaranteed non-None here)
        model_agreement = False

    # Resolve expected movement
    if tft_result:
        expected_movement_percent = tft_result["expected_movement_percent"]
    else:
        # Derive from XGBoost probability
        prob_up = xgb_result["prob_up"]  # type: ignore[index]
        sign = 1 if prob_up >= 0.5 else -1
        expected_movement_percent = round(sign * abs(prob_up - 0.5) * 20, 2)

    # Resolve forecast horizon
    forecast_horizon_days: int
    if tft_result:
        forecast_horizon_days = tft_result["forecast_horizon_days"]
    else:
        from backend.app.config import get_settings
        forecast_horizon_days = get_settings().FORECAST_HORIZON_DAYS

    # -------------------------------------------------------------------
    # Confidence calculation
    # -------------------------------------------------------------------
    tft_score = tft_result["raw_prediction"] if tft_result else None
    xgb_score = xgb_result["prob_up"] if xgb_result else None

    if tft_score is not None and xgb_score is not None:
        base_confidence = (tft_score + xgb_score) / 2
    elif tft_score is not None:
        base_confidence = tft_score
    else:
        base_confidence = xgb_score  # type: ignore[assignment]

    # Agreement bonus / disagreement penalty
    if tft_direction and xgb_direction:
        adjustment = +0.05 if model_agreement else -0.05
    else:
        adjustment = 0.0

    confidence = round(max(0.0, min(0.99, base_confidence + adjustment)), 4)

    # -------------------------------------------------------------------
    # Structured response
    # -------------------------------------------------------------------
    return {
        "ticker": ticker,
        "trend": trend,
        "confidence": confidence,
        "forecast_horizon_days": forecast_horizon_days,
        "expected_movement_percent": expected_movement_percent,
        "model_agreement": model_agreement,
        "models_used": models_used,
        "tft_output": tft_result,
        "xgb_output": xgb_result,
    }
