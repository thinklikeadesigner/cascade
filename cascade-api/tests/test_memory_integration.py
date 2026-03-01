"""Integration test for the full memory flow.

Tests the end-to-end path: system prompt includes core memory,
agent tools work, extraction runs.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestMemoryIntegration:
    @pytest.mark.asyncio
    async def test_system_prompt_includes_date_and_memory(self):
        """Verify build_system_prompt assembles all sections."""
        from cascade_api.agent.system_prompt import build_system_prompt

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"content": "## User Profile\n- Name: Integration Test User"}
        ]
        tenant = {"timezone": "UTC", "morning_hour": 8, "morning_minute": 0, "review_day": 0}

        prompt = await build_system_prompt(mock_sb, "tenant-1", tenant)

        # Has base prompt
        assert "Coaching Tone" in prompt
        # Has date context
        assert "Date:" in prompt
        assert "Days left in month:" in prompt
        # Has core memory
        assert "Integration Test User" in prompt
        # Has memory instructions
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
    async def test_core_memory_append_creates_section(self):
        """Verify core_memory_append creates a new section when one doesn't exist."""
        from cascade_api.agent.tools import execute_tool

        mock_sb = MagicMock()
        # Empty core memory
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_sb.table.return_value.upsert.return_value.execute.return_value.data = [
            {"content": "## User Profile\n- Name: New User", "version": 1}
        ]

        result = await execute_tool(
            "core_memory_append",
            {"section": "User Profile", "content": "- Name: New User"},
            mock_sb,
            "tenant-1",
        )
        assert "append" in result.lower()

    @pytest.mark.asyncio
    async def test_decay_calculation_correctness(self):
        """Verify decay formula produces expected values."""
        from cascade_api.agent.memory_decay import calculate_decay
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)

        # Today: ~1.0
        assert calculate_decay(now) > 0.99

        # 7 days: ~0.698
        week = calculate_decay(now - timedelta(days=7))
        assert 0.65 < week < 0.75

        # 30 days: ~0.215
        month = calculate_decay(now - timedelta(days=30))
        assert 0.15 < month < 0.30

        # 90 days: ~0.01
        quarter = calculate_decay(now - timedelta(days=90))
        assert quarter < 0.02


class TestTenantIsolation:
    """Verify no cross-tenant data leakage in memory operations."""

    @pytest.mark.asyncio
    async def test_update_memory_accessed_requires_tenant_id(self):
        """update_memory_accessed must accept and use tenant_id."""
        import inspect
        from cascade_api.db.memory import update_memory_accessed

        sig = inspect.signature(update_memory_accessed)
        params = list(sig.parameters.keys())
        assert "tenant_id" in params, "update_memory_accessed must require tenant_id"

    @pytest.mark.asyncio
    async def test_add_memory_link_requires_tenant_id(self):
        """add_memory_link must accept and use tenant_id."""
        import inspect
        from cascade_api.db.memory import add_memory_link

        sig = inspect.signature(add_memory_link)
        params = list(sig.parameters.keys())
        assert "tenant_id" in params, "add_memory_link must require tenant_id"

    @pytest.mark.asyncio
    async def test_add_memory_link_validates_ownership(self):
        """add_memory_link must reject cross-tenant links."""
        from cascade_api.db.memory import add_memory_link

        mock_sb = MagicMock()
        # source belongs to tenant, target does NOT (empty result)
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.side_effect = [
            MagicMock(data=[{"id": "mem-1"}]),  # source found
            MagicMock(data=[]),                   # target NOT found for this tenant
        ]

        with pytest.raises(ValueError, match="Cannot link memories across tenants"):
            await add_memory_link(mock_sb, "tenant-1", "mem-1", "mem-2", "related")

    @pytest.mark.asyncio
    async def test_core_memory_size_limit_enforced(self):
        """core_memory_append must reject writes that exceed 3000 chars."""
        from cascade_api.agent.tools import execute_tool

        mock_sb = MagicMock()
        # Current core memory is near the limit
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"content": "x" * 2990, "version": 1}
        ]

        result = await execute_tool(
            "core_memory_append",
            {"section": "Test", "content": "- " + "y" * 50},
            mock_sb,
            "tenant-1",
        )
        assert "error" in result.lower() or "limit" in result.lower()
