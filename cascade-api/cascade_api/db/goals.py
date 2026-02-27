"""CRUD helpers for the goals table."""

from __future__ import annotations

import structlog
from supabase import Client as SupabaseClient

log = structlog.get_logger()


async def create_goal(
    supabase: SupabaseClient,
    tenant_id: str,
    title: str,
    description: str | None = None,
    success_criteria: str | None = None,
    target_date: str | None = None,
) -> dict:
    """Insert a new goal."""
    row: dict = {"tenant_id": tenant_id, "title": title}
    if description is not None:
        row["description"] = description
    if success_criteria is not None:
        row["success_criteria"] = success_criteria
    if target_date is not None:
        row["target_date"] = target_date

    result = supabase.table("goals").insert(row).execute()
    log.info("goal.created", tenant_id=tenant_id, title=title)
    return result.data[0]


async def get_goals(
    supabase: SupabaseClient,
    tenant_id: str,
    status: str = "active",
) -> list[dict]:
    """Return goals filtered by status."""
    result = (
        supabase.table("goals")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("status", status)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


async def update_goal(
    supabase: SupabaseClient,
    goal_id: str,
    **updates,
) -> dict:
    """Update a goal by ID."""
    result = (
        supabase.table("goals")
        .update(updates)
        .eq("id", goal_id)
        .execute()
    )
    log.info("goal.updated", goal_id=goal_id, fields=list(updates.keys()))
    return result.data[0]
