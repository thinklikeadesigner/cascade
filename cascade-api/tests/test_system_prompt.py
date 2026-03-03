"""Tests for dynamic system prompt construction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _mock_memory_client(core_content: str = ""):
    """Build a mock MemoryClient for patching get_memory_client."""
    core_mock = AsyncMock()
    core_mock.read.return_value = (core_content, 1 if core_content else 0)

    scoped = MagicMock()
    scoped.core = core_mock

    client = MagicMock()
    client.for_tenant.return_value = scoped
    return client


class TestBuildSystemPrompt:
    @pytest.mark.asyncio
    async def test_includes_date_context(self):
        from cascade_api.agent.system_prompt import build_system_prompt

        mock_sb = MagicMock()
        tenant = {"timezone": "America/New_York", "morning_hour": 7, "morning_minute": 0, "review_day": 0}

        with patch("cascade_api.agent.system_prompt.get_memory_client", return_value=_mock_memory_client()):
            prompt = await build_system_prompt(mock_sb, "tenant-1", tenant)

        assert "Date:" in prompt
        assert "Days left in month:" in prompt

    @pytest.mark.asyncio
    async def test_includes_core_memory_when_present(self):
        from cascade_api.agent.system_prompt import build_system_prompt

        mock_sb = MagicMock()
        tenant = {"timezone": "America/New_York", "morning_hour": 7, "morning_minute": 0, "review_day": 0}

        client = _mock_memory_client("## User Profile\n- Name: Test User")
        with patch("cascade_api.agent.system_prompt.get_memory_client", return_value=client):
            prompt = await build_system_prompt(mock_sb, "tenant-1", tenant)

        assert "## User Profile" in prompt
        assert "Test User" in prompt

    @pytest.mark.asyncio
    async def test_includes_base_prompt(self):
        from cascade_api.agent.system_prompt import build_system_prompt

        mock_sb = MagicMock()
        tenant = {"timezone": "America/New_York", "morning_hour": 7, "morning_minute": 0, "review_day": 0}

        with patch("cascade_api.agent.system_prompt.get_memory_client", return_value=_mock_memory_client()):
            prompt = await build_system_prompt(mock_sb, "tenant-1", tenant)

        assert "Coaching Tone" in prompt
