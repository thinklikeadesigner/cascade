import pytest
from cascade_memory.stores.memory import InMemoryStore
from cascade_memory.models import MemoryRecord
from cascade_memory.errors import ConcurrencyError, MemoryNotFoundError, TenantIsolationError


class TestCoreMemory:
    @pytest.fixture
    def store(self):
        return InMemoryStore()

    async def test_get_core_empty(self, store):
        content, version = await store.get_core("t1")
        assert content == ""
        assert version == 0

    async def test_upsert_core(self, store):
        v = await store.upsert_core("t1", "hello", expected_version=0)
        assert v == 1
        content, version = await store.get_core("t1")
        assert content == "hello"
        assert version == 1

    async def test_upsert_core_concurrency_error(self, store):
        await store.upsert_core("t1", "v1", expected_version=0)
        with pytest.raises(ConcurrencyError):
            await store.upsert_core("t1", "v2", expected_version=0)

    async def test_tenant_isolation(self, store):
        await store.upsert_core("t1", "tenant1", expected_version=0)
        content, _ = await store.get_core("t2")
        assert content == ""


class TestArchivalMemory:
    @pytest.fixture
    def store(self):
        return InMemoryStore()

    async def test_save_and_get(self, store):
        m = MemoryRecord(id="", content="test fact", memory_type="fact")
        mid = await store.save("t1", m)
        assert mid
        retrieved = await store.get("t1", mid)
        assert retrieved.content == "test fact"

    async def test_get_not_found(self, store):
        with pytest.raises(MemoryNotFoundError):
            await store.get("t1", "nonexistent")

    async def test_list_by_status(self, store):
        await store.save("t1", MemoryRecord(id="", content="a", memory_type="fact"))
        await store.save("t1", MemoryRecord(id="", content="b", memory_type="fact", status="archived"))
        active = await store.list("t1", status="active")
        assert len(active) == 1
        assert active[0].content == "a"

    async def test_save_batch(self, store):
        memories = [
            MemoryRecord(id="", content=f"fact {i}", memory_type="fact")
            for i in range(3)
        ]
        ids = await store.save_batch("t1", memories)
        assert len(ids) == 3

    async def test_update(self, store):
        mid = await store.save("t1", MemoryRecord(id="", content="old", memory_type="fact"))
        await store.update("t1", mid, content="new")
        m = await store.get("t1", mid)
        assert m.content == "new"

    async def test_delete(self, store):
        mid = await store.save("t1", MemoryRecord(id="", content="x", memory_type="fact"))
        await store.delete("t1", mid)
        with pytest.raises(MemoryNotFoundError):
            await store.get("t1", mid)

    async def test_delete_all(self, store):
        await store.save("t1", MemoryRecord(id="", content="a", memory_type="fact"))
        await store.save("t1", MemoryRecord(id="", content="b", memory_type="fact"))
        await store.save("t2", MemoryRecord(id="", content="c", memory_type="fact"))
        count = await store.delete_all("t1")
        assert count == 2
        assert len(await store.list("t2")) == 1


class TestSearch:
    @pytest.fixture
    def store(self):
        return InMemoryStore()

    async def test_search_by_cosine_similarity(self, store):
        m1 = MemoryRecord(id="", content="python", memory_type="fact", embedding=[1.0, 0.0, 0.0])
        m2 = MemoryRecord(id="", content="java", memory_type="fact", embedding=[0.0, 1.0, 0.0])
        await store.save("t1", m1)
        await store.save("t1", m2)
        results = await store.search("t1", [1.0, 0.0, 0.0], count=5, threshold=0.0)
        assert results[0].memory.content == "python"
        assert results[0].similarity > results[1].similarity

    async def test_search_excludes_no_embedding(self, store):
        await store.save("t1", MemoryRecord(id="", content="no vec", memory_type="fact"))
        results = await store.search("t1", [1.0, 0.0], count=5, threshold=0.0)
        assert len(results) == 0


class TestLinks:
    @pytest.fixture
    def store(self):
        return InMemoryStore()

    async def test_add_and_get_links(self, store):
        id1 = await store.save("t1", MemoryRecord(id="", content="a", memory_type="fact"))
        id2 = await store.save("t1", MemoryRecord(id="", content="b", memory_type="fact"))
        await store.add_link("t1", id1, id2, "supports")
        links = await store.get_links("t1", id1)
        assert len(links) == 1
        assert links[0].link_type == "supports"

    async def test_cross_tenant_link_fails(self, store):
        id1 = await store.save("t1", MemoryRecord(id="", content="a", memory_type="fact"))
        id2 = await store.save("t2", MemoryRecord(id="", content="b", memory_type="fact"))
        with pytest.raises(TenantIsolationError):
            await store.add_link("t1", id1, id2, "related")


class TestDecay:
    @pytest.fixture
    def store(self):
        return InMemoryStore()

    async def test_touch_accessed(self, store):
        mid = await store.save("t1", MemoryRecord(id="", content="x", memory_type="fact"))
        await store.touch_accessed("t1", [mid])
        m = await store.get("t1", mid)
        assert m.last_accessed_at is not None
