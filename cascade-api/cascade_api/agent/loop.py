"""Agent loop — Claude tool-use conversation handler."""

from __future__ import annotations

import json

import structlog
import anthropic

from cascade_api.agent.tools import TOOLS, execute_tool
from cascade_api.agent.system_prompt import SYSTEM_PROMPT, build_system_prompt
from cascade_api.dependencies import get_supabase
from cascade_api.observability.langfuse_client import get_langfuse, should_eval, flush_langfuse

log = structlog.get_logger()

# Model routing thresholds
SIMPLE_MODEL = "claude-haiku-4-5-20251001"
COMPLEX_MODEL = "claude-sonnet-4-6"
MAX_TOOL_ROUNDS = 10


async def run_agent(
    tenant_id: str,
    user_message: str,
    conversation_history: list[dict],
    api_key: str,
    is_scheduled: bool = False,
    scheduled_context: str | None = None,
    scheduled_model: str | None = None,
) -> tuple[str, list[dict]]:
    """Run the agent loop with optional Langfuse tracing.

    Returns (response_text, updated_history).
    """
    client = anthropic.AsyncAnthropic(api_key=api_key)
    supabase = get_supabase()
    lf = get_langfuse()

    # Build system prompt
    tenant_result = supabase.table("tenants").select(
        "timezone, morning_hour, morning_minute, review_day"
    ).eq("id", tenant_id).execute()
    tenant = tenant_result.data[0] if tenant_result.data else {}

    system = await build_system_prompt(
        supabase, tenant_id, tenant,
        scheduled_context=scheduled_context,
    )

    messages = list(conversation_history)
    messages.append({"role": "user", "content": user_message})

    model = scheduled_model if scheduled_model else _pick_model(user_message, is_scheduled=is_scheduled)

    # --- Langfuse trace (root) ---
    trace = None
    if lf:
        try:
            trace = lf.trace(
                name="agent_loop",
                user_id=tenant_id,
                metadata={
                    "tenant_id": tenant_id,
                    "is_scheduled": is_scheduled,
                    "initial_model": model,
                },
                input=user_message,
            )
        except Exception as e:
            log.warning("langfuse.trace_failed", error=str(e))
            trace = None

    tool_calls_log = []  # collect for evals

    for round_num in range(MAX_TOOL_ROUNDS):
        # --- Langfuse generation span ---
        generation = None
        if trace:
            try:
                generation = trace.generation(
                    name=f"llm_call_{round_num}",
                    model=model,
                    input=messages,
                )
            except Exception:
                generation = None

        response = await client.messages.create(
            model=model,
            max_tokens=1024,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            tools=[*TOOLS, {"type": "web_search_20250305", "name": "web_search"}],
            messages=messages,
        )

        # End generation span
        if generation:
            try:
                generation.end(
                    output=response.content,
                    usage={
                        "input": response.usage.input_tokens,
                        "output": response.usage.output_tokens,
                    },
                    metadata={"stop_reason": response.stop_reason},
                )
            except Exception:
                pass

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_use_blocks:
            text = "".join(b.text for b in response.content if b.type == "text")
            messages.append({"role": "assistant", "content": response.content})

            # --- Finalize trace ---
            if trace:
                try:
                    trace.update(output=text)
                except Exception:
                    pass

            # --- Trigger evals (fire-and-forget) ---
            if trace and should_eval(user_message, is_scheduled):
                try:
                    import asyncio
                    from cascade_api.observability.evals import score_trace
                    asyncio.create_task(score_trace(
                        trace_id=trace.id,
                        user_message=user_message,
                        agent_response=text,
                        tool_calls=tool_calls_log,
                        is_scheduled=is_scheduled,
                        api_key=api_key,
                    ))
                except Exception as e:
                    log.warning("langfuse.eval_trigger_failed", error=str(e))

            if lf:
                try:
                    lf.flush()
                except Exception:
                    pass

            return text, messages

        # Execute tool calls
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for tool_block in tool_use_blocks:
            # --- Langfuse tool span ---
            tool_span = None
            if trace:
                try:
                    tool_span = trace.span(
                        name=f"tool_{tool_block.name}",
                        input=tool_block.input,
                    )
                except Exception:
                    tool_span = None

            try:
                result = await execute_tool(
                    tool_block.name, tool_block.input, supabase, tenant_id,
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": result,
                })
                tool_calls_log.append({
                    "tool": tool_block.name,
                    "input": tool_block.input,
                    "output": result,
                })

                if tool_span:
                    try:
                        tool_span.end(output=result)
                    except Exception:
                        pass

            except Exception as e:
                log.error("tool.failed", tool=tool_block.name, error=str(e))
                error_result = json.dumps({"error": str(e)})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_block.id,
                    "content": error_result,
                    "is_error": True,
                })

                if tool_span:
                    try:
                        tool_span.end(output=error_result, level="ERROR")
                    except Exception:
                        pass

        messages.append({"role": "user", "content": tool_results})

        if len(tool_use_blocks) > 1:
            model = COMPLEX_MODEL
            if trace:
                try:
                    trace.event(name="model_upgrade", metadata={"new_model": COMPLEX_MODEL})
                except Exception:
                    pass

    # Safety: max rounds exceeded
    if trace:
        try:
            trace.update(output="max_rounds_exceeded", metadata={"error": True})
            lf.flush()
        except Exception:
            pass

    return "I hit my reasoning limit. Can you try rephrasing?", messages


def _pick_model(message: str, is_scheduled: bool = False) -> str:
    """Route to cheap or expensive model based on context."""
    if is_scheduled:
        return SIMPLE_MODEL
    msg_lower = message.strip().lower()
    if len(msg_lower) < 20 and msg_lower in ("status", "tasks", "today", "review"):
        return SIMPLE_MODEL
    return COMPLEX_MODEL
