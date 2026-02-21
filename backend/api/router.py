"""
backend/api/router.py

Central API router for the Financial & Market Research Agent.

All sub-routers are registered here and this module is imported by
main.py. Adding a new feature area is as simple as importing its router
and calling include_router() below.
"""

from fastapi import APIRouter

from backend.api.routes import agent, compare, forecast, health, research, scenario, memory, demo

# ---------------------------------------------------------------------------
# Root API router
# ---------------------------------------------------------------------------
api_router = APIRouter()

# --- Core ---
api_router.include_router(health.router)               # GET /health

# --- Research, Forecasting & Comparison ---
api_router.include_router(forecast.router)             # GET /forecast/{ticker}
api_router.include_router(research.router)             # GET /research/{ticker}
api_router.include_router(compare.router)              # GET /compare/{ticker}
api_router.include_router(scenario.router)             # GET /scenario/{ticker}
api_router.include_router(agent.router)                # POST /agent

# --- Memory & Personalization ---
api_router.include_router(memory.router)               # /memory/...

# --- Demo & Presentation ---
api_router.include_router(demo.router, prefix="/demo") # /demo/...

# ---------------------------------------------------------------------------
# Future routers (uncomment / add as features are built)
# ---------------------------------------------------------------------------
# from backend.api.routes import agent, risk, screener, fundamentals
# api_router.include_router(agent.router)              # POST /agent/query
# api_router.include_router(risk.router)               # GET /risk/{ticker}
# api_router.include_router(screener.router)           # GET /screener
# api_router.include_router(fundamentals.router)       # GET /fundamentals/{ticker}
