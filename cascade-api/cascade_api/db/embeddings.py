"""Embedding generation and semantic search for the memory system.

Uses Google's gemini-embedding-001 (768 dims) via the google-genai package.
Supabase's match_memories RPC handles the pgvector similarity search.
"""

from __future__ import annotations

from functools import lru_cache

import structlog
from google import genai
from supabase import Client as SupabaseClient

from cascade_api.config import settings

log = structlog.get_logger()

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMS = 768


@lru_cache
def _get_genai_client() -> genai.Client:
    return genai.Client(api_key=settings.gemini_api_key)


async def generate_embedding(text: str) -> list[float]:
    """Generate a 768-dim embedding for the given text."""
    client = _get_genai_client()
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
    )
    return list(response.embeddings[0].values)


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
