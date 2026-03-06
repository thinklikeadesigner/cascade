"""Tests for LLM-as-judge eval scoring."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.mark.asyncio
async def test_score_trace_calls_haiku_and_posts_scores():
    """score_trace should call Haiku with the judge prompt and post scores to Langfuse."""
    judge_response = json.dumps({
        "signal_extraction": {"score": 0.8, "reason": "Correctly parsed churn and metric"},
        "memory_grounding": {"score": 0.9, "reason": "Referenced 2 specific signals"},
        "briefing_quality": {"score": None, "reason": "Not a briefing"},
        "tool_efficiency": {"score": 0.7, "reason": "One redundant recall call"},
    })

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=judge_response)]
    mock_response.usage = MagicMock(input_tokens=500, output_tokens=200)

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    mock_langfuse = MagicMock()

    with (
        patch("cascade_api.observability.evals.anthropic.AsyncAnthropic", return_value=mock_client),
        patch("cascade_api.observability.evals.get_langfuse", return_value=mock_langfuse),
    ):
        from cascade_api.observability.evals import score_trace

        await score_trace(
            trace_id="trace-abc",
            user_message="3 users asked for CSV export, one churned citing pricing",
            agent_response="Got it. Stored 3 signals: feature_request, churn_signal, metric.",
            tool_calls=[{"tool": "ingest_signal", "input": {"raw_text": "..."}, "output": "..."}],
            is_scheduled=False,
            api_key="sk-test",
        )

        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-haiku-4-5-20251001"

        # 3 non-null scores posted
        assert mock_langfuse.score.call_count == 3
        score_names = [c[1]["name"] for c in mock_langfuse.score.call_args_list]
        assert "signal_extraction" in score_names
        assert "memory_grounding" in score_names
        assert "tool_efficiency" in score_names


@pytest.mark.asyncio
async def test_score_trace_handles_malformed_json():
    """score_trace should not crash on malformed judge output."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not valid json")]
    mock_response.usage = MagicMock(input_tokens=500, output_tokens=50)

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with (
        patch("cascade_api.observability.evals.anthropic.AsyncAnthropic", return_value=mock_client),
        patch("cascade_api.observability.evals.get_langfuse", return_value=MagicMock()),
    ):
        from cascade_api.observability.evals import score_trace

        await score_trace(
            trace_id="trace-abc", user_message="test",
            agent_response="test response", tool_calls=[],
            is_scheduled=False, api_key="sk-test",
        )


@pytest.mark.asyncio
async def test_score_trace_noop_without_langfuse():
    """score_trace should do nothing if Langfuse is not configured."""
    with patch("cascade_api.observability.evals.get_langfuse", return_value=None):
        from cascade_api.observability.evals import score_trace

        await score_trace(
            trace_id="trace-abc", user_message="test",
            agent_response="test", tool_calls=[],
            is_scheduled=False, api_key="sk-test",
        )


def test_build_judge_prompt_includes_all_criteria():
    """The judge prompt should mention all 4 eval criteria."""
    from cascade_api.observability.evals import build_judge_prompt

    prompt = build_judge_prompt(
        user_message="3 users asked for CSV",
        agent_response="Stored 3 signals.",
        tool_calls=[],
        is_scheduled=False,
    )

    assert "signal_extraction" in prompt
    assert "memory_grounding" in prompt
    assert "briefing_quality" in prompt
    assert "tool_efficiency" in prompt


def test_build_judge_prompt_marks_briefing_when_scheduled():
    """When is_scheduled=True, the judge prompt should indicate briefing scoring applies."""
    from cascade_api.observability.evals import build_judge_prompt

    prompt = build_judge_prompt(
        user_message="Generate briefing",
        agent_response="Weekly Intel...",
        tool_calls=[],
        is_scheduled=True,
    )

    assert "This is a scheduled briefing" in prompt
