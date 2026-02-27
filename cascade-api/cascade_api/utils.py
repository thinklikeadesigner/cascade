"""Shared utilities for cascade_api."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta


def is_user_active(tenant: dict) -> bool:
    """Compute whether a user is active from subscription and trial state.

    A user is active if:
    - They have an active subscription, OR
    - They've completed fewer than 2 weekly reviews (still in trial), OR
    - They're past_due but within the 7-day grace period.
    """
    if tenant.get("subscription_status") == "active":
        return True
    if tenant.get("completed_weekly_reviews", 0) < 2:
        return True
    if tenant.get("subscription_status") == "past_due":
        past_due_since = tenant.get("past_due_since")
        if past_due_since:
            if isinstance(past_due_since, str):
                past_due_since = datetime.fromisoformat(
                    past_due_since.replace("Z", "+00:00")
                )
            if past_due_since + timedelta(days=7) > datetime.now(timezone.utc):
                return True
    return False
