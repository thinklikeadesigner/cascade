import pytest
from unittest.mock import AsyncMock, MagicMock
from cascade_memory.extractors.anthropic import AnthropicExtractor


@pytest.fixture
def mock_client():
    client = AsyncMock()
    return client


@pytest.fixture
def extractor(mock_client):
    return AnthropicExtractor(client=mock_client)


class TestExtract:
    async def test_parses_json_response(self, extractor, mock_client):
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text='[{"content":"likes python","memory_type":"preference","tags":["tech"],"confidence":0.9}]')]
        )
        results = await extractor.extract("User said they love python")
        assert len(results) == 1
        assert results[0].content == "likes python"
        assert results[0].memory_type == "preference"
        assert results[0].confidence == 0.9

    async def test_handles_empty_response(self, extractor, mock_client):
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="[]")]
        )
        results = await extractor.extract("hi")
        assert results == []

    async def test_handles_markdown_wrapped_json(self, extractor, mock_client):
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text='```json\n[{"content":"fact","memory_type":"fact","tags":[],"confidence":1.0}]\n```')]
        )
        results = await extractor.extract("something")
        assert len(results) == 1
