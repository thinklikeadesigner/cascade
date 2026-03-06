"""Decay scoring — pure math utility, no external deps."""

from __future__ import annotations

from datetime import datetime, timezone


def calculate_decay(last_accessed: datetime, rate: float = 0.95) -> float:
    """Calculate memory decay score.

    Formula: rate ^ days_since_last_accessed
    Returns 1.0 if last_accessed is in the future.
    """
    now = datetime.now(timezone.utc)
    if last_accessed.tzinfo is None:
        last_accessed = last_accessed.replace(tzinfo=timezone.utc)
    delta = now - last_accessed
    days = max(delta.total_seconds() / 86400, 0)
    return round(rate**days, 4)
