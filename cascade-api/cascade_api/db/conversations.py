"""CRUD helpers for the conversations table — raw WhatsApp message logging."""

from __future__ import annotations

import json

import structlog
from supabase import Client as SupabaseClient

from cascade_api.dependencies import get_anthropic

log = structlog.get_logger()


async def store_conversation(
    supabase: SupabaseClient,
    tenant_id: str,
    raw_text: str,
    source: str = "whatsapp",
) -> dict:
    """Store a raw conversation message."""
    row = {
        "tenant_id": tenant_id,
        "raw_text": raw_text,
        "source": source,
    }
    result = supabase.table("conversations").insert(row).execute()
    log.info("conversation.stored", tenant_id=tenant_id, source=source)
    return result.data[0]


async def get_conversations(
    supabase: SupabaseClient,
    tenant_id: str,
    limit: int = 50,
    source: str | None = None,
) -> list[dict]:
    """Return recent conversations for a tenant."""
    query = (
        supabase.table("conversations")
        .select("*")
        .eq("tenant_id", tenant_id)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if source:
        query = query.eq("source", source)
    result = query.execute()
    return result.data


ENTITY_EXTRACTION_PROMPT = """\
Extract structured entities from this WhatsApp conversation message. \
Identify any of: people, companies, skills, tasks, metrics, dates, goals.

Return ONLY a JSON object — no markdown, no explanation:
{{"people": [], "companies": [], "skills": [], "tasks": [], "metrics": [], "dates": [], "goals": []}}

Only include categories that have matches. Empty categories can be omitted.

Message: {text}
"""


async def extract_entities(
    supabase: SupabaseClient,
    conversation_id: int,
    raw_text: str,
    api_key: str,
) -> dict:
    """Run lightweight entity extraction on a stored conversation and update the row.

    Uses Claude Haiku for speed/cost. Updates extracted_entities JSONB column.
    """
    client = get_anthropic(api_key)
    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": ENTITY_EXTRACTION_PROMPT.format(text=raw_text),
            }
        ],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]
    entities: dict = json.loads(raw)

    result = (
        supabase.table("conversations")
        .update({"extracted_entities": entities})
        .eq("id", conversation_id)
        .execute()
    )
    log.info(
        "conversation.entities_extracted",
        id=conversation_id,
        entity_types=list(entities.keys()),
    )
    return result.data[0]


async def store_and_extract(
    supabase: SupabaseClient,
    tenant_id: str,
    raw_text: str,
    api_key: str,
    source: str = "whatsapp",
) -> dict:
    """Convenience: store a conversation and run entity extraction in one call."""
    conversation = await store_conversation(supabase, tenant_id, raw_text, source)
    return await extract_entities(
        supabase, conversation["id"], raw_text, api_key
    )
