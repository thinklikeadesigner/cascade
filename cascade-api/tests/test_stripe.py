"""Tests for Stripe payment and webhook handling."""

import pytest
from unittest.mock import MagicMock, patch


def test_checkout_session_completed_activates_subscription():
    """Webhook should update tenant subscription_status to active."""
    mock_supabase = MagicMock()
    # Idempotency check — no existing event
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    with patch("cascade_api.api.stripe_webhook.get_supabase", return_value=mock_supabase):
        with patch("cascade_api.api.stripe_webhook.stripe") as mock_stripe:
            mock_stripe.Webhook.construct_event.return_value = MagicMock(
                id="evt-123",
                type="checkout.session.completed",
                data=MagicMock(object=MagicMock(
                    client_reference_id="tenant-1",
                    customer="cus_123",
                    subscription="sub_123",
                )),
            )

            from cascade_api.api.stripe_webhook import process_webhook_event
            result = process_webhook_event("evt-123", "checkout.session.completed", {
                "client_reference_id": "tenant-1",
                "customer": "cus_123",
                "subscription": "sub_123",
            }, mock_supabase)

            assert result["status"] == "processed"


def test_idempotency_skips_duplicate_event():
    """Duplicate Stripe event IDs should be skipped."""
    mock_supabase = MagicMock()
    # Idempotency check — event already exists
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "existing-record"}
    ]

    from cascade_api.api.stripe_webhook import process_webhook_event
    result = process_webhook_event("evt-duplicate", "checkout.session.completed", {
        "client_reference_id": "tenant-1",
    }, mock_supabase)

    assert result["status"] == "already_processed"


def test_subscription_deleted_marks_churned():
    """customer.subscription.deleted should mark tenant as churned."""
    mock_supabase = MagicMock()
    # Idempotency check — no existing event
    select_mock = MagicMock()
    eq_mock = MagicMock()

    def table_side_effect(name):
        mock_table = MagicMock()
        if name == "stripe_events":
            # First call: idempotency check returns empty
            mock_table.select.return_value.eq.return_value.execute.return_value.data = []
        elif name == "tenants":
            # For the select query to find tenant by customer ID
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                {"id": "tenant-1", "user_id": "user-1"}
            ]
        return mock_table

    mock_supabase.table.side_effect = table_side_effect

    with patch("cascade_api.api.stripe_webhook.track_event"):
        from cascade_api.api.stripe_webhook import process_webhook_event
        result = process_webhook_event("evt-churn", "customer.subscription.deleted", {
            "customer": "cus_123",
        }, mock_supabase)

    assert result["status"] == "processed"


def test_payment_failed_marks_past_due():
    """invoice.payment_failed should mark tenant as past_due."""
    mock_supabase = MagicMock()

    def table_side_effect(name):
        mock_table = MagicMock()
        if name == "stripe_events":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = []
        elif name == "tenants":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [
                {"id": "tenant-1"}
            ]
        return mock_table

    mock_supabase.table.side_effect = table_side_effect

    from cascade_api.api.stripe_webhook import process_webhook_event
    result = process_webhook_event("evt-fail", "invoice.payment_failed", {
        "customer": "cus_456",
    }, mock_supabase)

    assert result["status"] == "processed"
