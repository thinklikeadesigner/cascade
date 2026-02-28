"""Agent loop — Claude tool-use conversation handler."""

from __future__ import annotations

import json

import structlog
import anthropic

from cascade_api.agent.tools import TOOLS, execute_tool
from cascade_api.agent.system_prompt import SYSTEM_PROMPT
from cascade_api.dependencies import get_supabase

log = structlog.get_logger()

# Model routing thresholds
SIMPLE_MODEL = "claude-haiku-4-5-20251001"
COMPLEX_MODEL = "claude-sonnet-4-5-20250514"
MAX_TOOL_ROUNDS = 10


async def run_agent(
    tenant_id: str,
    user_message: str,
    conversation_history: list[dict],
    api_key: str,
    is_scheduled: bool = False,
    scheduled_context: str | None = None,
) -> tuple[str, list[dict]]:
    """Run the agent loop. Returns (response_text, updated_history).

    For scheduled messages, pass is_scheduled=True and scheduled_context
    with instructions. These go into a system prompt addendum, not the
    user message — avoids the [SCHEDULED: ...] prefix hack leaking into
    Claude's reasoning or response.
    """

    client = anthropic.AsyncAnthropic(api_key=api_key)
    supabase = get_supabase()

    # Build system prompt — add scheduled context if present
    system = SYSTEM_PROMPT
    if scheduled_context:
        system = f"{SYSTEM_PROMPT}\n\n## Current Task\n\n{scheduled_context}"

    # Build messages: history + new user message
    messages = list(conversation_history)
    messages.append({"role": "user", "content": user_message})

    # Pick model — default Sonnet, Haiku only for scheduled/trivial
    model = _pick_model(user_message, is_scheduled=is_scheduled)

    for _ in range(MAX_TOOL_ROUNDS):
        response = await client.messages.create(
            model=model,
            max_tokens=1024,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            tools=TOOLS,
            messages=messages,
        )

        # Check if Claude wants to use tools
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            # Claude produced a final text response
            text = "".join(b.text for b in response.content if b.type == "text")
            messages.append({"role": "assistant", "content": response.content})
            return text, messages

        # Execute tool calls and feed results back
        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tool_block in tool_use_blocks:
            try:
                result = await execute_tool(
                    tool_block.name, tool_block.input, supabase, tenant_id,
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": result,
                })
            except Exception as e:
                log.error("tool.failed", tool=tool_block.name, error=str(e))
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": json.dumps({"error": str(e)}),
                    "is_error": True,
                })

        messages.append({"role": "user", "content": tool_results})

        # Upgrade to complex model if tool use is getting multi-step
        if len(tool_use_blocks) > 1:
            model = COMPLEX_MODEL

    # Safety: max rounds exceeded
    return "I hit my reasoning limit. Can you try rephrasing?", messages


def _pick_model(message: str, is_scheduled: bool = False) -> str:
    """Route to cheap or expensive model based on context.

    Default to Sonnet. Haiku only for scheduled messages and trivially short
    factual queries. The per-message cost difference is fractions of a cent —
    not worth risking bad responses on misrouted complex messages.
    """
    if is_scheduled:
        return SIMPLE_MODEL

    # Only use Haiku for very short, single-intent messages
    msg_lower = message.strip().lower()
    if len(msg_lower) < 20 and msg_lower in (
        "status", "tasks", "today", "review",
    ):
        return SIMPLE_MODEL

    return COMPLEX_MODEL
