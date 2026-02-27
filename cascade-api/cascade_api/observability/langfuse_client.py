"""Langfuse tracing wrapper for Claude API calls."""

from __future__ import annotations

import anthropic
import structlog
from functools import lru_cache
from langfuse import Langfuse

from cascade_api.config import settings

log = structlog.get_logger()

MODEL = "claude-sonnet-4-5-20250514"
MAX_TOKENS = 4096


@lru_cache
def get_langfuse() -> Langfuse | None:
    if not settings.langfuse_public_key:
        return None
    return Langfuse(
        public_key=settings.langfuse_public_key,
        secret_key=settings.langfuse_secret_key,
        host=settings.langfuse_host,
    )


async def traced_ask(
    system_prompt: str,
    user_message: str,
    api_key: str,
    user_id: str | None = None,
    context: str | None = None,
    model: str = MODEL,
    max_tokens: int = MAX_TOKENS,
) -> str:
    """Call Claude with Langfuse tracing. Falls back to untraced if Langfuse is not configured."""
    key = api_key or settings.anthropic_api_key
    client = anthropic.AsyncAnthropic(api_key=key)
    lf = get_langfuse()

    trace = None
    generation = None

    if lf:
        trace = lf.trace(
            name=context or "claude_call",
            user_id=user_id,
            metadata={"context": context},
        )
        generation = trace.generation(
            name="claude_completion",
            model=model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

    response = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    result = response.content[0].text

    if generation:
        generation.end(
            output=result,
            usage={
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens,
            },
        )

    if lf:
        lf.flush()

    return result
