"""Tests for embedding generation and search."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestGenerateEmbedding:
    @pytest.mark.asyncio
    async def test_returns_embedding_list(self):
        from cascade_api.db.embeddings import generate_embedding

        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)

        with patch("cascade_api.db.embeddings._get_openai_client", return_value=mock_client):
            result = await generate_embedding("test text")
            assert len(result) == 1536


class TestSemanticSearch:
    @pytest.mark.asyncio
    async def test_returns_matched_memories(self):
        from cascade_api.db.embeddings import semantic_search

        mock_sb = MagicMock()
        mock_sb.rpc.return_value.execute.return_value.data = [
            {"id": "mem-1", "content": "test fact", "similarity": 0.85}
        ]

        with patch("cascade_api.db.embeddings.generate_embedding", new_callable=AsyncMock) as mock_embed:
            mock_embed.return_value = [0.1] * 1536
            results = await semantic_search(mock_sb, "tenant-1", "test query")
            assert len(results) == 1
            assert results[0]["similarity"] == 0.85
