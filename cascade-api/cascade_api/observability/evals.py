"""LLM-as-judge eval scoring for Cascade agent traces."""

from __future__ import annotations

import json

import anthropic
import structlog

from cascade_api.observability.langfuse_client import get_langfuse

log = structlog.get_logger()

JUDGE_MODEL = "claude-haiku-4-5-20251001"


def build_judge_prompt(
    user_message: str,
    agent_response: str,
    tool_calls: list[dict],
    is_scheduled: bool,
) -> str:
    """Build the judge prompt for scoring agent output."""
    tool_summary = ""
    if tool_calls:
        tool_lines = []
        for tc in tool_calls:
            tool_lines.append(f"- {tc['tool']}({json.dumps(tc.get('input', {}), default=str)[:200]})")
        tool_summary = "\n".join(tool_lines)
    else:
        tool_summary = "(no tool calls)"

    briefing_note = "This is a scheduled briefing — score briefing_quality." if is_scheduled else "This is NOT a scheduled briefing — set briefing_quality score to null."

    return f"""You are an eval judge for Cascade, a strategic co-pilot for founders. Score the agent's response on 4 criteria.

{briefing_note}

## User Message
{user_message}

## Agent Response
{agent_response}

## Tool Calls Made
{tool_summary}

## Scoring Criteria (0.0 to 1.0, or null if not applicable)

1. **signal_extraction**: Did the agent correctly identify and categorize signals from the user's input? Were the right signal types assigned (user_signal, churn_signal, feature_request, market_move, metric, decision)? Was anything missed or miscategorized? Score null if the user didn't provide business data to extract.

2. **memory_grounding**: Did the response reference specific signals, memories, or past data rather than giving generic advice? 1.0 = every claim grounded in specific data. 0.0 = pure generic advice with no data references.

3. **briefing_quality**: (Only for scheduled briefings, null otherwise) Did the briefing surface patterns across signals rather than just listing them? Did it connect signals to hypotheses? Did it identify actionable insights?

4. **tool_efficiency**: Were the tool calls necessary and sufficient? Penalize: redundant recalls, calling tools whose data wasn't used, missing obvious tool calls (e.g., not using recall before answering a question about past data). Score null if no tool calls were expected.

## Response Format

Return ONLY valid JSON, no other text:

{{"signal_extraction": {{"score": 0.8, "reason": "brief explanation"}}, "memory_grounding": {{"score": 0.9, "reason": "brief explanation"}}, "briefing_quality": {{"score": null, "reason": "not a briefing"}}, "tool_efficiency": {{"score": 0.7, "reason": "brief explanation"}}}}"""


async def score_trace(
    trace_id: str,
    user_message: str,
    agent_response: str,
    tool_calls: list[dict],
    is_scheduled: bool,
    api_key: str,
) -> None:
    """Score an agent trace using LLM-as-judge and post scores to Langfuse."""
    lf = get_langfuse()
    if not lf:
        return

    try:
        prompt = build_judge_prompt(user_message, agent_response, tool_calls, is_scheduled)

        client = anthropic.AsyncAnthropic(api_key=api_key)
        response = await client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text
        scores = json.loads(raw)

        for criterion, data in scores.items():
            if not isinstance(data, dict):
                continue
            score_val = data.get("score")
            if score_val is None:
                continue
            lf.score(
                trace_id=trace_id,
                name=criterion,
                value=float(score_val),
                comment=data.get("reason", ""),
            )

        lf.flush()
        log.info("langfuse.eval_completed", trace_id=trace_id, criteria_scored=len(scores))

    except json.JSONDecodeError:
        log.warning("langfuse.eval_json_parse_failed", trace_id=trace_id)
    except Exception as e:
        log.warning("langfuse.eval_failed", trace_id=trace_id, error=str(e))
