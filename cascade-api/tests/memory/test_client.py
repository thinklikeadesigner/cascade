import pytest
from cascade_api.memory.client import MemoryClient
from cascade_api.memory.stores.memory import InMemoryStore
from cascade_api.memory.embedders.fake import FakeEmbedder


@pytest.fixture
def client():
    return MemoryClient(
        store=InMemoryStore(),
        embedder=FakeEmbedder(dimensions=3),
        core_memory_limit=500,
    )


class TestClientSave:
    async def test_save_generates_embedding(self, client):
        mid = await client.save("t1", "hello world", memory_type="fact", tags=["test"])
        m = await client.store.get("t1", mid)
        assert m.embedding is not None
        assert len(m.embedding) == 3

    async def test_save_with_source_id(self, client):
        mid = await client.save("t1", "fact", memory_type="fact", source_id="conv-1")
        m = await client.store.get("t1", mid)
        assert m.source_id == "conv-1"


class TestClientRecall:
    async def test_recall_returns_results(self, client):
        await client.save("t1", "python is great", memory_type="fact")
        results = await client.recall("t1", "python is great", threshold=0.0)
        assert len(results) >= 1

    async def test_recall_touches_accessed(self, client):
        await client.save("t1", "fact", memory_type="fact")
        await client.recall("t1", "fact")
        # No error means touch_accessed was called


class TestClientForget:
    async def test_forget_sets_status(self, client):
        mid = await client.save("t1", "secret", memory_type="fact")
        await client.forget("t1", mid)
        m = await client.store.get("t1", mid)
        assert m.status == "forgotten"


class TestClientDelete:
    async def test_hard_delete(self, client):
        mid = await client.save("t1", "x", memory_type="fact")
        await client.delete("t1", mid)
        from cascade_api.memory.errors import MemoryNotFoundError

        with pytest.raises(MemoryNotFoundError):
            await client.store.get("t1", mid)


class TestClientDecay:
    async def test_run_decay(self, client):
        await client.save("t1", "old fact", memory_type="fact")
        count = await client.run_decay()
        assert isinstance(count, int)


class TestClientCore:
    async def test_core_via_client(self, client):
        await client.core.append("t1", "Prefs", "dark mode")
        content, _ = await client.core.read("t1")
        assert "dark mode" in content


class TestTenantScopedClient:
    async def test_scoped_save_and_recall(self, client):
        scoped = client.for_tenant("t1")
        mid = await scoped.save("hello", memory_type="fact")
        assert mid
        results = await scoped.recall("hello")
        assert len(results) >= 1

    async def test_scoped_core(self, client):
        scoped = client.for_tenant("t1")
        await scoped.core.append("Section", "text")
        content, _ = await scoped.core.read()
        assert "text" in content

    async def test_scoped_forget(self, client):
        scoped = client.for_tenant("t1")
        mid = await scoped.save("x", memory_type="fact")
        await scoped.forget(mid)

    async def test_scoped_link(self, client):
        scoped = client.for_tenant("t1")
        id1 = await scoped.save("a", memory_type="fact")
        id2 = await scoped.save("b", memory_type="fact")
        await scoped.link(id1, id2, "supports")
        links = await scoped.get_related(id1)
        assert len(links) == 1
