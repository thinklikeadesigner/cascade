"""Memory decay scoring.

Memories decay in retrieval priority based on time since last access.
Formula: decay_score = base_score * (0.95 ^ days_since_last_access)

This runs as part of the daily cron to update decay scores in batch.
Memories are never auto-deleted — they just rank lower in retrieval.
"""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from supabase import Client as SupabaseClient

log = structlog.get_logger()

DECAY_RATE = 0.95  # Daily decay multiplier


def calculate_decay(
    last_accessed: datetime,
    base_score: float = 1.0,
) -> float:
    """Calculate decay score based on days since last access."""
    now = datetime.now(timezone.utc)
    if last_accessed.tzinfo is None:
        last_accessed = last_accessed.replace(tzinfo=timezone.utc)
    days = (now - last_accessed).total_seconds() / 86400
    return base_score * (DECAY_RATE ** days)


async def update_decay_scores(supabase: SupabaseClient) -> int:
    """Batch-update decay scores for all active memories via single SQL statement.

    Called by daily cron. Computes decay in Postgres to avoid loading all
    memories into Python and to prevent cross-tenant data handling.
    """
    result = supabase.rpc("update_memory_decay_scores", {}).execute()
    updated = result.data if isinstance(result.data, int) else 0
    log.info("memory_decay.updated", changed=updated)
    return updated
