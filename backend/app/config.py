"""
backend/app/config.py

Environment configuration loader for the Financial & Market Research Agent.

Uses python-dotenv to load and expose all application settings from the
`.env` file in a strongly-typed Settings class.  Every key here maps
1-to-1 to a variable in the .env file — do not add defaults that shadow
misconfigured environments silently.
"""

import os
from functools import lru_cache
from typing import List

from dotenv import load_dotenv

# Load .env from the project root (two levels up from this file)
load_dotenv()


class Settings:
    """
    Central configuration class.

    All attribute names exactly match the keys defined in .env.
    Add new settings here as the project grows.
    """

    # -----------------------------------------------------------------------
    # 🌐 Application
    # -----------------------------------------------------------------------
    APP_NAME: str = os.getenv("APP_NAME", "Financial Research Agent")
    APP_ENV: str = os.getenv("APP_ENV", "production")
    DEBUG: bool = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # -----------------------------------------------------------------------
    # 🤖 AI / LLM Configuration
    # -----------------------------------------------------------------------
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "local")          # local | groq | gemini
    LOCAL_LLM_MODEL: str = os.getenv("LOCAL_LLM_MODEL", "llama3")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # -----------------------------------------------------------------------
    # 📊 Forecast Model Settings
    # -----------------------------------------------------------------------
    TFT_MODEL_PATH: str = os.getenv(
        "TFT_MODEL_PATH", "backend/forecasting/tft/tft_model.pth"
    )
    TFT_PARAMS_PATH: str = os.getenv(
        "TFT_PARAMS_PATH", "backend/forecasting/tft/tft_dataset_params.pkl"
    )
    XGB_MODEL_PATH: str = os.getenv(
        "XGB_MODEL_PATH", "backend/forecasting/xgboost/xgb_model.pkl"
    )
    FEATURES_PATH: str = os.getenv(
        "FEATURES_PATH", "backend/forecasting/features.pkl"
    )
    STOCKS_LIST_PATH: str = os.getenv(
        "STOCKS_LIST_PATH", "backend/forecasting/stocks_used.pkl"
    )
    FORECAST_HORIZON_DAYS: int = int(os.getenv("FORECAST_HORIZON_DAYS", "30"))
    ENCODER_LENGTH: int = int(os.getenv("ENCODER_LENGTH", "60"))

    # -----------------------------------------------------------------------
    # 📈 Market Data Settings
    # -----------------------------------------------------------------------
    # Stored as comma-separated string in .env; exposed as a list here.
    DATA_PROVIDERS: List[str] = [
        p.strip()
        for p in os.getenv("DATA_PROVIDERS", "yfinance").split(",")
        if p.strip()
    ]
    CACHE_ENABLED: bool = os.getenv("CACHE_ENABLED", "True").lower() in ("true", "1", "yes")
    CACHE_TTL_MINUTES: int = int(os.getenv("CACHE_TTL_MINUTES", "60"))

    # -----------------------------------------------------------------------
    # 📈 Data API Keys
    # -----------------------------------------------------------------------
    ALPHA_VANTAGE_KEY: str = os.getenv("ALPHA_VANTAGE_KEY", "")

    # -----------------------------------------------------------------------
    # 🧠 Agent Settings
    # -----------------------------------------------------------------------
    QUICK_MODE_TIMEOUT: int = int(os.getenv("QUICK_MODE_TIMEOUT", "30"))
    DEEP_MODE_TIMEOUT: int = int(os.getenv("DEEP_MODE_TIMEOUT", "180"))
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.65"))

    # -----------------------------------------------------------------------
    # 🗄 Database Settings
    # -----------------------------------------------------------------------
    DB_TYPE: str = os.getenv("DB_TYPE", "sqlite")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./financial_agent.db")

    # -----------------------------------------------------------------------
    # 🧠 Memory & Personalization
    # -----------------------------------------------------------------------
    MEMORY_ENABLED: bool = os.getenv("MEMORY_ENABLED", "True").lower() in ("true", "1", "yes")
    DEFAULT_RISK_PROFILE: str = os.getenv("DEFAULT_RISK_PROFILE", "moderate")
    DEFAULT_TIME_HORIZON: str = os.getenv("DEFAULT_TIME_HORIZON", "long_term")

    # -----------------------------------------------------------------------
    # 🔐 Security
    # -----------------------------------------------------------------------
    API_KEY_REQUIRED: bool = os.getenv("API_KEY_REQUIRED", "False").lower() in ("true", "1", "yes")
    API_KEY: str = os.getenv("API_KEY", "")

    # -----------------------------------------------------------------------
    # 📊 Logging
    # -----------------------------------------------------------------------
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "app.log")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached singleton Settings instance.

    Using lru_cache ensures the .env file is parsed only once per
    application lifetime, improving startup performance.
    """
    return Settings()

# reload
