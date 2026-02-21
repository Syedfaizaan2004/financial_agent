"""
backend/api/routes/memory.py

Memory & Personalization API endpoints.

Provides simple REST endpoints for managing user preferences and
retrieving session history. No authentication required (hackathon mode).

Endpoints:
    POST   /memory/preferences             — save (upsert) preferences
    GET    /memory/preferences/{user_id}   — retrieve preferences
    PUT    /memory/preferences/{user_id}   — partial update
    DELETE /memory/preferences/{user_id}   — delete record
    GET    /memory/history/{user_id}       — recent query history
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.memory import crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/memory", tags=["Memory & Personalization"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class PreferencesIn(BaseModel):
    """Request body for saving or updating user preferences."""
    user_id:           str             = Field(..., min_length=1, max_length=64, examples=["user_001"])
    risk_profile:      Optional[str]   = Field("moderate", examples=["conservative"])
    preferred_metrics: Optional[List[str]] = Field(default_factory=list, examples=[["ROE", "FCF"]])
    preferred_sectors: Optional[List[str]] = Field(default_factory=list, examples=[["Technology"]])
    time_horizon:      Optional[str]   = Field("medium", examples=["long"])

    @field_validator("risk_profile")
    @classmethod
    def validate_risk(cls, v: Optional[str]) -> Optional[str]:
        allowed = {"conservative", "moderate", "aggressive"}
        if v and v.lower() not in allowed:
            raise ValueError(f"risk_profile must be one of {sorted(allowed)}")
        return v.lower() if v else v

    @field_validator("time_horizon")
    @classmethod
    def validate_horizon(cls, v: Optional[str]) -> Optional[str]:
        allowed = {"short", "medium", "long"}
        if v and v.lower() not in allowed:
            raise ValueError(f"time_horizon must be one of {sorted(allowed)}")
        return v.lower() if v else v


class PreferencesUpdateIn(BaseModel):
    """Partial update — all fields optional."""
    risk_profile:      Optional[str]       = None
    preferred_metrics: Optional[List[str]] = None
    preferred_sectors: Optional[List[str]] = None
    time_horizon:      Optional[str]       = None

    @field_validator("risk_profile")
    @classmethod
    def validate_risk(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() not in {"conservative", "moderate", "aggressive"}:
            raise ValueError("Invalid risk_profile value")
        return v.lower() if v else v

    @field_validator("time_horizon")
    @classmethod
    def validate_horizon(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.lower() not in {"short", "medium", "long"}:
            raise ValueError("Invalid time_horizon value")
        return v.lower() if v else v


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/preferences", summary="Save user preferences (upsert)")
def save_preferences(
    body: PreferencesIn,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Insert or replace user preferences.

    If a record already exists for `user_id`, it is completely replaced.
    Use PUT for partial updates.
    """
    result = crud.save_preferences(
        db,
        user_id = body.user_id,
        prefs   = body.model_dump(exclude={"user_id"}),
    )
    return {"status": "saved", "preferences": result}


@router.get("/preferences/{user_id}", summary="Get user preferences")
def get_preferences(
    user_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retrieve user preferences. Returns defaults if no record exists.
    """
    result = crud.get_preferences(db, user_id=user_id)
    return {"preferences": result}


@router.put("/preferences/{user_id}", summary="Partially update user preferences")
def update_preferences(
    user_id: str,
    body: PreferencesUpdateIn,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Partially update user preferences.

    Only fields included in the request body are changed.
    """
    update_data = {k: v for k, v in body.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update.")

    result = crud.update_preferences(db, user_id=user_id, prefs=update_data)
    return {"status": "updated", "preferences": result}


@router.delete("/preferences/{user_id}", summary="Delete user preferences")
def delete_preferences(
    user_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Delete a user's preference record. Returns 404 if not found.
    """
    deleted = crud.delete_preferences(db, user_id=user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"No preferences found for user_id='{user_id}'")
    return {"status": "deleted", "user_id": user_id}


@router.get("/history/{user_id}", summary="Get recent query history")
def get_history(
    user_id: str,
    limit: int = 5,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Retrieve recent query history for a user.

    Args:
        limit: Number of recent queries to return (max 20).
    """
    limit   = min(max(limit, 1), 20)
    history = crud.get_query_history(db, user_id=user_id, limit=limit)
    return {"user_id": user_id, "history": history, "count": len(history)}
