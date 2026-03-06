"""In-memory store — dict-backed, for testing and as protocol reference implementation."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone

from cascade_api.memory.errors import (
    ConcurrencyError,
    MemoryNotFoundError,
    TenantIsolationError,
)
from cascade_api.memory.models import MemoryLink, MemoryRecord, SearchResult


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


class InMemoryStore:
    def __init__(self):
        self._core: dict[str, tuple[str, int]] = {}  # tenant_id -> (content, version)
        self._memories: dict[str, MemoryRecord] = {}  # memory_id -> record
        self._tenant_memories: dict[str, list[str]] = {}  # tenant_id -> [memory_ids]
        self._links: list[MemoryLink] = []
        self._embedding_dims: int | None = None

    # ── Core memory ──────────────────────────────────────

    async def get_core(self, tenant_id: str) -> tuple[str, int]:
        return self._core.get(tenant_id, ("", 0))

    async def upsert_core(self, tenant_id: str, content: str, expected_version: int) -> int:
        _, current_version = self._core.get(tenant_id, ("", 0))
        if current_version != expected_version:
            raise ConcurrencyError(f"Expected version {expected_version}, got {current_version}")
        new_version = current_version + 1
        self._core[tenant_id] = (content, new_version)
        return new_version

    # ── Archival memory ──────────────────────────────────

    async def save(self, tenant_id: str, memory: MemoryRecord) -> str:
        mid = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        record = MemoryRecord(
            id=mid,
            content=memory.content,
            memory_type=memory.memory_type,
            tags=list(memory.tags),
            confidence=memory.confidence,
            decay_score=memory.decay_score,
            status=memory.status,
            embedding=list(memory.embedding) if memory.embedding else None,
            superseded_by=memory.superseded_by,
            source_id=memory.source_id,
            created_at=now,
            last_accessed_at=now,
            last_confirmed_at=now,
        )
        self._memories[mid] = record
        self._tenant_memories.setdefault(tenant_id, []).append(mid)
        return mid

    async def save_batch(self, tenant_id: str, memories: list[MemoryRecord]) -> list[str]:
        return [await self.save(tenant_id, m) for m in memories]

    async def get(self, tenant_id: str, memory_id: str) -> MemoryRecord:
        if memory_id not in self._memories:
            raise MemoryNotFoundError(f"Memory {memory_id} not found")
        if memory_id not in self._tenant_memories.get(tenant_id, []):
            raise MemoryNotFoundError(f"Memory {memory_id} not found for tenant {tenant_id}")
        return self._memories[memory_id]

    async def list(
        self, tenant_id: str, status: str = "active", limit: int = 50
    ) -> list[MemoryRecord]:
        ids = self._tenant_memories.get(tenant_id, [])
        results = [self._memories[mid] for mid in ids if self._memories[mid].status == status]
        results.sort(key=lambda m: m.created_at or datetime.min, reverse=True)
        return results[:limit]

    async def update(
        self,
        tenant_id: str,
        memory_id: str,
        content: str | None = None,
        status: str | None = None,
        embedding: list[float] | None = None,
        superseded_by: str | None = None,
    ) -> None:
        m = await self.get(tenant_id, memory_id)
        if content is not None:
            m.content = content
        if status is not None:
            m.status = status
        if embedding is not None:
            m.embedding = embedding
        if superseded_by is not None:
            m.superseded_by = superseded_by

    async def search(
        self,
        tenant_id: str,
        embedding: list[float],
        count: int = 5,
        threshold: float = 0.5,
    ) -> list[SearchResult]:
        ids = self._tenant_memories.get(tenant_id, [])
        results = []
        for mid in ids:
            m = self._memories[mid]
            if m.status != "active" or m.embedding is None:
                continue
            sim = _cosine_similarity(embedding, m.embedding)
            if sim < threshold:
                continue
            rank = sim * (0.3 + 0.7 * m.decay_score) * m.confidence
            results.append(SearchResult(memory=m, similarity=sim, rank_score=rank))
        results.sort(key=lambda r: r.rank_score, reverse=True)
        return results[:count]

    async def delete(self, tenant_id: str, memory_id: str) -> None:
        await self.get(tenant_id, memory_id)  # validates existence + tenant
        del self._memories[memory_id]
        self._tenant_memories[tenant_id].remove(memory_id)
        self._links = [
            link
            for link in self._links
            if link.source_id != memory_id and link.target_id != memory_id
        ]

    async def delete_all(self, tenant_id: str) -> int:
        ids = self._tenant_memories.get(tenant_id, [])
        count = len(ids)
        for mid in list(ids):
            if mid in self._memories:
                del self._memories[mid]
        self._links = [
            link for link in self._links if link.source_id not in ids and link.target_id not in ids
        ]
        self._tenant_memories[tenant_id] = []
        return count

    # ── Links ────────────────────────────────────────────

    async def add_link(
        self, tenant_id: str, source_id: str, target_id: str, link_type: str
    ) -> None:
        t1_ids = set(self._tenant_memories.get(tenant_id, []))
        if source_id not in t1_ids or target_id not in t1_ids:
            raise TenantIsolationError("Cannot link memories from different tenants")
        link = MemoryLink(
            id=str(uuid.uuid4()),
            source_id=source_id,
            target_id=target_id,
            link_type=link_type,
        )
        self._links.append(link)

    async def get_links(self, tenant_id: str, memory_id: str) -> list[MemoryLink]:
        t_ids = set(self._tenant_memories.get(tenant_id, []))
        return [
            link
            for link in self._links
            if (link.source_id == memory_id or link.target_id == memory_id)
            and link.source_id in t_ids
            and link.target_id in t_ids
        ]

    # ── Decay ────────────────────────────────────────────

    async def update_decay_scores(self, decay_rate: float = 0.95) -> int:
        now = datetime.now(timezone.utc)
        count = 0
        for m in self._memories.values():
            if m.status != "active" or m.last_accessed_at is None:
                continue
            days = max((now - m.last_accessed_at).total_seconds() / 86400, 0)
            new_score = round(decay_rate**days, 4)
            if abs(m.decay_score - new_score) > 0.01:
                m.decay_score = new_score
                count += 1
        return count

    async def touch_accessed(self, tenant_id: str, memory_ids: list[str]) -> None:
        now = datetime.now(timezone.utc)
        t_ids = set(self._tenant_memories.get(tenant_id, []))
        for mid in memory_ids:
            if mid in t_ids and mid in self._memories:
                self._memories[mid].last_accessed_at = now

    # ── Setup ────────────────────────────────────────────

    async def initialize(self, embedding_dimensions: int) -> None:
        self._embedding_dims = embedding_dimensions
