"""CRUD helpers for the tracker_entries table."""

from __future__ import annotations

from datetime import date, timedelta

import structlog
from supabase import Client as SupabaseClient

log = structlog.get_logger()


async def log_entry(
    supabase: SupabaseClient,
    tenant_id: str,
    date_str: str,
    data: dict,
) -> dict:
    """Upsert a tracker_entries row (merge if same tenant+date exists)."""
    existing = (
        supabase.table("tracker_entries")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("date", date_str)
        .execute()
    )

    if existing.data:
        # Merge: keep existing values, overwrite with new non-None values
        row_id = existing.data[0]["id"]
        merged = {k: v for k, v in data.items() if v is not None}
        result = (
            supabase.table("tracker_entries")
            .update(merged)
            .eq("id", row_id)
            .execute()
        )
        log.info("tracker_entry.updated", tenant_id=tenant_id, date=date_str)
    else:
        row = {"tenant_id": tenant_id, "date": date_str, **data}
        result = supabase.table("tracker_entries").insert(row).execute()
        log.info("tracker_entry.created", tenant_id=tenant_id, date=date_str)

    return result.data[0]


async def get_entries(
    supabase: SupabaseClient,
    tenant_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict]:
    """Return tracker entries filtered by optional date range."""
    query = (
        supabase.table("tracker_entries")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("date", desc=True)
    )

    if start_date:
        query = query.gte("date", start_date)
    if end_date:
        query = query.lte("date", end_date)

    result = query.execute()
    return result.data


async def get_weekly_velocity(
    supabase: SupabaseClient,
    tenant_id: str,
    weeks: int = 4,
) -> list[dict]:
    """Call the get_weekly_velocity() Postgres function."""
    result = supabase.rpc(
        "get_weekly_velocity",
        {"p_tenant_id": tenant_id, "p_weeks": weeks},
    ).execute()
    return result.data
