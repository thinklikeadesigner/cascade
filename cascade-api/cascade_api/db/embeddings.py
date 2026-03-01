"""Embedding generation and semantic search for the memory system.

Uses OpenAI's text-embedding-3-small (1536 dims) via the openai package.
Supabase's match_memories RPC handles the pgvector similarity search.
"""

from __future__ import annotations

from functools import lru_cache

import structlog
from openai import AsyncOpenAI
from supabase import Client as SupabaseClient

from cascade_api.config import settings

log = structlog.get_logger()

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536


@lru_cache
def _get_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.openai_api_key)


async def generate_embedding(text: str) -> list[float]:
    """Generate a 1536-dim embedding for the given text."""
    client = _get_openai_client()
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


async def semantic_search(
    supabase: SupabaseClient,
    tenant_id: str,
    query: str,
    match_count: int = 5,
    threshold: float = 0.5,
) -> list[dict]:
    """Hybrid semantic search over archival memories.

    Calls the match_memories Postgres function (pgvector cosine similarity).
    Results are ranked by similarity * decay_score * confidence.
    """
    embedding = await generate_embedding(query)

    results = supabase.rpc(
        "match_memories",
        {
            "query_embedding": embedding,
            "match_tenant_id": tenant_id,
            "match_count": match_count,
            "match_threshold": threshold,
        },
    ).execute()

    return results.data
