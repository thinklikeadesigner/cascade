"""Anthropic LLM client — BYOK per-request."""

from __future__ import annotations

import anthropic


async def ask(
    system_prompt: str,
    user_message: str,
    api_key: str,
    user_id: str | None = None,
    context: str | None = None,
) -> str:
    client = anthropic.AsyncAnthropic(api_key=api_key)
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text
