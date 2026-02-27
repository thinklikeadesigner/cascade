"""Supabase Auth helpers for API endpoints."""

from __future__ import annotations

from fastapi import Header, HTTPException

from cascade_api.dependencies import get_supabase


async def get_current_user_id(authorization: str = Header(...)) -> str:
    """Extract user ID from Supabase JWT. Returns auth.users ID."""
    token = authorization.replace("Bearer ", "")
    supabase = get_supabase()
    try:
        user = supabase.auth.get_user(token)
        return user.user.id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
