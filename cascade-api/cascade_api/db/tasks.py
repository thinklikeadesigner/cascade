"""CRUD helpers for the tasks table."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from supabase import Client as SupabaseClient

log = structlog.get_logger()


async def create_task(
    supabase: SupabaseClient,
    tenant_id: str,
    title: str,
    week_start: str,
    scheduled_day: str | None = None,
    category: str = "core",
    goal_id: str | None = None,
    estimated_minutes: int | None = None,
) -> dict:
    """Insert a new task."""
    row: dict = {
        "tenant_id": tenant_id,
        "title": title,
        "week_start": week_start,
        "category": category,
    }
    if scheduled_day is not None:
        row["scheduled_day"] = scheduled_day
    if goal_id is not None:
        row["goal_id"] = goal_id
    if estimated_minutes is not None:
        row["estimated_minutes"] = estimated_minutes

    result = supabase.table("tasks").insert(row).execute()
    log.info("task.created", tenant_id=tenant_id, title=title, category=category)
    return result.data[0]


async def get_week_tasks(
    supabase: SupabaseClient,
    tenant_id: str,
    week_start: str,
) -> list[dict]:
    """Return all tasks for a given week."""
    result = (
        supabase.table("tasks")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("week_start", week_start)
        .order("sort_order")
        .execute()
    )
    return result.data


async def complete_task(
    supabase: SupabaseClient,
    task_id: str,
) -> dict:
    """Mark a task as completed with a timestamp."""
    result = (
        supabase.table("tasks")
        .update({
            "completed": True,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", task_id)
        .execute()
    )
    log.info("task.completed", task_id=task_id)
    return result.data[0]
