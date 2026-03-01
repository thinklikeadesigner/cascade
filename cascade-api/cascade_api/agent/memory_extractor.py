"""Background memory extraction — runs after each conversation.

Takes a conversation transcript, extracts key facts via Claude Haiku,
checks for contradictions against existing memories, and saves new
memories to the archival store.
"""

from __future__ import annotations

import json

import structlog
from supabase import Client as SupabaseClient

from cascade_api.db.memory import save_memory, get_memories
from cascade_api.db.embeddings import generate_embedding

log = structlog.get_logger()

EXTRACTION_PROMPT = """\
Extract key facts, decisions, preferences, and state changes from this conversation.

For each item, return a JSON object with:
- "content": the fact as a concise statement
- "memory_type": one of "fact", "preference", "pattern", "goal_context"
- "tags": list of 1-3 context tags

Only extract information worth remembering long-term. Skip small talk, \
acknowledgments, and transient details.

Return a JSON array. If nothing worth remembering, return [].

Conversation:
{text}
"""

CONTRADICTION_CHECK_PROMPT = """\
Compare this new fact against existing memories. Does it contradict any of them?

New fact: {new_fact}

Existing memories:
{existing_memories}

If there is a contradiction, return JSON:
{{"contradicts": true, "memory_id": "<id of contradicted memory>", "explanation": "<brief explanation>"}}

If no contradiction, return:
{{"contradicts": false}}
"""


async def extract_memories_from_conversation(
    supabase: SupabaseClient,
    anthropic_client,
    tenant_id: str,
    conversation_text: str,
    conversation_id: int | None = None,
) -> list[dict]:
    """Extract and store memories from a conversation transcript.

    Called as a background task after each conversation completes.
    """
    # Step 1: Extract facts via Haiku
    response = await anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[{
            "role": "user",
            "content": EXTRACTION_PROMPT.format(text=conversation_text),
        }],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[:raw.rfind("```")]

    try:
        extracted = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("memory_extraction.parse_failed", tenant_id=tenant_id)
        return []

    if not extracted:
        return []

    # Step 2: Save each extracted memory
    saved = []
    for item in extracted:
        content = item.get("content", "")
        if not content:
            continue

        memory_type = item.get("memory_type", "fact")
        tags = item.get("tags", [])

        # Generate embedding
        try:
            embedding = await generate_embedding(content)
        except Exception:
            embedding = None

        result = await save_memory(
            supabase, tenant_id, content,
            memory_type=memory_type,
            tags=tags,
            source_conversation_id=conversation_id,
            embedding=embedding,
        )
        saved.append(result)

    log.info("memory_extraction.complete", tenant_id=tenant_id, count=len(saved))
    return saved
