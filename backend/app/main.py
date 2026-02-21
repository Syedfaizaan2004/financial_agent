"""
backend/app/main.py

FastAPI application entry point for the Financial & Market Research Agent.

This module:
  - Initialises the FastAPI application instance
  - Loads environment variables via the config module
  - Configures logging (level + file) from .env settings
  - Registers CORS middleware
  - Includes all API routers
  - Runs startup / shutdown lifecycle hooks

Run with:
    uvicorn backend.app.main:app --reload
  or, from inside the backend/ directory:
    uvicorn app.main:app --reload
"""

import logging
import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.router import api_router
from backend.app.config import get_settings
from backend.app.cors import CORS_SETTINGS

# ---------------------------------------------------------------------------
# Load settings first (needed to configure logging level + log file)
# ---------------------------------------------------------------------------
settings = get_settings()

# ---------------------------------------------------------------------------
# Logging configuration — level and output file driven by .env
# ---------------------------------------------------------------------------
_log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

_handlers: list = [logging.StreamHandler(sys.stdout)]
if settings.LOG_FILE:
    _handlers.append(logging.FileHandler(settings.LOG_FILE, encoding="utf-8"))

logging.basicConfig(
    level=_log_level,
    format="%(asctime)s  [%(levelname)s]  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=_handlers,
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# FastAPI application factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "🏦 Financial & Market Research Agent API\n\n"
        "A production-grade backend acting as a junior equity research analyst. "
        "Capabilities include stock trend forecasting (TFT & XGBoost), "
        "company fundamental analysis, financial risk detection, "
        "peer comparison, scenario stress testing, investment memo generation, "
        "confidence scoring, contradiction detection, and memory-based personalization."
    ),
    version="0.1.0",
    docs_url="/docs",            # Swagger UI
    redoc_url="/redoc",          # ReDoc UI
    openapi_url="/openapi.json",
    debug=settings.DEBUG,
)

# ---------------------------------------------------------------------------
# Middleware — CORS
# ---------------------------------------------------------------------------
app.add_middleware(CORSMiddleware, **CORS_SETTINGS)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(api_router)

# ---------------------------------------------------------------------------
# Lifecycle events
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def on_startup() -> None:
    """
    Startup hook: runs once when the application boots.

    Logs key configuration values, verifies model files exist, and
    reports the supported ticker count loaded from stocks_used.pkl.
    """
    logger.info("=" * 60)
    logger.info("🚀  Starting      : %s", settings.APP_NAME)
    logger.info("    Environment   : %s", settings.APP_ENV)
    logger.info("    Debug mode    : %s", settings.DEBUG)
    logger.info("    LLM Provider  : %s (%s)", settings.LLM_PROVIDER, settings.LOCAL_LLM_MODEL)
    logger.info("    Forecast days : %s  (encoder: %s)", settings.FORECAST_HORIZON_DAYS, settings.ENCODER_LENGTH)
    logger.info("    Log level     : %s  →  %s", settings.LOG_LEVEL, settings.LOG_FILE)
    logger.info("    Docs          : http://%s:%s/docs", settings.HOST, settings.PORT)
    logger.info("=" * 60)

    # --- Verify forecasting model files exist on disk ---
    _check_model_assets()

    # --- Log supported ticker universe ---
    _log_ticker_universe()

    # --- Initialise memory database tables ---
    try:
        from backend.db.session import init_db
        init_db()
        logger.info("    🧠  Memory DB     : tables ready (SQLite)")
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("    ⚠️   Memory DB init failed: %s", exc)

    pass


@app.on_event("shutdown")
async def on_shutdown() -> None:
    """Shutdown hook: runs when the application is stopping."""
    logger.info("👋  %s is shutting down. Goodbye!", settings.APP_NAME)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_model_assets() -> None:
    """
    Verify that pre-trained model files are present on disk.

    Uses the .env-aligned attribute names from Settings.
    Logs ✅ / ⚠️ for each asset — never raises so the app always starts.
    """
    assets = {
        "TFT model":          settings.TFT_MODEL_PATH,
        "TFT params":         settings.TFT_PARAMS_PATH,        # TFT_PARAMS_PATH from .env
        "XGBoost model":      settings.XGB_MODEL_PATH,
        "Feature list":       settings.FEATURES_PATH,
        "Stocks list":        settings.STOCKS_LIST_PATH,        # STOCKS_LIST_PATH from .env
    }

    all_present = True
    for label, path in assets.items():
        if os.path.exists(path):
            logger.info("    ✅  %-22s found  (%s)", label, path)
        else:
            logger.warning("    ⚠️   %-22s NOT found  (%s)", label, path)
            all_present = False

    if all_present:
        logger.info("    🎯  All model assets detected — forecasting ready.")
    else:
        logger.warning(
            "    ⚠️   One or more model assets are missing. "
            "Forecasting endpoints will return stubs until assets are present."
        )


def _log_ticker_universe() -> None:
    """
    Load and log the supported ticker universe from stocks_used.pkl.

    Called at startup to confirm the forecasting ticker list is accessible
    and to surface the supported symbols for operators.
    """
    try:
        from backend.forecasting.utils import get_supported_tickers
        tickers = get_supported_tickers()
        logger.info(
            "    📈  Ticker universe : %d tickers supported",
            len(tickers),
        )
        logger.info("    📋  Tickers : %s", ", ".join(sorted(tickers)))
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("    ⚠️   Could not load ticker universe: %s", exc)
