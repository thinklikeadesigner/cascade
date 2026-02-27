"""Payment link generation for trial-to-paid conversion."""

from __future__ import annotations

import stripe
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from cascade_api.config import settings
from cascade_api.dependencies import get_supabase

router = APIRouter(prefix="/api/payment", tags=["payment"])

stripe.api_key = settings.stripe_secret_key


class CheckoutRequest(BaseModel):
    tenant_id: str
    plan: str = "founding"  # "founding" or "standard"


@router.post("/create-checkout")
async def create_checkout(req: CheckoutRequest):
    """Generate a Stripe Checkout URL for the tenant."""
    price_id = (
        settings.stripe_founding_price_id
        if req.plan == "founding"
        else settings.stripe_standard_price_id
    )

    if not price_id:
        raise HTTPException(status_code=500, detail="Stripe price not configured")

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        client_reference_id=req.tenant_id,
        success_url=f"{settings.frontend_url or 'https://cascade-flame.vercel.app'}/payment/success",
        cancel_url=f"{settings.frontend_url or 'https://cascade-flame.vercel.app'}/payment/cancel",
    )

    return {"checkout_url": session.url}
