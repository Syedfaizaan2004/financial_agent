"""
backend/app/dependencies.py

Shared FastAPI dependency functions.

This module acts as the central injection point for all reusable dependencies
throughout the application (config, database sessions, auth, caching, etc.).
Add new dependencies here as features are built out.
"""

from typing import Generator

from fastapi import Depends

from backend.app.config import Settings, get_settings


# ---------------------------------------------------------------------------
# Configuration dependency
# ---------------------------------------------------------------------------

def get_config(settings: Settings = Depends(get_settings)) -> Settings:
    """
    FastAPI dependency that yields the application Settings instance.

    Usage:
        @router.get("/some-route")
        async def some_route(config: Settings = Depends(get_config)):
            return {"app": config.APP_NAME}
    """
    return settings


# ---------------------------------------------------------------------------
# Database session dependency (future-ready)
# ---------------------------------------------------------------------------

def get_db() -> Generator:
    """
    FastAPI dependency that provides a database session.

    Currently a stub — will be wired to SQLAlchemy / SQLModel session once
    the database layer is implemented in a future phase.

    Usage:
        @router.get("/some-route")
        async def some_route(db = Depends(get_db)):
            ...
    """
    # TODO: Replace with real session factory when DB models are ready.
    #   from backend.core.database import SessionLocal
    #   db = SessionLocal()
    #   try:
    #       yield db
    #   finally:
    #       db.close()
    try:
        yield None  # Placeholder — no DB connection yet
    finally:
        pass  # Cleanup hook for future DB teardown


# ---------------------------------------------------------------------------
# Future dependency stubs (uncomment as features are added)
# ---------------------------------------------------------------------------

# def get_cache_client():
#     """Return a Redis / in-memory cache client."""
#     ...

# def get_current_user(token: str = Depends(oauth2_scheme)):
#     """Validate JWT and return the current authenticated user."""
#     ...
