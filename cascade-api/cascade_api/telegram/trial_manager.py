"""Trial management — cycle-based (2 completed weekly reviews).

The trial model is engagement-based, not calendar-based.
A user's trial ends after completing 2 weekly review cycles.
The Sunday review cron increments completed_weekly_reviews.
"""

from __future__ import annotations

import structlog

log = structlog.get_logger()


def get_trial_actions(tenants: list[dict]) -> list[dict]:
    """Determine which tenants need a payment nudge.

    A tenant needs a nudge when they've completed 2+ weekly reviews
    and don't have an active subscription.
    """
    actions = []

    for tenant in tenants:
        if tenant.get("subscription_status") == "active":
            continue  # Paying user, skip

        reviews = tenant.get("completed_weekly_reviews", 0)
        if reviews >= 2:
            actions.append({"tenant": tenant, "action": "payment_needed"})

    return actions
