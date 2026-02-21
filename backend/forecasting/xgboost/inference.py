"""
backend/forecasting/xgboost/inference.py

XGBoost inference module for the Financial & Market Research Agent.

Loads the pre-trained XGBoost classifier ONCE using the singleton pattern
and exposes predict_xgb() for generating upward-movement probability scores.

Features used by the model: ['RSI', 'MACD', 'Volatility', 'Return']
These are computed from real recent price data fetched via yfinance.

Design decisions:
- CPU only (XGBoost is always CPU unless explicitly set otherwise)
- Lazy loading: model loaded on first predict call, not at import
- Graceful degradation: returns clear RuntimeError if xgboost/yfinance not installed
- Feature computation mirrors training-time logic (RSI, MACD, Volatility, Return)
- No training code — inference only
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton state
# ---------------------------------------------------------------------------
_predictor_instance: Optional["XGBPredictor"] = None


class XGBPredictor:
    """
    Singleton class for XGBoost model inference.

    The model and feature list are loaded exactly once on first use
    and cached for the lifetime of the application process.
    """

    _model: Any = None
    _features: List[str] = []
    _loaded: bool = False

    def __init__(self, model_path: str, features_path: str) -> None:
        """
        Store paths only — actual loading is deferred to first predict call.

        Args:
            model_path (str): Path to xgb_model.pkl
            features_path (str): Path to features.pkl
        """
        self._model_path = model_path
        self._features_path = features_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_loaded(self) -> None:
        """
        Load the XGBoost model and feature list if not already loaded.

        Raises:
            RuntimeError: If xgboost is not installed.
            FileNotFoundError: If model files are missing from disk.
        """
        if self._loaded:
            return

        # --- Validate optional dependencies ---
        try:
            import xgboost  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "xgboost is required for XGBoost inference. "
                "Install it with: pip install xgboost"
            ) from exc

        import pickle
        import xgboost as xgb

        # --- Load feature list ---
        logger.info("Loading feature list from: %s", self._features_path)
        with open(self._features_path, "rb") as f:
            self._features = pickle.load(f)
        logger.info("Features loaded: %s ✅", self._features)

        # --- Load XGBoost model ---
        logger.info("Loading XGBoost model from: %s", self._model_path)
        with open(self._model_path, "rb") as f:
            self._model = pickle.load(f)
        logger.info("XGBoost model loaded ✅  (type: %s)", type(self._model).__name__)

        self._loaded = True

    def _fetch_features(self, ticker: str) -> np.ndarray:
        """
        Fetch recent OHLCV data and compute technical indicator features.

        Features (matching training-time computation):
          - RSI     : 14-period Relative Strength Index (0–100)
          - MACD    : MACD line value (EMA12 − EMA26)
          - Volatility: 20-day rolling std of daily returns (annualised x100)
          - Return  : 5-day cumulative return (%)

        Args:
            ticker (str): Validated uppercase stock symbol.

        Returns:
            np.ndarray: Shape (1, n_features) array ready for XGBoost.

        Raises:
            RuntimeError: If yfinance is not installed or data fetch fails.
        """
        try:
            import yfinance as yf
        except ImportError as exc:
            raise RuntimeError(
                "yfinance is required for feature computation. "
                "Install it with: pip install yfinance"
            ) from exc

        logger.info("Fetching 90-day OHLCV data for %s via yfinance...", ticker)
        df = yf.download(ticker, period="90d", interval="1d", progress=False, auto_adjust=True)

        if df.empty or len(df) < 30:
            raise RuntimeError(
                f"Insufficient market data returned for ticker '{ticker}'. "
                "Check internet connection or try again later."
            )

        close = df["Close"].squeeze()

        # --- RSI (14-period) ---
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss.replace(0, float("nan"))
        rsi = float((100 - (100 / (1 + rs))).iloc[-1])

        # --- MACD (EMA12 − EMA26) ---
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = float((ema12 - ema26).iloc[-1])

        # --- Volatility (20-day rolling std of returns, annualised ×100) ---
        daily_returns = close.pct_change()
        volatility = float(daily_returns.rolling(20).std().iloc[-1] * 100)

        # --- 5-day cumulative return (%) ---
        ret = float((close.iloc[-1] / close.iloc[-5] - 1) * 100)

        feature_vector = np.array([[rsi, macd, volatility, ret]], dtype=np.float32)
        logger.info(
            "Features for %s — RSI=%.2f  MACD=%.4f  Volatility=%.4f  Return=%.4f",
            ticker, rsi, macd, volatility, ret,
        )
        return feature_vector

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def predict_xgb(self, ticker: str) -> Dict[str, Any]:
        """
        Generate an upward-movement probability for the given ticker.

        Handles two model serialization styles automatically:
          - xgb.Booster  → predict via DMatrix (native XGBoost)
          - sklearn-style → predict via numpy array / DataFrame

        Args:
            ticker (str): Validated uppercase stock symbol (e.g. 'AAPL').

        Returns:
            dict:
                prob_up (float): Probability of upward price movement [0, 1]
                prob_down (float): Probability of downward price movement [0, 1]
                predicted_direction (str): 'upward' | 'downward'
                feature_values (dict): Computed feature values used for prediction
                feature_importance (dict): Model's feature importance scores

        Raises:
            RuntimeError: If xgboost or yfinance is not installed.
            FileNotFoundError: If model files are missing.
        """
        self._ensure_loaded()
        import xgboost as xgb
        import pandas as pd

        # Compute real feature values from live market data
        feature_vector = self._fetch_features(ticker)  # shape (1, n_features)

        # Build a named DataFrame so XGBoost can match feature names exactly,
        # avoiding the "Unknown data type: DMatrix" warning.
        feature_df = pd.DataFrame(feature_vector, columns=self._features)

        # --- Route by model type ---
        model_type = type(self._model).__name__

        if isinstance(self._model, xgb.Booster):
            # Native Booster: must use DMatrix
            dmatrix = xgb.DMatrix(feature_df)
            raw_probs = self._model.predict(dmatrix)
        else:
            # sklearn-style XGBClassifier / XGBRegressor
            if hasattr(self._model, "predict_proba"):
                raw_probs = self._model.predict_proba(feature_df)
                # predict_proba returns (1, n_classes) — grab column index 1 (prob_up)
                if raw_probs.ndim == 2:
                    prob_up = float(raw_probs[0][1])
                else:
                    prob_up = float(raw_probs[0])
            else:
                raw_probs = self._model.predict(feature_df)
                prob_up = float(raw_probs[0])

            prob_down = round(1.0 - prob_up, 4)
            prob_up   = round(prob_up, 4)
            predicted_direction = "upward" if prob_up >= 0.5 else "downward"

            # Feature importance
            try:
                importance_raw = self._model.get_booster().get_score(importance_type="gain")
                total = sum(importance_raw.values()) or 1
                feature_importance = {k: round(v / total, 4) for k, v in importance_raw.items()}
            except Exception:  # pylint: disable=broad-except
                feature_importance = {}

            feature_values = {
                name: round(float(feature_vector[0][i]), 4)
                for i, name in enumerate(self._features)
            }
            return {
                "prob_up": prob_up,
                "prob_down": prob_down,
                "predicted_direction": predicted_direction,
                "feature_values": feature_values,
                "feature_importance": feature_importance,
            }

        # --- Handle native Booster raw_probs ---
        if raw_probs.ndim == 1:
            prob_up = float(raw_probs[0])
        else:
            prob_up = float(raw_probs[0][1])

        prob_down = round(1.0 - prob_up, 4)
        prob_up   = round(prob_up, 4)
        predicted_direction = "upward" if prob_up >= 0.5 else "downward"

        # Feature importance (Booster-native)
        try:
            importance_raw = self._model.get_score(importance_type="gain")
            total = sum(importance_raw.values()) or 1
            feature_importance = {k: round(v / total, 4) for k, v in importance_raw.items()}
        except Exception:  # pylint: disable=broad-except
            feature_importance = {}

        feature_values = {
            name: round(float(feature_vector[0][i]), 4)
            for i, name in enumerate(self._features)
        }

        return {
            "prob_up": prob_up,
            "prob_down": prob_down,
            "predicted_direction": predicted_direction,
            "feature_values": feature_values,
            "feature_importance": feature_importance,
        }



# ---------------------------------------------------------------------------
# Factory / accessor
# ---------------------------------------------------------------------------

def get_xgb_predictor() -> XGBPredictor:
    """
    Return the application-wide XGBoost predictor singleton.

    Returns:
        XGBPredictor: The singleton predictor ready for inference.
    """
    global _predictor_instance
    if _predictor_instance is None:
        from backend.app.config import get_settings
        cfg = get_settings()
        _predictor_instance = XGBPredictor(
            model_path=cfg.XGB_MODEL_PATH,
            features_path=cfg.FEATURES_PATH,
        )
    return _predictor_instance


def predict_xgb(ticker: str) -> Dict[str, Any]:
    """
    Convenience function: run XGBoost inference via the singleton predictor.

    Args:
        ticker (str): Validated uppercase stock symbol.

    Returns:
        dict: Structured XGBoost prediction output.
    """
    return get_xgb_predictor().predict_xgb(ticker)
