"""Tests for Langfuse tracing in the agent loop."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_deps():
    """Set up mocks for agent loop dependencies."""
    # Mock supabase
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"timezone": "America/New_York", "morning_hour": 7, "morning_minute": 0, "review_day": 1}
    ]

    # Mock anthropic — return a text-only response (no tool use)
    mock_response = MagicMock()
    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "Here's your status update."
    mock_response.content = [text_block]
    mock_response.model = "claude-haiku-4-5-20251001"
    mock_response.usage = MagicMock(input_tokens=100, output_tokens=50)
    mock_response.stop_reason = "end_turn"

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    return mock_sb, mock_client, mock_response


@pytest.mark.asyncio
async def test_run_agent_creates_langfuse_trace(mock_deps):
    """run_agent should create a Langfuse trace with tenant metadata."""
    mock_sb, mock_client, _ = mock_deps

    mock_langfuse = MagicMock()
    mock_trace = MagicMock()
    mock_langfuse.trace.return_value = mock_trace
    mock_generation = MagicMock()
    mock_trace.generation.return_value = mock_generation

    with (
        patch("cascade_api.agent.loop.get_supabase", return_value=mock_sb),
        patch("cascade_api.agent.loop.anthropic.AsyncAnthropic", return_value=mock_client),
        patch("cascade_api.agent.loop.build_system_prompt", new_callable=AsyncMock, return_value="system prompt"),
        patch("cascade_api.agent.loop.get_langfuse", return_value=mock_langfuse),
        patch("cascade_api.agent.loop.should_eval", return_value=False),
    ):
        from cascade_api.agent.loop import run_agent
        text, messages = await run_agent(
            tenant_id="tenant-123",
            user_message="How am I doing?",
            conversation_history=[],
            api_key="sk-test",
        )

        assert text == "Here's your status update."
        # Verify trace was created with tenant metadata
        mock_langfuse.trace.assert_called_once()
        call_kwargs = mock_langfuse.trace.call_args[1]
        assert call_kwargs["user_id"] == "tenant-123"
        assert "tenant_id" in call_kwargs["metadata"]


@pytest.mark.asyncio
async def test_run_agent_creates_generation_span(mock_deps):
    """Each LLM call in the loop should create a Langfuse generation."""
    mock_sb, mock_client, _ = mock_deps

    mock_langfuse = MagicMock()
    mock_trace = MagicMock()
    mock_langfuse.trace.return_value = mock_trace
    mock_generation = MagicMock()
    mock_trace.generation.return_value = mock_generation

    with (
        patch("cascade_api.agent.loop.get_supabase", return_value=mock_sb),
        patch("cascade_api.agent.loop.anthropic.AsyncAnthropic", return_value=mock_client),
        patch("cascade_api.agent.loop.build_system_prompt", new_callable=AsyncMock, return_value="system prompt"),
        patch("cascade_api.agent.loop.get_langfuse", return_value=mock_langfuse),
        patch("cascade_api.agent.loop.should_eval", return_value=False),
    ):
        from cascade_api.agent.loop import run_agent
        await run_agent(
            tenant_id="tenant-123",
            user_message="status",
            conversation_history=[],
            api_key="sk-test",
        )

        # Verify generation was created and ended
        mock_trace.generation.assert_called_once()
        gen_kwargs = mock_trace.generation.call_args[1]
        assert "model" in gen_kwargs
        mock_generation.end.assert_called_once()


@pytest.mark.asyncio
async def test_run_agent_works_without_langfuse(mock_deps):
    """Agent loop still works when Langfuse is not configured."""
    mock_sb, mock_client, _ = mock_deps

    with (
        patch("cascade_api.agent.loop.get_supabase", return_value=mock_sb),
        patch("cascade_api.agent.loop.anthropic.AsyncAnthropic", return_value=mock_client),
        patch("cascade_api.agent.loop.build_system_prompt", new_callable=AsyncMock, return_value="system prompt"),
        patch("cascade_api.agent.loop.get_langfuse", return_value=None),
        patch("cascade_api.agent.loop.should_eval", return_value=False),
    ):
        from cascade_api.agent.loop import run_agent
        text, messages = await run_agent(
            tenant_id="tenant-123",
            user_message="Hello",
            conversation_history=[],
            api_key="sk-test",
        )
        assert text == "Here's your status update."


@pytest.mark.asyncio
async def test_run_agent_traces_tool_calls():
    """Tool executions should create Langfuse spans."""
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"timezone": "America/New_York", "morning_hour": 7, "morning_minute": 0, "review_day": 1}
    ]

    # First response: tool use. Second response: text.
    tool_block = MagicMock()
    tool_block.type = "tool_use"
    tool_block.name = "recall"
    tool_block.id = "tool-123"
    tool_block.input = {"query": "churn signals"}

    tool_response = MagicMock()
    tool_response.content = [tool_block]
    tool_response.usage = MagicMock(input_tokens=100, output_tokens=50)
    tool_response.stop_reason = "tool_use"

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = "Based on your churn signals..."
    final_response = MagicMock()
    final_response.content = [text_block]
    final_response.usage = MagicMock(input_tokens=200, output_tokens=100)
    final_response.stop_reason = "end_turn"

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=[tool_response, final_response])

    mock_langfuse = MagicMock()
    mock_trace = MagicMock()
    mock_langfuse.trace.return_value = mock_trace
    mock_generation = MagicMock()
    mock_trace.generation.return_value = mock_generation
    mock_tool_span = MagicMock()
    mock_trace.span.return_value = mock_tool_span

    with (
        patch("cascade_api.agent.loop.get_supabase", return_value=mock_sb),
        patch("cascade_api.agent.loop.anthropic.AsyncAnthropic", return_value=mock_client),
        patch("cascade_api.agent.loop.build_system_prompt", new_callable=AsyncMock, return_value="system"),
        patch("cascade_api.agent.loop.get_langfuse", return_value=mock_langfuse),
        patch("cascade_api.agent.loop.should_eval", return_value=False),
        patch("cascade_api.agent.loop.execute_tool", new_callable=AsyncMock, return_value='{"memories": []}'),
    ):
        from cascade_api.agent.loop import run_agent
        text, _ = await run_agent(
            tenant_id="tenant-123",
            user_message="What are my churn signals?",
            conversation_history=[],
            api_key="sk-test",
        )

        assert text == "Based on your churn signals..."
        # 2 LLM calls = 2 generations
        assert mock_trace.generation.call_count == 2
        # 1 tool call = 1 span
        mock_trace.span.assert_called_once()
        span_kwargs = mock_trace.span.call_args[1]
        assert span_kwargs["name"] == "tool_recall"
        mock_tool_span.end.assert_called_once()
