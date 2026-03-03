"""Integration test for the full memory flow.

Tests the end-to-end path: system prompt includes core memory,
agent tools work, decay is available via cascade-memory.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_memory_client(core_content: str = ""):
    """Build a mock MemoryClient for patching get_memory_client."""
    core_mock = AsyncMock()
    core_mock.read.return_value = (core_content, 1 if core_content else 0)
    core_mock.append.return_value = 2

    scoped = MagicMock()
    scoped.core = core_mock
    scoped.save = AsyncMock(return_value="mem-1")
    scoped.recall = AsyncMock(return_value=[])
    scoped.forget = AsyncMock()

    client = MagicMock()
    client.for_tenant.return_value = scoped
    client.run_decay = AsyncMock(return_value=42)
    client.store = MagicMock()
    client.store.update = AsyncMock()
    client.embedder = MagicMock()
    client.embedder.embed = AsyncMock(return_value=[0.1] * 768)
    return client


class TestMemoryIntegration:
    @pytest.mark.asyncio
    async def test_system_prompt_includes_date_and_memory(self):
        """Verify build_system_prompt assembles all sections."""
        from cascade_api.agent.system_prompt import build_system_prompt

        mock_sb = MagicMock()
        tenant = {"timezone": "UTC", "morning_hour": 8, "morning_minute": 0, "review_day": 0}

        client = _mock_memory_client("## User Profile\n- Name: Integration Test User")
        with patch("cascade_api.agent.system_prompt.get_memory_client", return_value=client):
            prompt = await build_system_prompt(mock_sb, "tenant-1", tenant)

        assert "Coaching Tone" in prompt
        assert "Date:" in prompt
        assert "Days left in month:" in prompt
        assert "Integration Test User" in prompt
        assert "Core Memory" in prompt

    @pytest.mark.asyncio
    async def test_all_memory_tools_registered(self):
        """Verify all 8 memory tools are in TOOLS and _EXECUTORS."""
        from cascade_api.agent.tools import TOOLS, _EXECUTORS

        memory_tools = [
            "core_memory_read", "core_memory_append", "core_memory_replace",
            "save_memory", "recall", "update_memory", "forget_memory",
            "get_current_datetime",
        ]
        tool_names = {t["name"] for t in TOOLS}
        for name in memory_tools:
            assert name in tool_names, f"{name} missing from TOOLS"
            assert name in _EXECUTORS, f"{name} missing from _EXECUTORS"

    @pytest.mark.asyncio
    async def test_core_memory_append_via_execute_tool(self):
        """Verify core_memory_append works through execute_tool."""
        from cascade_api.agent.tools import execute_tool

        mock_sb = MagicMock()
        client = _mock_memory_client()

        with patch("cascade_api.dependencies.get_memory_client", return_value=client):
            result = await execute_tool(
                "core_memory_append",
                {"section": "User Profile", "content": "- Name: New User"},
                mock_sb,
                "tenant-1",
            )
        assert "append" in result.lower()

    @pytest.mark.asyncio
    async def test_core_memory_append_limit_error(self):
        """core_memory_append returns error when limit exceeded."""
        from cascade_api.agent.tools import execute_tool
        from cascade_memory.errors import StoreLimitError

        mock_sb = MagicMock()
        client = _mock_memory_client()
        client.for_tenant.return_value.core.append.side_effect = StoreLimitError(
            "Core memory exceeds 3000 char limit"
        )

        with patch("cascade_api.dependencies.get_memory_client", return_value=client):
            result = await execute_tool(
                "core_memory_append",
                {"section": "Test", "content": "- " + "y" * 50},
                mock_sb,
                "tenant-1",
            )
        assert "error" in result.lower() or "limit" in result.lower()

    def test_decay_available_from_package(self):
        """Verify cascade_memory.decay.calculate_decay works."""
        from datetime import datetime, timedelta, timezone

        from cascade_memory.decay import calculate_decay

        now = datetime.now(timezone.utc)
        assert calculate_decay(now) > 0.99

        week = calculate_decay(now - timedelta(days=7))
        assert 0.65 < week < 0.75

        month = calculate_decay(now - timedelta(days=30))
        assert 0.15 < month < 0.30
