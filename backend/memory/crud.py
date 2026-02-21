"""
backend/memory/crud.py

CRUD operations for user preferences and session query history.

All functions accept an active SQLAlchemy Session, making them
compatible with both FastAPI dependency injection and direct use.

Functions:
    save_preferences(db, user_id, prefs)    — insert or replace
    get_preferences(db, user_id) -> dict    — retrieve (or defaults)
    update_preferences(db, user_id, prefs)  — partial update
    delete_preferences(db, user_id)         — remove record
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from backend.memory.models import UserPreferences, SessionQuery

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default preferences — returned when no record exists
# ---------------------------------------------------------------------------

DEFAULT_PREFERENCES: Dict[str, Any] = {
    "risk_profile":      "moderate",
    "preferred_metrics": [],
    "preferred_sectors": [],
    "time_horizon":      "medium",
}

# Allowed values for validation
_VALID_RISK_PROFILES:  frozenset = frozenset({"conservative", "moderate", "aggressive"})
_VALID_TIME_HORIZONS:  frozenset = frozenset({"short", "medium", "long"})


# ---------------------------------------------------------------------------
# Preferences CRUD
# ---------------------------------------------------------------------------

def save_preferences(
    db: Session,
    user_id: str,
    prefs: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Insert or replace user preferences (upsert).

    If a record already exists for user_id, it is completely replaced
    with the new values. Missing fields default to DEFAULT_PREFERENCES.

    Args:
        db (Session): Active SQLAlchemy session.
        user_id (str): Caller-supplied user identifier.
        prefs (dict): New preferences. Allowed keys:
            risk_profile, preferred_metrics, preferred_sectors, time_horizon

    Returns:
        dict: Saved preferences including last_updated timestamp.
    """
    user_id = _sanitize_user_id(user_id)
    validated = _validate_prefs(prefs)

    existing = db.get(UserPreferences, user_id)
    if existing:
        # Full replace
        existing.risk_profile      = validated["risk_profile"]
        existing.preferred_metrics = validated["preferred_metrics"]
        existing.preferred_sectors = validated["preferred_sectors"]
        existing.time_horizon      = validated["time_horizon"]
        existing.last_updated      = datetime.now(timezone.utc)
        record = existing
    else:
        record = UserPreferences(
            user_id           = user_id,
            risk_profile      = validated["risk_profile"],
            preferred_metrics = validated["preferred_metrics"],
            preferred_sectors = validated["preferred_sectors"],
            time_horizon      = validated["time_horizon"],
            last_updated      = datetime.now(timezone.utc),
        )
        db.add(record)

    db.commit()
    db.refresh(record)
    logger.info("[crud] Preferences saved for user_id=%s", user_id)
    return record.to_dict()


def get_preferences(
    db: Session,
    user_id: str,
) -> Dict[str, Any]:
    """
    Retrieve user preferences. Returns defaults if no record exists.

    Args:
        db (Session): Active SQLAlchemy session.
        user_id (str): User identifier.

    Returns:
        dict: User preferences (with defaults filled in).
    """
    user_id = _sanitize_user_id(user_id)
    record  = db.get(UserPreferences, user_id)

    if record is None:
        logger.info("[crud] No preferences found for %s — returning defaults", user_id)
        return {"user_id": user_id, **DEFAULT_PREFERENCES, "last_updated": None}

    return record.to_dict()


