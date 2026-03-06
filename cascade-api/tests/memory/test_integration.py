"""End-to-end integration test: extract → embed → save → recall → decay → recall."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from cascade_api.memory import MemoryClient
from cascade_api.memory.stores.memory import InMemoryStore
from cascade_api.memory.embedders.fake import FakeEmbedder
from cascade_api.memory.extractors.anthropic import AnthropicExtractor


@pytest.fixture
def mock_anthropic():
    client = AsyncMock()
    client.messages.create.return_value = MagicMock(
        content=[
            MagicMock(
                text='[{"content":"User prefers TypeScript over JavaScript","memory_type":"preference","tags":["tech","language"],"confidence":0.95}]'
            )
        ]
    )
    return client


@pytest.fixture
def client(mock_anthropic):
    return MemoryClient(
        store=InMemoryStore(),
        embedder=FakeEmbedder(dimensions=16),
        extractor=AnthropicExtractor(client=mock_anthropic),
    )


class TestFullFlow:
    async def test_extract_then_recall(self, client):
        scoped = client.for_tenant("tenant-1")

        # Extract memories from conversation
        ids = await scoped.extract("User: I much prefer TypeScript.\nAssistant: Got it!")
        assert len(ids) == 1

        # Recall should find it
        results = await scoped.recall("TypeScript", threshold=0.0)
        assert len(results) >= 1
        assert "TypeScript" in results[0].memory.content

    async def test_core_memory_lifecycle(self, client):
        scoped = client.for_tenant("tenant-1")

        # Start empty
        content, v = await scoped.core.read()
        assert content == ""
        assert v == 0

        # Append
        v = await scoped.core.append("Preferences", "Likes TypeScript")
        assert v == 1

        # Append to same section
        v = await scoped.core.append("Preferences", "Prefers dark mode")
        assert v == 2

        # Replace
        v = await scoped.core.replace("Likes TypeScript", "Loves TypeScript")
        content, _ = await scoped.core.read()
        assert "Loves TypeScript" in content
        assert "Likes TypeScript" not in content

    async def test_archival_lifecycle(self, client):
        scoped = client.for_tenant("tenant-1")

        # Save
        mid = await scoped.save("User is a night owl", memory_type="preference", tags=["schedule"])
        assert mid

        # Recall
        results = await scoped.recall("User is a night owl", threshold=0.0)
        assert len(results) >= 1

        # Forget (soft delete)
        await scoped.forget(mid)
        results = await scoped.recall("User is a night owl", threshold=0.0)
        assert len(results) == 0  # forgotten memories excluded from search

    async def test_links(self, client):
        scoped = client.for_tenant("tenant-1")

        id1 = await scoped.save("User likes React", memory_type="preference")
        id2 = await scoped.save("User building a Next.js app", memory_type="fact")
        await scoped.link(id1, id2, "related")

        links = await scoped.get_related(id1)
        assert len(links) == 1
        assert links[0].link_type == "related"

    async def test_decay_reduces_scores(self, client):
        scoped = client.for_tenant("tenant-1")
        mid = await scoped.save("old fact", memory_type="fact")

        # Manually age the memory
        m = await client.store.get("tenant-1", mid)
        from datetime import datetime, timezone, timedelta

        m.last_accessed_at = datetime.now(timezone.utc) - timedelta(days=30)

        count = await client.run_decay()
        assert count >= 1

        m = await client.store.get("tenant-1", mid)
        assert m.decay_score < 0.3  # 0.95^30 ≈ 0.21

    async def test_tenant_isolation(self, client):
        s1 = client.for_tenant("t1")
        s2 = client.for_tenant("t2")

        await s1.save("secret for t1", memory_type="fact")
        results = await s2.recall("secret", threshold=0.0)
        assert len(results) == 0  # t2 cannot see t1's memories

    async def test_hard_delete(self, client):
        scoped = client.for_tenant("tenant-1")
        mid = await scoped.save("to be deleted", memory_type="fact")
        await scoped.delete(mid)

        from cascade_api.memory.errors import MemoryNotFoundError

        with pytest.raises(MemoryNotFoundError):
            await client.store.get("tenant-1", mid)
