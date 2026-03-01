"""Database operations for the memory system.

Two layers:
- Core memory: a single markdown document per user, always in context.
- Archival memory: structured fact notes with vector embeddings for search.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from supabase import Client as SupabaseClient

log = structlog.get_logger()


# ── Core Memory ──────────────────────────────────────────────────

async def get_core_memory(supabase: SupabaseClient, tenant_id: str) -> str:
    """Return the core memory markdown doc for a tenant, or empty string."""
    result = (
        supabase.table("core_memories")
        .select("content")
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if result.data:
        return result.data[0]["content"]
    return ""


async def get_core_memory_with_version(supabase: SupabaseClient, tenant_id: str) -> tuple[str, int]:
    """Return (content, version) for optimistic concurrency control."""
    result = (
        supabase.table("core_memories")
        .select("content, version")
        .eq("tenant_id", tenant_id)
        .execute()
    )
    if result.data:
        return result.data[0]["content"], result.data[0]["version"]
    return "", 0


async def upsert_core_memory(
    supabase: SupabaseClient,
    tenant_id: str,
    content: str,
    expected_version: int | None = None,
) -> dict:
    """Create or update the core memory doc. Returns the row.

    Uses optimistic concurrency control via the version column.
    If expected_version is provided and doesn't match, the update
    is rejected to prevent lost writes from concurrent modifications.
    """
    if expected_version is not None and expected_version > 0:
        # Optimistic lock: only update if version matches
        result = (
            supabase.table("core_memories")
            .update({
                "content": content,
                "version": expected_version + 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("tenant_id", tenant_id)
            .eq("version", expected_version)
            .execute()
        )
        if not result.data:
            raise ValueError(
                "Core memory was modified by another process. "
                "Re-read with core_memory_read and retry."
            )
    else:
        # First write or no version check
        result = (
            supabase.table("core_memories")
            .upsert(
                {
                    "tenant_id": tenant_id,
                    "content": content,
                    "version": (expected_version or 0) + 1,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="tenant_id",
            )
            .execute()
        )

    log.info("core_memory.upserted", tenant_id=tenant_id, length=len(content))
    return result.data[0]


# ── Archival Memory ──────────────────────────────────────────────

async def save_memory(
    supabase: SupabaseClient,
    tenant_id: str,
    content: str,
    memory_type: str = "fact",
    tags: list[str] | None = None,
    confidence: float = 1.0,
    source_conversation_id: int | None = None,
    embedding: list[float] | None = None,
    status: str = "active",
) -> dict:
    """Insert a new archival memory note."""
    row = {
        "tenant_id": tenant_id,
        "content": content,
        "memory_type": memory_type,
        "tags": tags or [],
        "confidence": confidence,
        "status": status,
    }
    if source_conversation_id:
        row["source_conversation_id"] = source_conversation_id
    if embedding:
        row["embedding"] = embedding

    result = supabase.table("memories").insert(row).execute()
    log.info("memory.saved", tenant_id=tenant_id, type=memory_type, status=status)
    return result.data[0]


async def get_memories(
    supabase: SupabaseClient,
    tenant_id: str,
    status: str = "active",
    limit: int = 50,
) -> list[dict]:
    """Return memories for a tenant, filtered by status."""
    result = (
        supabase.table("memories")
        .select("*")
        .eq("tenant_id", tenant_id)
        .eq("status", status)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return result.data


async def update_memory_status(
    supabase: SupabaseClient,
    tenant_id: str,
    memory_id: str,
    status: str,
    superseded_by: str | None = None,
) -> dict:
    """Update a memory's status (archive, forget, etc.)."""
    updates: dict = {"status": status}
    if superseded_by:
        updates["superseded_by"] = superseded_by

    result = (
        supabase.table("memories")
        .update(updates)
        .eq("id", memory_id)
        .eq("tenant_id", tenant_id)
        .execute()
    )
    log.info("memory.status_updated", memory_id=memory_id, status=status)
    return result.data[0]


async def update_memory_accessed(
    supabase: SupabaseClient,
    tenant_id: str,
    memory_ids: list[str],
) -> None:
    """Touch last_accessed_at on retrieved memories (for decay scoring)."""
    now = datetime.now(timezone.utc).isoformat()
    for mid in memory_ids:
        supabase.table("memories").update(
            {"last_accessed_at": now}
        ).eq("id", mid).eq("tenant_id", tenant_id).execute()


async def add_memory_link(
    supabase: SupabaseClient,
    tenant_id: str,
    source_id: str,
    target_id: str,
    link_type: str,
) -> dict:
    """Create a Zettelkasten link between two memories.

    Validates both memories belong to the same tenant before inserting.
    """
    # Verify both memories belong to this tenant (defense-in-depth)
    source = supabase.table("memories").select("id").eq(
        "id", source_id
    ).eq("tenant_id", tenant_id).execute()
    target = supabase.table("memories").select("id").eq(
        "id", target_id
    ).eq("tenant_id", tenant_id).execute()

    if not source.data or not target.data:
        raise ValueError("Cannot link memories across tenants or link non-existent memories")

    result = (
        supabase.table("memory_links")
        .insert({
            "tenant_id": tenant_id,
            "source_memory_id": source_id,
            "target_memory_id": target_id,
            "link_type": link_type,
        })
        .execute()
    )
    return result.data[0]
