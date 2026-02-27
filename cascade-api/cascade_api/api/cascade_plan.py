"""Full cascade plan generation for onboarding (year -> quarter -> month -> week)."""

from __future__ import annotations

import json
from datetime import date, timedelta
from pydantic import BaseModel
from fastapi import APIRouter
import structlog

from cascade_api.dependencies import get_supabase
from cascade_api.observability.langfuse_client import traced_ask
from cascade_api.observability.posthog_client import track_event

log = structlog.get_logger()
router = APIRouter(prefix="/api/onboard", tags=["onboard"])

CASCADE_SYSTEM_PROMPT = """You are Cascade, a goal-execution engine. Generate a complete cascade plan.

Given a user's goal, success criteria, current state, and timeline, generate:
1. year_plan: One paragraph describing the full arc
2. quarterly_milestones: Array of {{"quarter": int, "description": str, "key_results": [str]}} for relevant quarters
3. monthly_targets: Array of {{"month": int, "targets": [str]}} for the current quarter
4. weekly_tasks: {{"core": [{{"title": str, "estimated_minutes": int, "scheduled_day": str}}], "flex": [{{"title": str, "estimated_minutes": int}}]}}

Core tasks are the minimum viable plan. Flex tasks are acceleration.
Core hours per week: {core_hours}. Flex hours: {flex_hours}.

Return valid JSON only. No markdown fences."""


class CascadePlanRequest(BaseModel):
    tenant_id: str
    goal_id: str
    api_key: str


async def generate_cascade(
    tenant_id: str,
    goal_id: str,
    api_key: str,
    supabase=None,
) -> dict:
    """Generate full cascade: year -> quarter -> month -> week."""
    if supabase is None:
        supabase = get_supabase()

    goal = supabase.table("goals").select("*").eq("id", goal_id).execute().data[0]
    tenant = supabase.table("tenants").select("core_hours, flex_hours").eq("id", tenant_id).execute().data[0]

    prompt = CASCADE_SYSTEM_PROMPT.format(
        core_hours=tenant["core_hours"],
        flex_hours=tenant["flex_hours"],
    )

    user_msg = f"""Goal: {goal['title']}
Success criteria: {goal['success_criteria']}
Current state: {goal['description']}
Target date: {goal['target_date']}
Today: {date.today().isoformat()}"""

    result = await traced_ask(
        system_prompt=prompt,
        user_message=user_msg,
        api_key=api_key,
        user_id=tenant_id,
        context="onboarding_cascade_generation",
    )

    plan = json.loads(result)

    # Mark as plan_drafted BEFORE writing plan data to DB.
    # If the DB writes below fail, the user stays in plan_drafted (not plan_approved
    # with missing data).
    supabase.table("tenants").update({
        "onboarding_status": "plan_drafted",
    }).eq("id", tenant_id).execute()

    # Store quarterly plans
    today = date.today()
    current_quarter = (today.month - 1) // 3 + 1
    for qm in plan.get("quarterly_milestones", []):
        supabase.table("quarterly_plans").insert({
            "goal_id": goal_id,
            "quarter": qm.get("quarter", current_quarter),
            "year": today.year,
            "milestones": qm,
        }).execute()

    # Store monthly plan
    supabase.table("monthly_plans").insert({
        "tenant_id": tenant_id,
        "month": today.month,
        "year": today.year,
        "targets": plan.get("monthly_targets", []),
    }).execute()

    # Store weekly plan + tasks
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_end = week_start + timedelta(days=6)

    wp = supabase.table("weekly_plans").insert({
        "tenant_id": tenant_id,
        "week_start": week_start.isoformat(),
        "week_end": week_end.isoformat(),
    }).execute().data[0]

    weekly = plan.get("weekly_tasks", {})
    for task in weekly.get("core", []):
        supabase.table("tasks").insert({
            "tenant_id": tenant_id,
            "goal_id": goal_id,
            "week_start": week_start.isoformat(),
            "title": task["title"],
            "category": "core",
            "estimated_minutes": task.get("estimated_minutes"),
            "scheduled_day": task.get("scheduled_day"),
        }).execute()

    for task in weekly.get("flex", []):
        supabase.table("tasks").insert({
            "tenant_id": tenant_id,
            "goal_id": goal_id,
            "week_start": week_start.isoformat(),
            "title": task["title"],
            "category": "flex",
            "estimated_minutes": task.get("estimated_minutes"),
        }).execute()

    # All plan data written successfully — now mark as plan_approved
    supabase.table("tenants").update({
        "onboarding_status": "plan_approved",
    }).eq("id", tenant_id).execute()

    track_event(tenant_id, "plan_approved", {"goal_id": goal_id})

    return plan


@router.post("/generate-plan")
async def generate_plan_endpoint(req: CascadePlanRequest):
    """Generate the full cascade plan during onboarding."""
    try:
        plan = await generate_cascade(req.tenant_id, req.goal_id, req.api_key)
        return {"status": "plan_approved", "plan": plan}
    except Exception as e:
        import traceback
        log.error("generate_plan.failed", error=str(e), traceback=traceback.format_exc(), tenant_id=req.tenant_id, goal_id=req.goal_id)
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))
