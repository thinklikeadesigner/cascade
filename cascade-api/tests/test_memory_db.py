"""Tests for memory database operations."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_sb():
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    sb.table.return_value.insert.return_value.execute.return_value.data = [{}]
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]
    sb.table.return_value.upsert.return_value.execute.return_value.data = [{}]
    return sb


class TestGetCoreMemory:
    @pytest.mark.asyncio
    async def test_returns_empty_string_when_no_record(self, mock_sb):
        from cascade_api.db.memory import get_core_memory

        result = await get_core_memory(mock_sb, "tenant-1")
        assert result == ""

    @pytest.mark.asyncio
    async def test_returns_content_when_record_exists(self, mock_sb):
        from cascade_api.db.memory import get_core_memory

        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"content": "## User Profile\n- Name: Test"}
        ]
        result = await get_core_memory(mock_sb, "tenant-1")
        assert result == "## User Profile\n- Name: Test"


class TestUpsertCoreMemory:
    @pytest.mark.asyncio
    async def test_upserts_content(self, mock_sb):
        from cascade_api.db.memory import upsert_core_memory

        mock_sb.table.return_value.upsert.return_value.execute.return_value.data = [
            {"content": "new content", "version": 2}
        ]
        result = await upsert_core_memory(mock_sb, "tenant-1", "new content")
        assert result["version"] == 2


class TestSaveMemory:
    @pytest.mark.asyncio
    async def test_inserts_memory(self, mock_sb):
        from cascade_api.db.memory import save_memory

        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "mem-1", "content": "User prefers mornings", "status": "active"}
        ]
        result = await save_memory(
            mock_sb, "tenant-1", "User prefers mornings",
            memory_type="preference", tags=["schedule"],
        )
        assert result["status"] == "active"


class TestGetMemories:
    @pytest.mark.asyncio
    async def test_returns_active_memories(self, mock_sb):
        from cascade_api.db.memory import get_memories

        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"id": "mem-1", "content": "fact 1"},
        ]
        result = await get_memories(mock_sb, "tenant-1")
        assert len(result) == 1


class TestUpdateMemoryStatus:
    @pytest.mark.asyncio
    async def test_updates_status(self, mock_sb):
        from cascade_api.db.memory import update_memory_status

        mock_sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [
            {"id": "mem-1", "status": "forgotten"}
        ]
        result = await update_memory_status(mock_sb, "tenant-1", "mem-1", "forgotten")
        assert result["status"] == "forgotten"
