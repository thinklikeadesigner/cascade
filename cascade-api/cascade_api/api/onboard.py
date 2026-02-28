"""Onboarding API — goal creation, plan generation, Telegram connection."""

from __future__ import annotations

from datetime import datetime, timezone
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException
import structlog
from cascade_api.dependencies import get_supabase
from cascade_api.observability.posthog_client import track_event
from cascade_api.telegram.tokens import generate_token

log = structlog.get_logger()
router = APIRouter(prefix="/api/onboard", tags=["onboard"])


class GoalRequest(BaseModel):
    user_id: str
    title: str
    description: str
    success_criteria: str
    target_date: str
    current_state: str
    core_hours: int
    flex_hours: int


class SetScheduleRequest(BaseModel):
    user_id: str
    morning_hour: int
    morning_minute: int
    review_day: int
    timezone: str


class TelegramConnectRequest(BaseModel):
    user_id: str
    telegram_id: int


@router.post("/goal")
async def create_goal(req: GoalRequest):
    """Create tenant (if needed) + goal. Transition to goal_set."""
    try:
        supabase = get_supabase()

        # Find or create tenant
        result = supabase.table("tenants").select("*").eq("user_id", req.user_id).execute()
        if result.data:
            tenant = result.data[0]
        else:
            tenant = supabase.table("tenants").insert({
                "user_id": req.user_id,
                "core_hours": req.core_hours,
                "flex_hours": req.flex_hours,
                "onboarding_status": "signed_up",
            }).execute().data[0]

        # Create goal
        goal = supabase.table("goals").insert({
            "tenant_id": tenant["id"],
            "title": req.title,
            "description": f"{req.description}\n\nCurrent state: {req.current_state}",
            "success_criteria": req.success_criteria,
            "target_date": req.target_date,
        }).execute().data[0]

        # Update onboarding status
        supabase.table("tenants").update({
            "onboarding_status": "goal_set",
        }).eq("id", tenant["id"]).execute()

        track_event(req.user_id, "goal_defined", {"goal_title": req.title})

        return {"tenant_id": tenant["id"], "goal_id": goal["id"], "status": "goal_set"}
    except Exception as e:
        log.error("create_goal.failed", error=str(e), user_id=req.user_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/connect-telegram")
async def connect_telegram(req: TelegramConnectRequest):
    """Link Telegram account to tenant. Transition to tg_connected."""
    supabase = get_supabase()

    result = supabase.table("tenants").select("*").eq("user_id", req.user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = result.data[0]
    supabase.table("tenants").update({
        "telegram_id": req.telegram_id,
        "onboarding_status": "tg_connected",
    }).eq("id", tenant["id"]).execute()

    track_event(req.user_id, "telegram_connected", {"telegram_id": req.telegram_id})

    return {"status": "tg_connected", "tenant_id": tenant["id"]}


class TelegramLinkRequest(BaseModel):
    user_id: str


@router.post("/generate-telegram-link")
async def generate_telegram_link(req: TelegramLinkRequest):
    """Generate a secure one-time deep link token for Telegram connection."""
    supabase = get_supabase()

    result = supabase.table("tenants").select("*").eq("user_id", req.user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = result.data[0]
    token = generate_token(supabase, tenant["id"])

    return {"token": token, "tenant_id": tenant["id"]}


@router.post("/set-schedule")
async def set_schedule(req: SetScheduleRequest):
    """Set user's schedule preferences and timezone during onboarding."""
    supabase = get_supabase()

    result = supabase.table("tenants").select("*").eq("user_id", req.user_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant = result.data[0]
    supabase.table("tenants").update({
        "morning_hour": req.morning_hour,
        "morning_minute": req.morning_minute,
        "review_day": req.review_day,
        "timezone": req.timezone,
    }).eq("id", tenant["id"]).execute()

    track_event(req.user_id, "schedule_set", {
        "morning_hour": req.morning_hour,
        "review_day": req.review_day,
        "timezone": req.timezone,
    })

    return {"status": "schedule_set", "tenant_id": tenant["id"]}
