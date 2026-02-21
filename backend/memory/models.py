"""
backend/memory/models.py

SQLAlchemy ORM models for the Memory & Personalization system.

Tables:
    user_preferences — persistent user research profile
    session_queries  — recent query history per user
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import List

from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.types import TypeDecorator, TEXT

from backend.db.session import Base


# ---------------------------------------------------------------------------
# Custom type: JSON list stored as a TEXT column
# ---------------------------------------------------------------------------

class JSONList(TypeDecorator):
    """Store a Python list as a JSON string in a TEXT column."""
    impl          = TEXT
    cache_ok      = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return "[]"
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return []
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return []


# ---------------------------------------------------------------------------
# User Preferences
# ---------------------------------------------------------------------------

class UserPreferences(Base):
    """
    Persistent user research profile.

    Stores risk tolerance, preferred financial metrics, sector
    interests, and investment time horizon. No sensitive personal
    data — only research preferences.

    Columns:
        user_id           — primary key (provided by caller, e.g. 'default')
        risk_profile      — 'conservative' | 'moderate' | 'aggressive'
        preferred_metrics — list of metric names (JSON-encoded)
        preferred_sectors — list of sector names (JSON-encoded)
        time_horizon      — 'short' | 'medium' | 'long'
        last_updated      — UTC timestamp of last save/update
    """
    __tablename__ = "user_preferences"

    user_id           = Column(String(64),  primary_key=True, index=True)
    risk_profile      = Column(String(32),  nullable=False, default="moderate")
    preferred_metrics = Column(JSONList(),   nullable=False, default=list)
    preferred_sectors = Column(JSONList(),   nullable=False, default=list)
    time_horizon      = Column(String(16),  nullable=False, default="medium")
    last_updated      = Column(DateTime,    nullable=False,
                               default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "user_id":           self.user_id,
            "risk_profile":      self.risk_profile,
            "preferred_metrics": self.preferred_metrics,
            "preferred_sectors": self.preferred_sectors,
            "time_horizon":      self.time_horizon,
            "last_updated":      self.last_updated.isoformat() if self.last_updated else None,
        }

    def __repr__(self) -> str:
        return (
            f"<UserPreferences user_id={self.user_id!r} "
            f"risk={self.risk_profile!r} horizon={self.time_horizon!r}>"
        )


# ---------------------------------------------------------------------------
# Session Query History
# ---------------------------------------------------------------------------

class SessionQuery(Base):
    """
    Recent query history per user.

    Stores the last N queries a user has made so the agent can
    provide context-aware follow-up recommendations.

    Columns:
        id         — auto-increment primary key
        user_id    — reference to user (not a foreign key — keep it simple)
        query      — raw query string
        ticker     — extracted ticker (may be None)
        intent     — detected intent type
        created_at — UTC timestamp
    """
    __tablename__ = "session_queries"

    id         = Column(Integer,     primary_key=True, autoincrement=True)
    user_id    = Column(String(64),  nullable=False, index=True)
    query      = Column(Text,        nullable=False)
    ticker     = Column(String(16),  nullable=True)
    intent     = Column(String(32),  nullable=True)
    created_at = Column(DateTime,    nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "user_id":    self.user_id,
            "query":      self.query,
            "ticker":     self.ticker,
            "intent":     self.intent,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
