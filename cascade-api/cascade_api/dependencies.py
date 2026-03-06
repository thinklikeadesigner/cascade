from __future__ import annotations

from functools import lru_cache

import anthropic
from supabase import create_client, Client as SupabaseClient

from cascade_api.config import settings


@lru_cache
def get_supabase() -> SupabaseClient:
    """Singleton Supabase client using service role key (bypasses RLS)."""
    return create_client(settings.supabase_url, settings.supabase_service_key)


def get_anthropic(api_key: str | None = None) -> anthropic.AsyncAnthropic:
    """Anthropic client — BYOK per-request or fallback to server key."""
    key = api_key or settings.anthropic_api_key
    return anthropic.AsyncAnthropic(api_key=key)


@lru_cache
def get_memory_client():
    """Singleton MemoryClient wired to Supabase + Gemini + Claude Haiku."""
    from cascade_api.memory import MemoryClient
    from cascade_api.memory.stores.supabase import SupabaseStore
    from cascade_api.memory.embedders.gemini import GeminiEmbedder
    from cascade_api.memory.extractors.anthropic import AnthropicExtractor

    store = SupabaseStore(get_supabase())
    embedder = GeminiEmbedder(api_key=settings.gemini_api_key)
    extractor = AnthropicExtractor(client=get_anthropic())
    return MemoryClient(
        store=store,
        embedder=embedder,
        extractor=extractor,
        core_memory_limit=3000,
        decay_rate=0.95,
    )
