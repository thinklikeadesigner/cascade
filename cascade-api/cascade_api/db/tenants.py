"""CRUD helpers for the tenants table."""

from __future__ import annotations

import structlog
from supabase import Client as SupabaseClient

log = structlog.get_logger()


async def get_tenant(
    supabase: SupabaseClient,
    tenant_id: str,
) -> dict | None:
    """Return a single tenant by ID, or None if not found."""
    result = (
        supabase.table("tenants")
        .select("*")
        .eq("id", tenant_id)
        .execute()
    )
    return result.data[0] if result.data else None


async def update_tenant(
    supabase: SupabaseClient,
    tenant_id: str,
    **updates,
) -> dict:
    """Update a tenant by ID."""
    result = (
        supabase.table("tenants")
        .update(updates)
        .eq("id", tenant_id)
        .execute()
    )
    log.info("tenant.updated", tenant_id=tenant_id, fields=list(updates.keys()))
    return result.data[0]
