import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_traced_ask_calls_langfuse_and_returns_response():
    """Traced ask should create a Langfuse generation and return Claude's response."""
    mock_anthropic = AsyncMock()
    mock_anthropic.messages.create.return_value = MagicMock(
        content=[MagicMock(text="test response")]
    )

    with patch("cascade_api.observability.langfuse_client.get_langfuse") as mock_lf:
        mock_trace = MagicMock()
        mock_generation = MagicMock()
        mock_trace.generation.return_value = mock_generation
        mock_lf.return_value.trace.return_value = mock_trace

        from cascade_api.observability.langfuse_client import traced_ask

        result = await traced_ask(
            system_prompt="You are helpful.",
            user_message="Hello",
            api_key="sk-test",
            user_id="user-123",
            context="morning_message",
        )

        assert result == "test response"
        mock_lf.return_value.trace.assert_called_once()
        mock_trace.generation.assert_called_once()
        mock_generation.end.assert_called_once()
