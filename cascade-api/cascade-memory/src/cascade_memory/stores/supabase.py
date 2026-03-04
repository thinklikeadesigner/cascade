"""SupabaseStore — MemoryStore protocol implementation for Supabase + pgvector."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from cascade_memory.errors import (
    ConcurrencyError,
    MemoryNotFoundError,
    TenantIsolationError,
)
from cascade_memory.models import MemoryLink, MemoryRecord, SearchResult

log = logging.getLogger("cascade_memory.stores.supabase")


class SupabaseStore:
    """Supabase-backed memory store using pgvector for semantic search.

    Requires: pip install cascade-memory[supabase]
    """

    def __init__(self, client):
        """Initialize with a Supabase client instance.

        Args:
            client: A supabase.Client (sync) instance. The store wraps
                    its synchronous methods — Supabase Python SDK v2 is sync.
        """
        self._sb = client

    # ── Core memory ──────────────────────────────────────

    async def get_core(self, tenant_id: str) -> tuple[str, int]:
        result = (
            self._sb.table("core_memories")
            .select("content, version")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        if result.data:
            return result.data[0]["content"], result.data[0]["version"]
        return "", 0

    async def upsert_core(self, tenant_id: str, content: str, expected_version: int) -> int:
        now = datetime.now(timezone.utc).isoformat()
        new_version = expected_version + 1

        if expected_version > 0:
            # Optimistic lock: only update if version matches
            result = (
                self._sb.table("core_memories")
                .update({
                    "content": content,
                    "version": new_version,
                    "updated_at": now,
                })
                .eq("tenant_id", tenant_id)
                .eq("version", expected_version)
                .execute()
            )
            if not result.data:
                raise ConcurrencyError(
                    "Core memory was modified by another process. "
                    "Re-read and retry."
                )
        else:
            # First write — upsert
            result = (
                self._sb.table("core_memories")
                .upsert(
                    {
                        "tenant_id": tenant_id,
                        "content": content,
                        "version": new_version,
                        "updated_at": now,
                    },
                    on_conflict="tenant_id",
                )
                .execute()
            )

        log.info("core_memory.upserted tenant_id=%s length=%d", tenant_id, len(content))
        return new_version

    # ── Archival memory ──────────────────────────────────

    async def save(self, tenant_id: str, memory: MemoryRecord) -> str:
        row = {
            "tenant_id": tenant_id,
            "content": memory.content,
            "memory_type": memory.memory_type,
            "tags": memory.tags,
            "confidence": memory.confidence,
            "status": memory.status,
        }
        if memory.embedding:
            row["embedding"] = memory.embedding
        if memory.source_id:
            row["source_id"] = memory.source_id

        result = self._sb.table("memories").insert(row).execute()
        log.info("memory.saved tenant_id=%s type=%s", tenant_id, memory.memory_type)
        return result.data[0]["id"]

    async def save_batch(self, tenant_id: str, memories: list[MemoryRecord]) -> list[str]:
        return [await self.save(tenant_id, m) for m in memories]

    async def get(self, tenant_id: str, memory_id: str) -> MemoryRecord:
        result = (
            self._sb.table("memories")
            .select("*")
            .eq("id", memory_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        if not result.data:
            raise MemoryNotFoundError(f"Memory {memory_id} not found for tenant {tenant_id}")
        return self._row_to_record(result.data[0])

    async def list(self, tenant_id: str, status: str = "active", limit: int = 50) -> list[MemoryRecord]:
        result = (
            self._sb.table("memories")
            .select("*")
            .eq("tenant_id", tenant_id)
            .eq("status", status)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [self._row_to_record(r) for r in result.data]

    async def update(
        self, tenant_id: str, memory_id: str,
        content: str | None = None, status: str | None = None,
        embedding: list[float] | None = None, superseded_by: str | None = None,
    ) -> None:
        updates = {}
        if content is not None:
            updates["content"] = content
        if status is not None:
            updates["status"] = status
        if embedding is not None:
            updates["embedding"] = embedding
        if superseded_by is not None:
            updates["superseded_by"] = superseded_by

        if not updates:
            return

        result = (
            self._sb.table("memories")
            .update(updates)
            .eq("id", memory_id)
            .eq("tenant_id", tenant_id)
            .execute()
        )
        if not result.data:
            raise MemoryNotFoundError(f"Memory {memory_id} not found")

    async def search(
        self, tenant_id: str, embedding: list[float],
        count: int = 5, threshold: float = 0.5,
    ) -> list[SearchResult]:
        result = self._sb.rpc(
            "match_memories",
            {
                "query_embedding": embedding,
                "match_tenant_id": tenant_id,
                "match_count": count,
                "match_threshold": threshold,
            },
        ).execute()

        return [
            SearchResult(
                memory=MemoryRecord(
                    id=r["id"],
                    content=r["content"],
                    memory_type=r["memory_type"],
                    tags=r.get("tags", []),
                    confidence=r.get("confidence", 1.0),
                    decay_score=r.get("decay_score", 1.0),
                ),
                similarity=r["similarity"],
                rank_score=r["similarity"] * (0.3 + 0.7 * r.get("decay_score", 1.0)) * r.get("confidence", 1.0),
            )
            for r in result.data
        ]

    async def delete(self, tenant_id: str, memory_id: str) -> None:
        # Also clean up links
        self._sb.table("memory_links").delete().eq(
            "source_memory_id", memory_id
        ).execute()
        self._sb.table("memory_links").delete().eq(
            "target_memory_id", memory_id
        ).execute()
        self._sb.table("memories").delete().eq(
            "id", memory_id
        ).eq("tenant_id", tenant_id).execute()

    async def delete_all(self, tenant_id: str) -> int:
        # Get all memory IDs first for link cleanup
        existing = (
            self._sb.table("memories")
            .select("id")
            .eq("tenant_id", tenant_id)
            .execute()
        )
        count = len(existing.data)
        if count > 0:
            ids = [r["id"] for r in existing.data]
            for mid in ids:
                self._sb.table("memory_links").delete().eq("source_memory_id", mid).execute()
                self._sb.table("memory_links").delete().eq("target_memory_id", mid).execute()
            self._sb.table("memories").delete().eq("tenant_id", tenant_id).execute()
        return count

    # ── Links ────────────────────────────────────────────

    async def add_link(self, tenant_id: str, source_id: str, target_id: str, link_type: str) -> None:
        # Verify both memories belong to this tenant
        source = (
            self._sb.table("memories").select("id")
            .eq("id", source_id).eq("tenant_id", tenant_id).execute()
        )
        target = (
            self._sb.table("memories").select("id")
            .eq("id", target_id).eq("tenant_id", tenant_id).execute()
        )
        if not source.data or not target.data:
            raise TenantIsolationError(
                "Cannot link memories across tenants or link non-existent memories"
            )

        self._sb.table("memory_links").insert({
            "tenant_id": tenant_id,
            "source_memory_id": source_id,
            "target_memory_id": target_id,
            "link_type": link_type,
        }).execute()

    async def get_links(self, tenant_id: str, memory_id: str) -> list[MemoryLink]:
        # Get links where this memory is source or target
        source_links = (
            self._sb.table("memory_links").select("*")
            .eq("tenant_id", tenant_id)
            .eq("source_memory_id", memory_id)
            .execute()
        )
        target_links = (
            self._sb.table("memory_links").select("*")
            .eq("tenant_id", tenant_id)
            .eq("target_memory_id", memory_id)
            .execute()
        )
        all_links = source_links.data + target_links.data
        return [
            MemoryLink(
                id=r["id"],
                source_id=r["source_memory_id"],
                target_id=r["target_memory_id"],
                link_type=r["link_type"],
            )
            for r in all_links
        ]

    # ── Decay ────────────────────────────────────────────

    async def update_decay_scores(self, decay_rate: float = 0.95) -> int:
        result = self._sb.rpc(
            "update_memory_decay_scores",
            {"p_decay_rate": decay_rate},
        ).execute()
        return result.data if isinstance(result.data, int) else 0

    async def touch_accessed(self, tenant_id: str, memory_ids: list[str]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        for mid in memory_ids:
            self._sb.table("memories").update(
                {"last_accessed_at": now}
            ).eq("id", mid).eq("tenant_id", tenant_id).execute()

    # ── Setup ────────────────────────────────────────────

    async def initialize(self, embedding_dimensions: int) -> None:
        """No-op for SupabaseStore — run the SQL migration template manually."""

    # ── Helpers ──────────────────────────────────────────

    @staticmethod
    def _row_to_record(row: dict) -> MemoryRecord:
        def _parse_dt(val):
            if val is None:
                return None
            if isinstance(val, datetime):
                return val
            try:
                return datetime.fromisoformat(val.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return None

        return MemoryRecord(
            id=row["id"],
            content=row["content"],
            memory_type=row.get("memory_type", "fact"),
            tags=row.get("tags", []),
            confidence=row.get("confidence", 1.0),
            decay_score=row.get("decay_score", 1.0),
            status=row.get("status", "active"),
            embedding=row.get("embedding"),
            superseded_by=row.get("superseded_by"),
            source_id=row.get("source_id"),
            created_at=_parse_dt(row.get("created_at")),
            last_accessed_at=_parse_dt(row.get("last_accessed_at")),
            last_confirmed_at=_parse_dt(row.get("last_confirmed_at")),
        )
