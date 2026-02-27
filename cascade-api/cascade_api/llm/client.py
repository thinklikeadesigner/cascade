"""Anthropic LLM client — BYOK per-request."""

from __future__ import annotations

from cascade_api.observability.langfuse_client import traced_ask


async def ask(
    system_prompt: str,
    user_message: str,
    api_key: str,
    user_id: str | None = None,
    context: str | None = None,
) -> str:
    return await traced_ask(
        system_prompt=system_prompt,
        user_message=user_message,
        api_key=api_key,
        user_id=user_id,
        context=context,
    )
