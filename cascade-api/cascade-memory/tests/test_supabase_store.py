"""Tests for SupabaseStore — mock the Supabase client, verify correct API calls."""
import pytest
from unittest.mock import MagicMock
from cascade_memory.stores.supabase import SupabaseStore
from cascade_memory.models import MemoryRecord
from cascade_memory.errors import ConcurrencyError, TenantIsolationError


def _mock_supabase():
    """Build a mock Supabase client with chainable query builder."""
    sb = MagicMock()

    def _make_chain(data=None):
        chain = MagicMock()
        chain.execute.return_value = MagicMock(data=data or [])
        chain.eq.return_value = chain
        chain.gte.return_value = chain
        chain.lte.return_value = chain
        chain.order.return_value = chain
        chain.limit.return_value = chain
        chain.select.return_value = chain
        chain.insert.return_value = chain
        chain.update.return_value = chain
        chain.upsert.return_value = chain
        chain.delete.return_value = chain
        return chain

    sb.table.return_value = _make_chain()
    sb.rpc.return_value = _make_chain()
    return sb


class TestGetCore:
    async def test_returns_content_and_version(self):
        sb = _mock_supabase()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"content": "hello", "version": 3}]
        )
        store = SupabaseStore(sb)
        content, version = await store.get_core("t1")
        assert content == "hello"
        assert version == 3

    async def test_returns_empty_when_no_row(self):
        sb = _mock_supabase()
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        store = SupabaseStore(sb)
        content, version = await store.get_core("t1")
        assert content == ""
        assert version == 0


class TestUpsertCore:
    async def test_first_write_uses_upsert(self):
        sb = _mock_supabase()
        chain = MagicMock()
        chain.execute.return_value = MagicMock(data=[{"version": 1}])
        sb.table.return_value.upsert.return_value = chain
        store = SupabaseStore(sb)
        version = await store.upsert_core("t1", "content", expected_version=0)
        assert version == 1

    async def test_version_mismatch_raises_concurrency_error(self):
        sb = _mock_supabase()
        chain = MagicMock()
        chain.execute.return_value = MagicMock(data=[])
        chain.eq.return_value = chain
        sb.table.return_value.update.return_value = chain
        store = SupabaseStore(sb)
        with pytest.raises(ConcurrencyError):
            await store.upsert_core("t1", "content", expected_version=5)


class TestSave:
    async def test_save_returns_id(self):
        sb = _mock_supabase()
        chain = MagicMock()
        chain.execute.return_value = MagicMock(data=[{"id": "abc-123"}])
        sb.table.return_value.insert.return_value = chain
        store = SupabaseStore(sb)
        m = MemoryRecord(id="", content="test", memory_type="fact")
        mid = await store.save("t1", m)
        assert mid == "abc-123"


class TestSearch:
    async def test_search_calls_rpc(self):
        sb = _mock_supabase()
        sb.rpc.return_value.execute.return_value = MagicMock(data=[
            {
                "id": "m1", "content": "python", "memory_type": "fact",
                "tags": ["tech"], "confidence": 0.9, "decay_score": 0.8,
                "similarity": 0.95, "created_at": "2026-01-01T00:00:00Z",
                "last_confirmed_at": "2026-01-01T00:00:00Z",
            }
        ])
        store = SupabaseStore(sb)
        results = await store.search("t1", [0.1, 0.2], count=5, threshold=0.5)
        assert len(results) == 1
        assert results[0].memory.content == "python"
        assert results[0].similarity == 0.95


class TestDelete:
    async def test_delete_calls_supabase(self):
        sb = _mock_supabase()
        store = SupabaseStore(sb)
        await store.delete("t1", "mem-id")
        # Verify delete was called on the table
        sb.table.assert_called()


class TestDecay:
    async def test_update_decay_scores_calls_rpc(self):
        sb = _mock_supabase()
        sb.rpc.return_value.execute.return_value = MagicMock(data=42)
        store = SupabaseStore(sb)
        count = await store.update_decay_scores(0.95)
        assert count == 42


class TestLinks:
    async def test_add_link_validates_tenant(self):
        sb = _mock_supabase()
        # Both memories exist for tenant
        chain = MagicMock()
        chain.execute.return_value = MagicMock(data=[{"id": "m1"}])
        chain.eq.return_value = chain
        sb.table.return_value.select.return_value = chain
        sb.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "link-1"}]
        )
        store = SupabaseStore(sb)
        await store.add_link("t1", "m1", "m2", "supports")

    async def test_add_link_cross_tenant_fails(self):
        sb = _mock_supabase()
        chain = MagicMock()
        chain.execute.return_value = MagicMock(data=[])
        chain.eq.return_value = chain
        sb.table.return_value.select.return_value = chain
        store = SupabaseStore(sb)
        with pytest.raises(TenantIsolationError):
            await store.add_link("t1", "m1", "m2", "related")
