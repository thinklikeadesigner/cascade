"""PostHog user event tracking."""

from __future__ import annotations

from functools import lru_cache
from posthog import Posthog

from cascade_api.config import settings


@lru_cache
def get_posthog() -> Posthog | None:
    if not settings.posthog_api_key:
        return None
    return Posthog(
        settings.posthog_api_key,
        host=settings.posthog_host,
    )


def track_event(
    user_id: str,
    event: str,
    properties: dict | None = None,
) -> None:
    """Track a user event. No-op if PostHog is not configured."""
    ph = get_posthog()
    if not ph:
        return
    ph.capture(
        distinct_id=user_id,
        event=event,
        properties=properties or {},
    )
