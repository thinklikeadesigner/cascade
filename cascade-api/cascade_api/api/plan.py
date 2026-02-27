"""POST /api/plan — generate next week's tasks using Claude."""

from __future__ import annotations

import json
from datetime import date, timedelta

import structlog
from fastapi import HTTPException
from pydantic import BaseModel

from cascade_api.api.router import api_router
from cascade_api.db.client import get_supabase
from cascade_api.db import tracker, tasks, adaptations, goals
from cascade_api.dependencies import get_anthropic

log = structlog.get_logger()

PLAN_SYSTEM_PROMPT = """\
You are the Cascade planning engine. Generate a weekly task plan based on the user's goals, \
recent velocity, adaptations, and monthly targets.

Rules:
- Core tasks must be achievable within the user's Core hours alone
- Flex tasks are bonus — reach goals shouldn't depend on them
- If velocity data shows the user consistently completes less than planned, reduce scope
- Apply any active adaptations (day patterns, energy patterns, scope adjustments)
- Distribute tasks across the week, respecting any known low-energy days
- Each task needs: title, scheduled_day (YYYY-MM-DD), category (core/flex), estimated_minutes

Return ONLY valid JSON:
{
  "core_tasks": [
    {"title": "...", "scheduled_day": "YYYY-MM-DD", "estimated_minutes": 60}
  ],
  "flex_tasks": [
    {"title": "...", "scheduled_day": "YYYY-MM-DD", "estimated_minutes": 30}
  ],
  "concerns": ["any concerns about pacing, scope, or risk"]
}
"""


class PlanRequest(BaseModel):
    tenant_id: str
    api_key: str | None = None


class PlanResponse(BaseModel):
    week_start: str
    core_tasks: list[dict]
    flex_tasks: list[dict]
    concerns: list[str]


def _next_week_start() -> str:
    """Return Monday of next week as YYYY-MM-DD."""
    today = date.today()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    return (today + timedelta(days=days_until_monday)).isoformat()


def _current_week_start() -> str:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


def _current_month_end() -> str:
    today = date.today()
    if today.month == 12:
        last_day = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
    else:
        last_day = today.replace(month=today.month + 1, day=1) - timedelta(days=1)
    return last_day.isoformat()


@api_router.post("/api/plan", response_model=PlanResponse)
async def generate_plan(req: PlanRequest):
    supabase = get_supabase()
    week_start = _next_week_start()

    # Gather context
    velocity = await tracker.get_weekly_velocity(supabase, req.tenant_id, weeks=4)
    current_tasks = await tasks.get_week_tasks(supabase, req.tenant_id, _current_week_start())
    active_goals = await goals.get_goals(supabase, req.tenant_id, status="active")
    active_adapts = await adaptations.get_active(supabase, req.tenant_id)

    # Monthly entries for context
    month_start = date.today().replace(day=1).isoformat()
    month_entries = await tracker.get_entries(
        supabase, req.tenant_id, start_date=month_start,
    )

    if not active_goals:
        raise HTTPException(status_code=404, detail="No active goals found. Run cascade setup first.")

    # Build context for Claude
    context = {
        "week_start": week_start,
        "days": [(date.fromisoformat(week_start) + timedelta(days=i)).isoformat() for i in range(7)],
        "goals": [{"title": g["title"], "description": g.get("description"), "target_date": g.get("target_date")} for g in active_goals],
        "velocity_last_4_weeks": velocity,
        "current_week_tasks": [
            {"title": t["title"], "category": t["category"], "completed": t["completed"]}
            for t in current_tasks
        ],
        "monthly_entries_count": len(month_entries),
        "days_left_in_month": (date.fromisoformat(_current_month_end()) - date.today()).days,
        "active_adaptations": [
            {"type": a["pattern_type"], "description": a["description"]}
            for a in active_adapts
        ],
    }

    # Call Claude to generate the plan
    try:
        client = get_anthropic(req.api_key)
        message = await client.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=2048,
            system=PLAN_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"Generate next week's plan based on this context:\n{json.dumps(context, indent=2, default=str)}",
                }
            ],
        )
        plan_data = json.loads(message.content[0].text)
    except json.JSONDecodeError:
        log.error("plan.json_failed", raw=message.content[0].text)
        raise HTTPException(status_code=422, detail="Failed to parse plan from LLM")
    except Exception as exc:
        log.error("plan.failed", error=str(exc))
        raise HTTPException(status_code=502, detail="LLM plan generation failed")

    # Write tasks to database
    core_tasks_out = []
    for task_data in plan_data.get("core_tasks", []):
        goal_id = active_goals[0]["id"] if active_goals else None
        task = await tasks.create_task(
            supabase,
            tenant_id=req.tenant_id,
            title=task_data["title"],
            week_start=week_start,
            scheduled_day=task_data.get("scheduled_day"),
            category="core",
            goal_id=goal_id,
            estimated_minutes=task_data.get("estimated_minutes"),
        )
        core_tasks_out.append(task)

    flex_tasks_out = []
    for task_data in plan_data.get("flex_tasks", []):
        goal_id = active_goals[0]["id"] if active_goals else None
        task = await tasks.create_task(
            supabase,
            tenant_id=req.tenant_id,
            title=task_data["title"],
            week_start=week_start,
            scheduled_day=task_data.get("scheduled_day"),
            category="flex",
            goal_id=goal_id,
            estimated_minutes=task_data.get("estimated_minutes"),
        )
        flex_tasks_out.append(task)

    concerns = plan_data.get("concerns", [])

    log.info(
        "plan.generated",
        tenant_id=req.tenant_id,
        week_start=week_start,
        core_count=len(core_tasks_out),
        flex_count=len(flex_tasks_out),
    )

    return PlanResponse(
        week_start=week_start,
        core_tasks=core_tasks_out,
        flex_tasks=flex_tasks_out,
        concerns=concerns,
    )
