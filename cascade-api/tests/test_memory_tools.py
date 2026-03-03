"""Tests for memory agent tools using cascade-memory mocks."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cascade_memory.models import MemoryRecord, SearchResult


def _mock_memory_client():
    """Build a mock MemoryClient for patching get_memory_client."""
    core_mock = AsyncMock()
    scoped = MagicMock()
    scoped.core = core_mock
    scoped.save = AsyncMock()
    scoped.recall = AsyncMock()
    scoped.update = AsyncMock()
    scoped.forget = AsyncMock()

    client = MagicMock()
    client.for_tenant.return_value = scoped
    return client


@pytest.fixture
def mock_sb():
    sb = MagicMock()
    return sb


class TestCoreMemoryRead:
    @pytest.mark.asyncio
    async def test_returns_content(self, mock_sb):
        from cascade_api.agent.tools import execute_tool

        client = _mock_memory_client()
        client.for_tenant.return_value.core.read.return_value = ("## Profile\n- Name: Test", 1)

        with patch("cascade_api.dependencies.get_memory_client", return_value=client):
            result = await execute_tool("core_memory_read", {}, mock_sb, "tenant-1")
        assert "Profile" in result

    @pytest.mark.asyncio
    async def test_returns_empty_hint(self, mock_sb):
        from cascade_api.agent.tools import execute_tool

        client = _mock_memory_client()
        client.for_tenant.return_value.core.read.return_value = ("", 0)

        with patch("cascade_api.dependencies.get_memory_client", return_value=client):
            result = await execute_tool("core_memory_read", {}, mock_sb, "tenant-1")
        assert "empty" in result


class TestCoreMemoryAppend:
    @pytest.mark.asyncio
    async def test_appends_to_section(self, mock_sb):
        from cascade_api.agent.tools import execute_tool

        client = _mock_memory_client()
        client.for_tenant.return_value.core.append.return_value = 2

        with patch("cascade_api.dependencies.get_memory_client", return_value=client):
            result = await execute_tool(
                "core_memory_append",
                {"section": "User Profile", "content": "- Timezone: PST"},
                mock_sb,
                "tenant-1",
            )
        assert "appended" in result.lower()


class TestCoreMemoryReplace:
    @pytest.mark.asyncio
    async def test_replaces_line(self, mock_sb):
        from cascade_api.agent.tools import execute_tool

        client = _mock_memory_client()
        client.for_tenant.return_value.core.replace.return_value = 2

        with patch("cascade_api.dependencies.get_memory_client", return_value=client):
            result = await execute_tool(
                "core_memory_replace",
                {"old_text": "MRR: $10K", "new_text": "MRR: $15K"},
                mock_sb,
                "tenant-1",
            )
        assert "replaced" in result.lower()


class TestSaveMemory:
    @pytest.mark.asyncio
    async def test_saves_memory(self, mock_sb):
        from cascade_api.agent.tools import execute_tool

        client = _mock_memory_client()
        client.for_tenant.return_value.save.return_value = "mem-123"

        with patch("cascade_api.dependencies.get_memory_client", return_value=client):
            result = await execute_tool(
                "save_memory",
                {"content": "User prefers mornings", "memory_type": "preference"},
                mock_sb,
                "tenant-1",
            )
        assert "saved" in result.lower()
        assert "mem-123" in result


class TestRecall:
    @pytest.mark.asyncio
    async def test_returns_memories(self, mock_sb):
        from cascade_api.agent.tools import execute_tool

        record = MemoryRecord(
            id="mem-1", content="User likes mornings", memory_type="preference",
        )
        client = _mock_memory_client()
        client.for_tenant.return_value.recall.return_value = [
            SearchResult(memory=record, similarity=0.85, rank_score=0.85),
        ]

        with patch("cascade_api.dependencies.get_memory_client", return_value=client):
            result = await execute_tool("recall", {"query": "morning"}, mock_sb, "tenant-1")
        assert "mem-1" in result
        assert "0.85" in result


class TestForgetMemory:
    @pytest.mark.asyncio
    async def test_forgets(self, mock_sb):
        from cascade_api.agent.tools import execute_tool

        client = _mock_memory_client()

        with patch("cascade_api.dependencies.get_memory_client", return_value=client):
            result = await execute_tool(
                "forget_memory", {"memory_id": "mem-1"}, mock_sb, "tenant-1",
            )
        assert "forgotten" in result.lower()
