"""
backend/db/session.py

SQLAlchemy database engine and session factory.

Uses SQLite by default (DATABASE_URL from .env). Designed to be
simple and hackathon-friendly — no migrations required. Tables are
created automatically on startup via create_all().

Usage:
    from backend.db.session import get_db, engine
    from backend.db.session import Base   # for model declarations

    # FastAPI dependency injection:
    def my_endpoint(db: Session = Depends(get_db)): ...

    # Direct use:
    with SessionLocal() as db:
        db.add(obj)
        db.commit()
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database URL — defaults to local SQLite file
# ---------------------------------------------------------------------------

_DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "agent_memory.db"
_DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{_DEFAULT_DB_PATH}",
)

logger.info("[db/session] Database URL: %s", DATABASE_URL)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=_connect_args,
    echo=False,           # Set True to log all SQL statements
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# ---------------------------------------------------------------------------
# Declarative base — all ORM models inherit from this
# ---------------------------------------------------------------------------

Base = declarative_base()


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session and ensure it is closed after use.

    Use as a FastAPI dependency:
        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Create all tables defined by ORM models.

    Called once at application startup. Safe to call multiple times
    (idempotent — no-op if tables already exist).
    """
    # Import all models so SQLAlchemy knows about them before create_all
    import backend.memory.models  # noqa: F401  (side-effect import)
    Base.metadata.create_all(bind=engine)
    logger.info("[db/session] Database tables created / verified.")
