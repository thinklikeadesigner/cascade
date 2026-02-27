"""POST /api/review — weekly review ritual."""

from __future__ import annotations

from datetime import date, timedelta

import structlog
from fastapi import HTTPException
from pydantic import BaseModel

from cascade_api.api.router import api_router
from cascade_api.db.client import get_supabase
from cascade_api.db import tracker, tasks, adaptations

log = structlog.get_logger()


class ReviewRequest(BaseModel):
    tenant_id: str


class ReviewResponse(BaseModel):
    planned_vs_actual: dict
    completion_rate: dict
    what_worked: list[str]
    what_didnt: list[str]
    energy_assessment: dict
    adjustments: list[str]


def _current_week_start() -> str:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


def _current_week_end() -> str:
    today = date.today()
    sunday = today - timedelta(days=today.weekday()) + timedelta(days=6)
    return sunday.isoformat()


@api_router.post("/api/review", response_model=ReviewResponse)
async def weekly_review(req: ReviewRequest):
    supabase = get_supabase()
    week_start = _current_week_start()
    week_end = _current_week_end()

    # Get week tasks
    week_tasks = await tasks.get_week_tasks(supabase, req.tenant_id, week_start)
    if not week_tasks:
        raise HTTPException(status_code=404, detail="No tasks found for current week")

    # Get tracker data for the week
    entries = await tracker.get_entries(
        supabase, req.tenant_id, start_date=week_start, end_date=week_end,
    )

    # Planned vs actual
    core_tasks = [t for t in week_tasks if t["category"] == "core"]
    flex_tasks = [t for t in week_tasks if t["category"] == "flex"]
    core_done = [t for t in core_tasks if t["completed"]]
    flex_done = [t for t in flex_tasks if t["completed"]]

    planned_vs_actual = {
        "core_planned": len(core_tasks),
        "core_completed": len(core_done),
        "flex_planned": len(flex_tasks),
        "flex_completed": len(flex_done),
        "total_planned": len(week_tasks),
        "total_completed": len(core_done) + len(flex_done),
    }

    # Completion rates
    core_rate = round(len(core_done) / len(core_tasks) * 100, 1) if core_tasks else 0
    flex_rate = round(len(flex_done) / len(flex_tasks) * 100, 1) if flex_tasks else 0
    total_rate = round(
        (len(core_done) + len(flex_done)) / len(week_tasks) * 100, 1
    ) if week_tasks else 0

    completion_rate = {
        "core_pct": core_rate,
        "flex_pct": flex_rate,
        "total_pct": total_rate,
    }

    # What worked — completed tasks
    what_worked = [t["title"] for t in core_done + flex_done]

    # What didn't — incomplete tasks
    incomplete = [t for t in week_tasks if not t["completed"]]
    what_didnt = [t["title"] for t in incomplete]

    # Energy assessment
    energy_values = [e["energy_level"] for e in entries if e.get("energy_level")]
    energy_assessment = {
        "average": round(sum(energy_values) / len(energy_values), 1) if energy_values else None,
        "low_days": sum(1 for e in energy_values if e <= 2),
        "high_days": sum(1 for e in energy_values if e >= 4),
        "entries_with_energy": len(energy_values),
    }

    # Generate adjustments
    adjustments: list[str] = []

    if core_rate < 50:
        adjustments.append(
            f"Core completion at {core_rate}% — consider reducing scope next week."
        )
    elif core_rate < 75:
        adjustments.append(
            f"Core at {core_rate}%. Close but not hitting target. Check what blocked the remaining tasks."
        )

    if flex_tasks and len(flex_done) == 0:
        adjustments.append("Zero Flex tasks completed. Consider dropping Flex or making them smaller.")

    if energy_assessment["average"] and energy_assessment["average"] < 2.5:
        adjustments.append("Low average energy this week. Consider lighter scheduling or more rest.")

    if energy_assessment["low_days"] >= 3:
        adjustments.append(
            f"{energy_assessment['low_days']} low-energy days. Check sleep, stress, or overcommitment."
        )

    if not adjustments:
        adjustments.append("Solid week. Maintain current pace and scope.")

    # Append findings to adaptations table
    if core_rate < 60:
        await adaptations.create_adaptation(
            supabase,
            req.tenant_id,
            pattern_type="velocity",
            description=f"Week of {week_start}: core completion {core_rate}%. Scope may be too high.",
        )
    if energy_assessment["average"] and energy_assessment["average"] < 2.5:
        await adaptations.create_adaptation(
            supabase,
            req.tenant_id,
            pattern_type="energy",
            description=f"Week of {week_start}: avg energy {energy_assessment['average']}/5. Consider lighter load.",
        )

    log.info(
        "review.completed",
        tenant_id=req.tenant_id,
        week_start=week_start,
        core_rate=core_rate,
    )

    return ReviewResponse(
        planned_vs_actual=planned_vs_actual,
        completion_rate=completion_rate,
        what_worked=what_worked,
        what_didnt=what_didnt,
        energy_assessment=energy_assessment,
        adjustments=adjustments,
    )
