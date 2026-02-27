"""CRUD helpers for the adaptations table."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from supabase import Client as SupabaseClient

log = structlog.get_logger()


async def create_adaptation(
    supabase: SupabaseClient,
    tenant_id: str,
    pattern_type: str,
    description: str,
) -> dict:
    """Insert a new adaptation pattern."""
    row = {
        "tenant_id": tenant_id,
        "pattern_type": pattern_type,
        "description": description,
    }
    result = supabase.table("adaptations").insert(row).execute()
    log.info(
        "adaptation.created",
        tenant_id=tenant_id,
        pattern_type=pattern_type,
    )
    return result.data[0]


async def get_active(
    supabase: SupabaseClient,
    tenant_id: str,
) -> list[dict]:
    """Return adaptations where active=True."""
    result = (
        supabase.table("adaptations")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("active", True)
        .order("detected_at", desc=True)
        .execute()
    )
    return result.data


async def approve(
    supabase: SupabaseClient,
    adaptation_id: str,
) -> dict:
    """Mark an adaptation as approved."""
    result = (
        supabase.table("adaptations")
        .update({
            "approved": True,
            "approved_at": datetime.now(timezone.utc).isoformat(),
        })
        .eq("id", adaptation_id)
        .execute()
    )
    log.info("adaptation.approved", adaptation_id=adaptation_id)
    return result.data[0]
