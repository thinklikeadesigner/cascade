"""Tests for background memory extraction."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestExtractMemories:
    @pytest.mark.asyncio
    async def test_extracts_facts_from_conversation(self):
        from cascade_api.agent.memory_extractor import extract_memories_from_conversation

        mock_sb = MagicMock()
        mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
        mock_sb.table.return_value.insert.return_value.execute.return_value.data = [
            {"id": "mem-1", "content": "User prefers morning work", "status": "active"}
        ]

        mock_anthropic = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(
            type="text",
            text='[{"content": "User prefers morning work", "memory_type": "preference", "tags": ["schedule"]}]'
        )]
        mock_anthropic.messages.create = AsyncMock(return_value=mock_response)

        with patch("cascade_api.agent.memory_extractor.generate_embedding", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1] * 1536

            result = await extract_memories_from_conversation(
                supabase=mock_sb,
                anthropic_client=mock_anthropic,
                tenant_id="tenant-1",
                conversation_text="I work best in the mornings, afternoons I'm usually tired",
                conversation_id=42,
            )
            assert len(result) >= 1
