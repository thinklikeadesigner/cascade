"""GET /api/status — read-only progress snapshot."""

from __future__ import annotations

from datetime import date, timedelta

import structlog
from fastapi import HTTPException, Query
from pydantic import BaseModel

from cascade_api.api.router import api_router
from cascade_api.db.client import get_supabase
from cascade_api.db import tracker, tasks, adaptations, goals

log = structlog.get_logger()


class VelocitySnapshot(BaseModel):
    weeks: list[dict]
    trend: str  # "up", "down", "flat"


class StatusResponse(BaseModel):
    velocity: VelocitySnapshot
    week_progress: dict
    monthly_progress: dict
    rest_debt_days: int
    active_adaptations: list[dict]
    coaching_line: str


def _current_week_start() -> str:
    """Return Monday of the current week as YYYY-MM-DD."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


def _current_month_start() -> str:
    today = date.today()
    return today.replace(day=1).isoformat()


def _compute_trend(velocity_weeks: list[dict]) -> str:
    """Determine if completion rate is trending up, down, or flat."""
    if len(velocity_weeks) < 2:
        return "flat"
    rates = [w.get("completion_rate") or 0 for w in velocity_weeks[:3]]
    # rates are newest-first
    if rates[0] > rates[-1] + 5:
        return "up"
    elif rates[0] < rates[-1] - 5:
        return "down"
    return "flat"


def _compute_rest_debt(entries: list[dict]) -> int:
    """Count consecutive days with tracker entries (no rest)."""
    if not entries:
        return 0
    today = date.today()
    streak = 0
    for i in range(14):  # look back at most 14 days
        day = today - timedelta(days=i)
        day_str = day.isoformat()
        has_entry = any(e["date"] == day_str for e in entries)
        if has_entry:
            streak += 1
        else:
            break
    return streak


@api_router.get("/api/status", response_model=StatusResponse)
async def get_status(tenant_id: str = Query(...)):
    supabase = get_supabase()

    # Gather data in parallel-ish (all sync supabase calls)
    velocity_weeks = await tracker.get_weekly_velocity(supabase, tenant_id, weeks=4)
    week_start = _current_week_start()
    week_tasks = await tasks.get_week_tasks(supabase, tenant_id, week_start)
    month_start = _current_month_start()
    month_entries = await tracker.get_entries(supabase, tenant_id, start_date=month_start)
    active_adapts = await adaptations.get_active(supabase, tenant_id)
    recent_entries = await tracker.get_entries(supabase, tenant_id)

    # Week progress
    core_tasks = [t for t in week_tasks if t["category"] == "core"]
    flex_tasks = [t for t in week_tasks if t["category"] == "flex"]
    core_done = sum(1 for t in core_tasks if t["completed"])
    flex_done = sum(1 for t in flex_tasks if t["completed"])

    week_progress = {
        "core_completed": core_done,
        "core_total": len(core_tasks),
        "flex_completed": flex_done,
        "flex_total": len(flex_tasks),
        "core_rate": round(core_done / len(core_tasks) * 100, 1) if core_tasks else 0,
    }

    # Monthly progress
    today = date.today()
    days_in_month = (today.replace(month=today.month % 12 + 1, day=1) - timedelta(days=1)).day if today.month < 12 else 31
    days_elapsed = today.day
    pct_month_elapsed = round(days_elapsed / days_in_month * 100, 1)

    monthly_progress = {
        "entries_count": len(month_entries),
        "days_elapsed": days_elapsed,
        "days_in_month": days_in_month,
        "pct_elapsed": pct_month_elapsed,
    }

    # Velocity trend
    trend = _compute_trend(velocity_weeks)

    # Rest debt
    rest_debt = _compute_rest_debt(recent_entries)

    # Coaching line
    if not week_tasks:
        coaching_line = "No tasks planned this week. Run plan to generate your weekly tasks."
    elif week_progress["core_rate"] >= 80:
        coaching_line = f"Strong week — {core_done}/{len(core_tasks)} Core tasks done. Keep the pace."
    elif week_progress["core_rate"] >= 50:
        coaching_line = f"{core_done}/{len(core_tasks)} Core tasks done. Solid progress, but don't let the remaining ones slip."
    else:
        coaching_line = f"Only {core_done}/{len(core_tasks)} Core tasks done. What's blocking you? Let's figure it out."

    if rest_debt > 5:
        coaching_line += f" Rest debt: {rest_debt} days without a break. Take one soon."

    return StatusResponse(
        velocity=VelocitySnapshot(weeks=velocity_weeks, trend=trend),
        week_progress=week_progress,
        monthly_progress=monthly_progress,
        rest_debt_days=rest_debt,
        active_adaptations=active_adapts,
        coaching_line=coaching_line,
    )
