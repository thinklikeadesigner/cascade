"""Tests for cascade_api.utils — is_user_active computation."""

from datetime import datetime, timezone, timedelta

from cascade_api.utils import is_user_active


def test_active_subscription_is_active():
    """A user with subscription_status='active' is always active."""
    tenant = {
        "subscription_status": "active",
        "completed_weekly_reviews": 5,
    }
    assert is_user_active(tenant) is True


def test_trial_under_two_reviews_is_active():
    """A user with fewer than 2 completed weekly reviews (still in trial) is active."""
    tenant = {
        "subscription_status": "none",
        "completed_weekly_reviews": 1,
    }
    assert is_user_active(tenant) is True


def test_trial_zero_reviews_is_active():
    """A brand new user with 0 reviews and no subscription is active (in trial)."""
    tenant = {
        "subscription_status": "none",
        "completed_weekly_reviews": 0,
    }
    assert is_user_active(tenant) is True


def test_trial_over_no_subscription_is_not_active():
    """A user with 2+ completed reviews and no active subscription is not active."""
    tenant = {
        "subscription_status": "none",
        "completed_weekly_reviews": 2,
    }
    assert is_user_active(tenant) is False


def test_trial_over_three_reviews_not_active():
    """A user with 3 completed reviews and no subscription is not active."""
    tenant = {
        "subscription_status": "none",
        "completed_weekly_reviews": 3,
    }
    assert is_user_active(tenant) is False


def test_canceled_subscription_trial_over_not_active():
    """A canceled subscriber with 2+ reviews is not active."""
    tenant = {
        "subscription_status": "canceled",
        "completed_weekly_reviews": 3,
    }
    assert is_user_active(tenant) is False


def test_past_due_within_grace_period_is_active():
    """A past_due user within the 7-day grace period is active."""
    recent = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
    tenant = {
        "subscription_status": "past_due",
        "past_due_since": recent,
        "completed_weekly_reviews": 5,
    }
    assert is_user_active(tenant) is True


def test_past_due_after_grace_period_is_not_active():
    """A past_due user after 7 days is not active."""
    old = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    tenant = {
        "subscription_status": "past_due",
        "past_due_since": old,
        "completed_weekly_reviews": 5,
    }
    assert is_user_active(tenant) is False


def test_past_due_with_z_suffix():
    """is_user_active handles past_due_since timestamps with Z suffix."""
    recent = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    tenant = {
        "subscription_status": "past_due",
        "past_due_since": recent,
        "completed_weekly_reviews": 5,
    }
    assert is_user_active(tenant) is True


def test_past_due_as_datetime_object():
    """is_user_active handles past_due_since as a datetime object (not just string)."""
    recent = datetime.now(timezone.utc) - timedelta(days=2)
    tenant = {
        "subscription_status": "past_due",
        "past_due_since": recent,
        "completed_weekly_reviews": 5,
    }
    assert is_user_active(tenant) is True


def test_missing_completed_weekly_reviews_defaults_to_zero():
    """A tenant without completed_weekly_reviews field is treated as 0 (in trial)."""
    tenant = {
        "subscription_status": "none",
    }
    assert is_user_active(tenant) is True
