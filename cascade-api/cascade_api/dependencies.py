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
