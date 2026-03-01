"""Tests for dynamic system prompt construction."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


class TestBuildSystemPrompt:
    @pytest.mark.asyncio
    async def test_includes_date_context(self):
        from cascade_api.agent.system_prompt import build_system_prompt

        mock_sb = MagicMock()
        # No core memory
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        # Tenant timezone
        tenant = {"timezone": "America/New_York", "morning_hour": 7, "morning_minute": 0, "review_day": 0}

        prompt = await build_system_prompt(mock_sb, "tenant-1", tenant)
        assert "Date:" in prompt
        assert "Days left in month:" in prompt

    @pytest.mark.asyncio
    async def test_includes_core_memory_when_present(self):
        from cascade_api.agent.system_prompt import build_system_prompt

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
            {"content": "## User Profile\n- Name: Test User"}
        ]
        tenant = {"timezone": "America/New_York", "morning_hour": 7, "morning_minute": 0, "review_day": 0}

        prompt = await build_system_prompt(mock_sb, "tenant-1", tenant)
        assert "## User Profile" in prompt
        assert "Test User" in prompt

    @pytest.mark.asyncio
    async def test_includes_base_prompt(self):
        from cascade_api.agent.system_prompt import build_system_prompt

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        tenant = {"timezone": "America/New_York", "morning_hour": 7, "morning_minute": 0, "review_day": 0}

        prompt = await build_system_prompt(mock_sb, "tenant-1", tenant)
        assert "Coaching Tone" in prompt