def update_preferences(
    db: Session,
    user_id: str,
    prefs: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Partially update user preferences. Only provided fields are changed.

    Args:
        db (Session): Active SQLAlchemy session.
        user_id (str): User identifier.
        prefs (dict): Fields to update (partial dict is fine).

    Returns:
        dict: Updated preferences.
    """
    user_id = _sanitize_user_id(user_id)
    record  = db.get(UserPreferences, user_id)

    if record is None:
        # Create with provided fields merged into defaults
        return save_preferences(db, user_id, {**DEFAULT_PREFERENCES, **prefs})

    if "risk_profile" in prefs:
        rp = prefs["risk_profile"]
        if rp in _VALID_RISK_PROFILES:
            record.risk_profile = rp
    if "preferred_metrics" in prefs and isinstance(prefs["preferred_metrics"], list):
        record.preferred_metrics = prefs["preferred_metrics"]
    if "preferred_sectors" in prefs and isinstance(prefs["preferred_sectors"], list):
        record.preferred_sectors = prefs["preferred_sectors"]
    if "time_horizon" in prefs:
        th = prefs["time_horizon"]
        if th in _VALID_TIME_HORIZONS:
            record.time_horizon = th

    record.last_updated = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    logger.info("[crud] Preferences updated for user_id=%s", user_id)
    return record.to_dict()


def delete_preferences(db: Session, user_id: str) -> bool:
    """
    Delete a user's preferences record.

    Returns:
        bool: True if deleted, False if record did not exist.
    """
    user_id = _sanitize_user_id(user_id)
    record  = db.get(UserPreferences, user_id)
    if record:
        db.delete(record)
        db.commit()
        return True
    return False


# ---------------------------------------------------------------------------
# Session Query History CRUD
# ---------------------------------------------------------------------------

def store_query(
    db: Session,
    user_id: str,
    query: str,
    ticker: Optional[str] = None,
    intent: Optional[str] = None,
    max_history: int = 10,
) -> None:
    """
    Persist a user query to session history.

    Keeps only the most recent `max_history` entries per user to
    prevent unbounded growth.

    Args:
        db (Session): Active SQLAlchemy session.
        user_id (str): User identifier.
        query (str): Raw query string.
        ticker (str | None): Extracted ticker.
        intent (str | None): Detected intent.
        max_history (int): Maximum number of entries to retain.
    """
    user_id = _sanitize_user_id(user_id)
    entry = SessionQuery(
        user_id    = user_id,
        query      = query[:500],   # cap length
        ticker     = (ticker or "")[:16],
        intent     = (intent or "")[:32],
    )
    db.add(entry)
    db.commit()

    # Prune old entries beyond max_history
    all_entries = (
        db.query(SessionQuery)
        .filter(SessionQuery.user_id == user_id)
        .order_by(SessionQuery.created_at.desc())
        .all()
    )
    if len(all_entries) > max_history:
        for old in all_entries[max_history:]:
            db.delete(old)
        db.commit()


def get_last_query(
    db: Session,
    user_id: str,
) -> Optional[str]:
    """
    Retrieve the most recent query string for a user.

    Args:
        db (Session): Active SQLAlchemy session.
        user_id (str): User identifier.

    Returns:
        str | None: Most recent query or None if no history.
    """
    user_id = _sanitize_user_id(user_id)
    entry = (
        db.query(SessionQuery)
        .filter(SessionQuery.user_id == user_id)
        .order_by(SessionQuery.created_at.desc())
        .first()
    )
    return entry.query if entry else None


def get_query_history(
    db: Session,
    user_id: str,
    limit: int = 5,
) -> list:
    """
    Retrieve recent query history for a user.

    Returns:
        list[dict]: Most recent `limit` session query records.
    """
    user_id = _sanitize_user_id(user_id)
    entries = (
        db.query(SessionQuery)
        .filter(SessionQuery.user_id == user_id)
        .order_by(SessionQuery.created_at.desc())
        .limit(limit)
        .all()
    )
    return [e.to_dict() for e in entries]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sanitize_user_id(user_id: str) -> str:
    """Strip whitespace and truncate to 64 chars."""
    return (user_id or "default").strip()[:64]


def _validate_prefs(prefs: Dict[str, Any]) -> Dict[str, Any]:
    """Merge provided prefs with defaults, applying field-level validation."""
    merged = {**DEFAULT_PREFERENCES, **prefs}

    if merged["risk_profile"] not in _VALID_RISK_PROFILES:
        merged["risk_profile"] = DEFAULT_PREFERENCES["risk_profile"]
    if merged["time_horizon"] not in _VALID_TIME_HORIZONS:
        merged["time_horizon"] = DEFAULT_PREFERENCES["time_horizon"]
    if not isinstance(merged["preferred_metrics"], list):
        merged["preferred_metrics"] = []
    if not isinstance(merged["preferred_sectors"], list):
        merged["preferred_sectors"] = []

    return merged
