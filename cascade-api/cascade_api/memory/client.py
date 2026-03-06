"""MemoryClient — single entry point for cascade-memory."""

from __future__ import annotations

import logging

from cascade_api.memory.core import CoreMemory
from cascade_api.memory.errors import EmbeddingError
from cascade_api.memory.models import MemoryLink, MemoryRecord, SearchResult
from cascade_api.memory.protocols.embedder import Embedder
from cascade_api.memory.protocols.extractor import MemoryExtractor
from cascade_api.memory.protocols.store import MemoryStore

logger = logging.getLogger("cascade_memory")


class MemoryClient:
    def __init__(
        self,
        store: MemoryStore,
        embedder: Embedder,
        extractor: MemoryExtractor | None = None,
        core_memory_limit: int = 3000,
        decay_rate: float = 0.95,
        require_embedding: bool = False,
    ):
        self.store = store
        self.embedder = embedder
        self.extractor = extractor
        self.core = CoreMemory(store, core_memory_limit)
        self._decay_rate = decay_rate
        self._require_embedding = require_embedding

    def for_tenant(self, tenant_id: str) -> TenantScopedClient:
        return TenantScopedClient(self, tenant_id)

    async def initialize(self) -> None:
        await self.store.initialize(self.embedder.dimensions)

    async def save(
        self,
        tenant_id: str,
        content: str,
        *,
        memory_type: str = "fact",
        tags: list[str] | None = None,
        confidence: float = 1.0,
        source_id: str | None = None,
    ) -> str:
        embedding = None
        try:
            embedding = await self.embedder.embed(content)
        except Exception as e:
            if self._require_embedding:
                raise EmbeddingError(str(e)) from e
            logger.warning("Embedding failed, saving without: %s", e)

        record = MemoryRecord(
            id="",
            content=content,
            memory_type=memory_type,
            tags=tags or [],
            confidence=confidence,
            embedding=embedding,
            source_id=source_id,
        )
        return await self.store.save(tenant_id, record)

    async def recall(
        self,
        tenant_id: str,
        query: str,
        count: int = 5,
        threshold: float = 0.5,
    ) -> list[SearchResult]:
        embedding = await self.embedder.embed(query)
        results = await self.store.search(tenant_id, embedding, count, threshold)
        if results:
            ids = [r.memory.id for r in results]
            await self.store.touch_accessed(tenant_id, ids)
        return results

    async def update(
        self,
        tenant_id: str,
        memory_id: str,
        content: str,
    ) -> None:
        embedding = None
        try:
            embedding = await self.embedder.embed(content)
        except Exception as e:
            if self._require_embedding:
                raise EmbeddingError(str(e)) from e
            logger.warning("Embedding failed, updating without: %s", e)
        await self.store.update(tenant_id, memory_id, content=content, embedding=embedding)

    async def forget(self, tenant_id: str, memory_id: str) -> None:
        await self.store.update(tenant_id, memory_id, status="forgotten")

    async def delete(self, tenant_id: str, memory_id: str) -> None:
        await self.store.delete(tenant_id, memory_id)

    async def delete_all(self, tenant_id: str) -> int:
        return await self.store.delete_all(tenant_id)

    async def link(
        self,
        tenant_id: str,
        source_id: str,
        target_id: str,
        link_type: str,
    ) -> None:
        await self.store.add_link(tenant_id, source_id, target_id, link_type)

    async def get_related(self, tenant_id: str, memory_id: str) -> list[MemoryLink]:
        return await self.store.get_links(tenant_id, memory_id)

    async def run_decay(self) -> int:
        return await self.store.update_decay_scores(self._decay_rate)

    async def extract(
        self,
        tenant_id: str,
        conversation_text: str,
        source_id: str | None = None,
    ) -> list[str]:
        if not self.extractor:
            raise RuntimeError("No extractor configured")
        extracted = await self.extractor.extract(conversation_text)
        if not extracted:
            return []

        # Generate embeddings in batch
        texts = [e.content for e in extracted]
        try:
            embeddings = await self.embedder.embed_batch(texts)
        except Exception as e:
            if self._require_embedding:
                raise EmbeddingError(str(e)) from e
            logger.warning("Batch embedding failed: %s", e)
            embeddings = [None] * len(extracted)

        records = [
            MemoryRecord(
                id="",
                content=e.content,
                memory_type=e.memory_type,
                tags=e.tags,
                confidence=e.confidence,
                embedding=emb,
                source_id=source_id,
            )
            for e, emb in zip(extracted, embeddings)
        ]
        return await self.store.save_batch(tenant_id, records)


class TenantScopedClient:
    """Tenant-scoped wrapper — eliminates tenant_id from every call."""

    def __init__(self, client: MemoryClient, tenant_id: str):
        self._client = client
        self._tenant_id = tenant_id
        self.core = _ScopedCore(client.core, tenant_id)

    async def save(
        self,
        content: str,
        *,
        memory_type: str = "fact",
        tags: list[str] | None = None,
        confidence: float = 1.0,
        source_id: str | None = None,
    ) -> str:
        return await self._client.save(
            self._tenant_id,
            content,
            memory_type=memory_type,
            tags=tags,
            confidence=confidence,
            source_id=source_id,
        )

    async def recall(
        self, query: str, count: int = 5, threshold: float = 0.5
    ) -> list[SearchResult]:
        return await self._client.recall(self._tenant_id, query, count, threshold)

    async def update(self, memory_id: str, content: str) -> None:
        return await self._client.update(self._tenant_id, memory_id, content)

    async def forget(self, memory_id: str) -> None:
        return await self._client.forget(self._tenant_id, memory_id)

    async def delete(self, memory_id: str) -> None:
        return await self._client.delete(self._tenant_id, memory_id)

    async def link(self, source_id: str, target_id: str, link_type: str) -> None:
        return await self._client.link(self._tenant_id, source_id, target_id, link_type)

    async def get_related(self, memory_id: str) -> list[MemoryLink]:
        return await self._client.get_related(self._tenant_id, memory_id)

    async def extract(self, conversation_text: str, source_id: str | None = None) -> list[str]:
        return await self._client.extract(self._tenant_id, conversation_text, source_id)


class _ScopedCore:
    def __init__(self, core: CoreMemory, tenant_id: str):
        self._core = core
        self._tid = tenant_id

    async def read(self) -> tuple[str, int]:
        return await self._core.read(self._tid)

    async def append(self, section: str, text: str) -> int:
        return await self._core.append(self._tid, section, text)

    async def replace(self, old: str, new: str) -> int:
        return await self._core.replace(self._tid, old, new)

    async def overwrite(self, content: str, expected_version: int) -> int:
        return await self._core.overwrite(self._tid, content, expected_version)
