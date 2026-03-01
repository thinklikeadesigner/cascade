"""Tests for memory agent tools."""

from __future__ import annotations

from unittest.mock import MagicMock, AsyncMock, patch

import pytest


@pytest.fixture
def mock_sb():
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    sb.table.return_value.upsert.return_value.execute.return_value.data = [{}]
    sb.table.return_value.insert.return_value.execute.return_value.data = [{}]
    sb.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.return_value.data = [{}]
    return sb


class TestCoreMemoryRead:
    @pytest.mark.asyncio
    async def test_returns_content(self, mock_sb):
        from cascade_api.agent.tools import execute_tool

        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"content": "## Profile\n- Name: Test"}
        ]
        result = await execute_tool("core_memory_read", {}, mock_sb, "tenant-1")
        assert "Profile" in result


class TestCoreMemoryAppend:
    @pytest.mark.asyncio
    async def test_appends_to_section(self, mock_sb):
        from cascade_api.agent.tools import execute_tool

        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"content": "## User Profile\n- Name: Test\n\n## Active Goals\n- Goal 1", "version": 1}
        ]
        mock_sb.table.return_value.upsert.return_value.execute.return_value.data = [
            {"content": "updated", "version": 2}
        ]
        result = await execute_tool(
            "core_memory_append",
            {"section": "User Profile", "content": "- Timezone: PST"},
            mock_sb,
            "tenant-1",
        )
        assert "appended" in result.lower() or "updated" in result.lower()


class TestCoreMemoryReplace:
    @pytest.mark.asyncio
    async def test_replaces_line(self, mock_sb):
        from cascade_api.agent.tools import execute_tool

        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"content": "## User Profile\n- Name: Test\n- MRR: $10K", "version": 1}
        ]
        mock_sb.table.return_value.upsert.return_value.execute.return_value.data = [
            {"content": "updated", "version": 2}
        ]
        result = await execute_tool(
            "core_memory_replace",
            {"old_text": "MRR: $10K", "new_text": "MRR: $15K"},
            mock_sb,
            "tenant-1",
        )
        assert "replaced" in result.lower() or "updated" in result.lower()
