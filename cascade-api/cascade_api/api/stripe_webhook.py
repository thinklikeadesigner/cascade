"""Stripe webhook handler with idempotency."""

from __future__ import annotations

from datetime import datetime, timezone

import stripe
import structlog
from fastapi import APIRouter, Request, HTTPException

from cascade_api.config import settings
from cascade_api.dependencies import get_supabase
from cascade_api.observability.posthog_client import track_event

log = structlog.get_logger()
router = APIRouter(tags=["stripe"])

stripe.api_key = settings.stripe_secret_key


def process_webhook_event(
    event_id: str,
    event_type: str,
    data: dict,
    supabase=None,
) -> dict:
    """Process a Stripe webhook event with idempotency."""
    if supabase is None:
        supabase = get_supabase()

    # Idempotency check
    existing = supabase.table("stripe_events").select("id").eq("stripe_event_id", event_id).execute()
    if existing.data:
        return {"status": "already_processed"}

    # Record event
    supabase.table("stripe_events").insert({
        "stripe_event_id": event_id,
        "event_type": event_type,
    }).execute()

    if event_type == "checkout.session.completed":
        tenant_id = data.get("client_reference_id")
        supabase.table("tenants").update({
            "subscription_status": "active",
            "paid_at": datetime.now(timezone.utc).isoformat(),
            "stripe_customer_id": data.get("customer"),
            "stripe_subscription_id": data.get("subscription"),
        }).eq("id", tenant_id).execute()

        track_event(tenant_id, "payment_completed", {})

    elif event_type == "customer.subscription.deleted":
        customer_id = data.get("customer")
        result = supabase.table("tenants").select("id, user_id").eq("stripe_customer_id", customer_id).execute()
        if result.data:
            t = result.data[0]
            supabase.table("tenants").update({
                "subscription_status": "canceled",
            }).eq("id", t["id"]).execute()
            track_event(t.get("user_id", t["id"]), "churned", {})

    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        result = supabase.table("tenants").select("id").eq("stripe_customer_id", customer_id).execute()
        if result.data:
            supabase.table("tenants").update({
                "subscription_status": "past_due",
                "past_due_since": datetime.now(timezone.utc).isoformat(),
            }).eq("id", result.data[0]["id"]).execute()

    elif event_type == "invoice.paid":
        customer_id = data.get("customer")
        result = supabase.table("tenants").select("id").eq("stripe_customer_id", customer_id).execute()
        if result.data:
            supabase.table("tenants").update({
                "subscription_status": "active",
                "past_due_since": None,
            }).eq("id", result.data[0]["id"]).execute()

    return {"status": "processed"}


@router.post("/api/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle incoming Stripe webhooks."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret,
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(status_code=400, detail="Invalid signature")

    data_obj = event.data.object
    result = process_webhook_event(
        event_id=event.id,
        event_type=event.type,
        data={
            "client_reference_id": getattr(data_obj, "client_reference_id", None),
            "customer": getattr(data_obj, "customer", None),
            "subscription": getattr(data_obj, "subscription", None),
        },
    )

    return result
