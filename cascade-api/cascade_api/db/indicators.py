"""CRUD helpers for the leading_indicators table."""

from __future__ import annotations

import structlog
from supabase import Client as SupabaseClient

from cascade_api.steer.skill_tracker import update_skill

log = structlog.get_logger()


async def create_indicator(
    supabase: SupabaseClient,
    tenant_id: str,
    goal_id: str,
    title: str,
    target_value: int,
    unit: str | None = None,
    skill_name: str | None = None,
    due_date: str | None = None,
) -> dict:
    """Insert a new leading indicator."""
    row: dict = {
        "tenant_id": tenant_id,
        "goal_id": goal_id,
        "title": title,
        "target_value": target_value,
    }
    if unit is not None:
        row["unit"] = unit
    if skill_name is not None:
        row["skill_name"] = skill_name
    if due_date is not None:
        row["due_date"] = due_date

    result = supabase.table("leading_indicators").insert(row).execute()
    log.info("indicator.created", tenant_id=tenant_id, title=title)
    return result.data[0]


async def get_indicators(
    supabase: SupabaseClient,
    tenant_id: str,
    goal_id: str,
) -> list[dict]:
    """Return all indicators for a goal."""
    result = (
        supabase.table("leading_indicators")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("goal_id", goal_id)
        .order("created_at")
        .execute()
    )
    return result.data


async def update_indicator(
    supabase: SupabaseClient,
    indicator_id: str,
    current_value: int,
) -> dict:
    """Update the current_value of an indicator."""
    result = (
        supabase.table("leading_indicators")
        .update({"current_value": current_value})
        .eq("id", indicator_id)
        .execute()
    )
    log.info("indicator.updated", id=indicator_id, current_value=current_value)
    return result.data[0]


async def complete_indicator(
    supabase: SupabaseClient,
    indicator_id: str,
) -> dict:
    """Mark an indicator complete and bump linked skill proficiency."""
    result = (
        supabase.table("leading_indicators")
        .update({"completed": True})
        .eq("id", indicator_id)
        .execute()
    )
    indicator = result.data[0]
    log.info("indicator.completed", id=indicator_id)

    # If linked to a skill, bump proficiency by 0.1 (capped at 1.0)
    if indicator.get("skill_name") and indicator.get("tenant_id"):
        # Get current proficiency
        user_result = (
            supabase.table("user_skills")
            .select("proficiency")
            .eq("tenant_id", indicator["tenant_id"])
            .eq("skill_name", indicator["skill_name"])
            .execute()
        )

        current = float(user_result.data[0]["proficiency"]) if user_result.data else 0.0
        new_proficiency = min(1.0, current + 0.1)

        await update_skill(
            supabase,
            tenant_id=indicator["tenant_id"],
            skill_name=indicator["skill_name"],
            proficiency=new_proficiency,
        )
        log.info(
            "indicator.skill_bumped",
            skill=indicator["skill_name"],
            old=current,
            new=new_proficiency,
        )

    return indicator


async def get_deficit(
    supabase: SupabaseClient,
    tenant_id: str,
    goal_id: str,
) -> list[dict]:
    """Return indicators sorted by deficit (target - current), descending."""
    result = (
        supabase.table("leading_indicators")
        .select("id, title, target_value, current_value, unit, skill_name, due_date")
        .eq("tenant_id", tenant_id)
        .eq("goal_id", goal_id)
        .eq("completed", False)
        .execute()
    )

    items: list[dict] = []
    for row in result.data:
        deficit = row["target_value"] - (row["current_value"] or 0)
        items.append(
            {
                "id": row["id"],
                "title": row["title"],
                "target_value": row["target_value"],
                "current_value": row["current_value"] or 0,
                "deficit": deficit,
                "unit": row.get("unit"),
                "skill_name": row.get("skill_name"),
            }
        )

    items.sort(key=lambda i: i["deficit"], reverse=True)
    return items
