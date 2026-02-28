"""Conversation history storage for the agent loop."""

from __future__ import annotations

import json

import structlog
from supabase import Client as SupabaseClient

log = structlog.get_logger()

MAX_HISTORY_MESSAGES = 20  # Keep last N messages for context


async def get_history(
    supabase: SupabaseClient,
    tenant_id: str,
) -> list[dict]:
    """Retrieve recent conversation history for the agent."""
    result = (
        supabase.table("conversations")
        .select("role, content")
        .eq("tenant_id", tenant_id)
        .eq("source", "agent_history")
        .order("created_at", desc=True)
        .limit(MAX_HISTORY_MESSAGES)
        .execute()
    )
    # Reverse to chronological order
    rows = list(reversed(result.data))
    return [{"role": row["role"], "content": row["content"]} for row in rows]


async def save_turn(
    supabase: SupabaseClient,
    tenant_id: str,
    role: str,
    content: str,
) -> None:
    """Save a single conversation turn."""
    supabase.table("conversations").insert({
        "tenant_id": tenant_id,
        "role": role,
        "raw_text": content if isinstance(content, str) else json.dumps(content),
        "content": content,
        "source": "agent_history",
    }).execute()
