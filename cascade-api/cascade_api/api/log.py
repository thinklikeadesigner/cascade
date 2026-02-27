"""POST /api/log — parse natural language into tracker entries."""

from __future__ import annotations

from datetime import date

import structlog
from fastapi import HTTPException
from pydantic import BaseModel

from cascade_api.api.router import api_router
from cascade_api.db.client import get_supabase
from cascade_api.db import tracker
from cascade_api.dependencies import get_anthropic

log = structlog.get_logger()

PARSE_SYSTEM_PROMPT = """\
You are a structured data parser for a goal-tracking system.
Given a user's natural-language progress note, extract structured fields.

Return ONLY valid JSON with these possible keys (omit keys with no data):
- date (YYYY-MM-DD, default to today if not specified)
- outreach_sent (integer)
- conversations (integer)
- new_clients (integer)
- features_shipped (integer)
- content_published (integer)
- mrr (number)
- energy_level (1-5 integer)
- notes (string — anything that doesn't map to a numeric field)

Example input: "sent 5 DMs on linkt, had a great call with a PM from Stripe, energy was high"
Example output: {"outreach_sent": 5, "conversations": 1, "energy_level": 4, "notes": "call with PM from Stripe"}
"""


class LogRequest(BaseModel):
    tenant_id: str
    text: str
    source: str = "whatsapp"


class LogResponse(BaseModel):
    parsed: dict
    conversation_id: int


@api_router.post("/api/log", response_model=LogResponse)
async def log_progress(req: LogRequest):
    supabase = get_supabase()

    # Parse natural language with Claude Haiku
    try:
        client = get_anthropic()
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=PARSE_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Today is {date.today().isoformat()}. Parse this: {req.text}",
                }
            ],
        )
        import json

        raw_text = message.content[0].text
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        log.error("parse.json_failed", raw=raw_text)
        raise HTTPException(status_code=422, detail="Failed to parse progress text into structured data")
    except Exception as exc:
        log.error("parse.failed", error=str(exc))
        raise HTTPException(status_code=502, detail="LLM parsing failed")

    # Extract date, default to today
    entry_date = parsed.pop("date", date.today().isoformat())

    # Upsert tracker entry
    entry = await tracker.log_entry(supabase, req.tenant_id, entry_date, parsed)

    # Store raw text in conversations table
    conv_result = (
        supabase.table("conversations")
        .insert({
            "tenant_id": req.tenant_id,
            "raw_text": req.text,
            "source": req.source,
            "extracted_entities": parsed,
        })
        .execute()
    )
    conversation_id = conv_result.data[0]["id"]

    log.info(
        "log.processed",
        tenant_id=req.tenant_id,
        date=entry_date,
        conversation_id=conversation_id,
    )

    return LogResponse(parsed=entry, conversation_id=conversation_id)
