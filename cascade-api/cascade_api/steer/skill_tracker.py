"""Track user skill proficiency and compute gaps against expert graph."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from supabase import Client as SupabaseClient

log = structlog.get_logger()


async def update_skill(
    supabase: SupabaseClient,
    tenant_id: str,
    skill_name: str,
    proficiency: float,
) -> dict:
    """Upsert a user_skills row — update proficiency + last_practiced_at."""
    now = datetime.now(timezone.utc).isoformat()

    existing = (
        supabase.table("user_skills")
        .select("id")
        .eq("tenant_id", tenant_id)
        .eq("skill_name", skill_name)
        .execute()
    )

    if existing.data:
        result = (
            supabase.table("user_skills")
            .update({"proficiency": proficiency, "last_practiced_at": now})
            .eq("id", existing.data[0]["id"])
            .execute()
        )
        log.info("skill.updated", skill_name=skill_name, proficiency=proficiency)
    else:
        result = (
            supabase.table("user_skills")
            .insert(
                {
                    "tenant_id": tenant_id,
                    "skill_name": skill_name,
                    "proficiency": proficiency,
                    "last_practiced_at": now,
                }
            )
            .execute()
        )
        log.info("skill.created", skill_name=skill_name, proficiency=proficiency)

    return result.data[0]


async def get_skill_gaps(
    supabase: SupabaseClient,
    tenant_id: str,
    goal_id: str,
) -> list[dict]:
    """Return skills sorted by gap (expert weight - user proficiency), descending.

    Joins expert_skills for the goal against user_skills for the tenant.
    Skills the user hasn't practiced yet default to 0 proficiency.
    """
    expert_result = (
        supabase.table("expert_skills")
        .select("skill_name, weight, category")
        .eq("goal_id", goal_id)
        .execute()
    )

    user_result = (
        supabase.table("user_skills")
        .select("skill_name, proficiency")
        .eq("tenant_id", tenant_id)
        .execute()
    )

    user_map: dict[str, float] = {
        row["skill_name"]: float(row["proficiency"]) for row in user_result.data
    }

    gaps: list[dict] = []
    for expert in expert_result.data:
        name = expert["skill_name"]
        weight = float(expert["weight"])
        current = user_map.get(name, 0.0)
        gaps.append(
            {
                "skill_name": name,
                "required_weight": weight,
                "current_proficiency": current,
                "gap": round(weight - current, 4),
            }
        )

    gaps.sort(key=lambda g: g["gap"], reverse=True)
    return gaps


async def apply_decay(
    supabase: SupabaseClient,
    tenant_id: str,
    decay_rate: float = 0.02,
) -> int:
    """Reduce proficiency based on days since last_practiced_at.

    Formula: new = max(0, proficiency - decay_rate * days_since_practice)
    Returns count of skills updated.
    """
    result = (
        supabase.table("user_skills")
        .select("id, proficiency, last_practiced_at")
        .eq("tenant_id", tenant_id)
        .execute()
    )

    now = datetime.now(timezone.utc)
    updated = 0

    for row in result.data:
        if not row.get("last_practiced_at"):
            continue

        last_practiced = datetime.fromisoformat(row["last_practiced_at"])
        days_since = (now - last_practiced).days
        if days_since <= 0:
            continue

        current = float(row["proficiency"])
        new_proficiency = max(0.0, current - decay_rate * days_since)
        if new_proficiency == current:
            continue

        supabase.table("user_skills").update(
            {"proficiency": round(new_proficiency, 4)}
        ).eq("id", row["id"]).execute()
        updated += 1

    log.info("skills.decay_applied", tenant_id=tenant_id, updated=updated)
    return updated
