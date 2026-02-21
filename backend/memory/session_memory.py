"""
backend/memory/session_memory.py

Session-level memory handler for the AI Research Agent.

Provides a simple functional interface over the CRUD layer for
storing and retrieving query context. Handles DB session lifecycle
internally so callers don't need to manage sessions directly.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def store_last_query(
    user_id: str,
    query: str,
    ticker: Optional[str] = None,
    intent: Optional[str] = None,
) -> None:
    """
    Persist the user's latest query to session history.

    Non-blocking — failures are logged but do not raise exceptions.

    Args:
        user_id (str): User identifier.
        query (str): Raw query string.
        ticker (str | None): Extracted ticker symbol.
        intent (str | None): Detected intent type.
    """
    try:
        from backend.db.session import SessionLocal
        from backend.memory.crud import store_query
        with SessionLocal() as db:
            store_query(db, user_id=user_id, query=query, ticker=ticker, intent=intent)
        logger.debug("[session_memory] Stored query for user=%s", user_id)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("[session_memory] Failed to store query for %s: %s", user_id, exc)


def get_last_query(user_id: str) -> Optional[str]:
    """
    Retrieve the most recent query string for a user.

    Returns None if no history exists or on any error.

    Args:
        user_id (str): User identifier.

    Returns:
        str | None: Most recent query text.
    """
    try:
        from backend.db.session import SessionLocal
        from backend.memory.crud import get_last_query as _get
        with SessionLocal() as db:
            return _get(db, user_id=user_id)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("[session_memory] Failed to get query for %s: %s", user_id, exc)
        return None


def get_query_history(user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Retrieve recent query history for a user.

    Returns an empty list on any error.

    Args:
        user_id (str): User identifier.
        limit (int): Number of recent entries to return.

    Returns:
        list[dict]: Session query records.
    """
    try:
        from backend.db.session import SessionLocal
        from backend.memory.crud import get_query_history as _hist
        with SessionLocal() as db:
            return _hist(db, user_id=user_id, limit=limit)
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("[session_memory] Failed to get history for %s: %s", user_id, exc)
        return []
