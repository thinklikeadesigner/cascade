"""Tests for cascade_api.telegram.trial_manager — cycle-based trial actions."""

from cascade_api.telegram.trial_manager import get_trial_actions


def test_reviews_ge_2_no_subscription_gets_payment_needed():
    """Tenant with 2+ reviews and no active subscription needs payment."""
    tenants = [{
        "id": "t-1",
        "completed_weekly_reviews": 2,
        "subscription_status": "none",
    }]

    actions = get_trial_actions(tenants)
    assert len(actions) == 1
    assert actions[0]["action"] == "payment_needed"
    assert actions[0]["tenant"]["id"] == "t-1"


def test_reviews_ge_2_high_count_gets_payment_needed():
    """Tenant with many reviews and no subscription still gets payment_needed."""
    tenants = [{
        "id": "t-2",
        "completed_weekly_reviews": 5,
        "subscription_status": "none",
    }]

    actions = get_trial_actions(tenants)
    assert len(actions) == 1
    assert actions[0]["action"] == "payment_needed"


def test_reviews_lt_2_no_action():
    """Tenant still in trial (< 2 reviews) gets no action."""
    tenants = [{
        "id": "t-3",
        "completed_weekly_reviews": 1,
        "subscription_status": "none",
    }]

    actions = get_trial_actions(tenants)
    assert len(actions) == 0


def test_zero_reviews_no_action():
    """Brand new tenant with 0 reviews gets no action."""
    tenants = [{
        "id": "t-4",
        "completed_weekly_reviews": 0,
        "subscription_status": "none",
    }]

    actions = get_trial_actions(tenants)
    assert len(actions) == 0


def test_active_subscription_skipped():
    """Tenant with active subscription is skipped regardless of review count."""
    tenants = [{
        "id": "t-5",
        "completed_weekly_reviews": 5,
        "subscription_status": "active",
    }]

    actions = get_trial_actions(tenants)
    assert len(actions) == 0


def test_multiple_tenants_mixed():
    """Multiple tenants: only those with reviews >= 2 and no active sub get flagged."""
    tenants = [
        {"id": "t-a", "completed_weekly_reviews": 3, "subscription_status": "none"},
        {"id": "t-b", "completed_weekly_reviews": 1, "subscription_status": "none"},
        {"id": "t-c", "completed_weekly_reviews": 4, "subscription_status": "active"},
    ]

    actions = get_trial_actions(tenants)
    assert len(actions) == 1
    assert actions[0]["tenant"]["id"] == "t-a"
