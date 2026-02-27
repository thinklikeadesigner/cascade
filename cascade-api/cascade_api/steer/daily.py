"""Generate daily task recommendations based on skill gaps and indicator deficits."""

from __future__ import annotations

import json
from datetime import date, timedelta

import structlog
from supabase import Client as SupabaseClient

from cascade_api.db.goals import get_goals
from cascade_api.db.indicators import get_deficit
from cascade_api.dependencies import get_anthropic
from cascade_api.steer.skill_tracker import get_skill_gaps

log = structlog.get_logger()

DAILY_TASK_PROMPT = """\
You are a daily task generator for a goal-execution system. Given the user's \
highest-priority skill gaps and leading indicator deficits, generate 1-3 \
concrete Core tasks for today.

Each task must be:
- Specific and actionable (not "study algorithms" but "solve 3 medium BFS problems on LeetCode")
- Estimated at 30-90 minutes
- Directly tied to a skill or indicator

Return ONLY a JSON array — no markdown, no explanation. Each element:
{{"title": "...", "estimated_minutes": 60, "skill_name": "...", "rationale": "..."}}

Top skill gaps (by leverage):
{gaps_text}

Top indicator deficits:
{deficits_text}

Incomplete tasks this week (avoid duplicates):
{existing_tasks}
"""


async def generate_daily_tasks(
    supabase: SupabaseClient,
    tenant_id: str,
    api_key: str,
) -> list[dict]:
    """Generate today's recommended Core tasks based on leverage ranking.

    Leverage = skill_weight x deficit_urgency, where:
        deficit_urgency = deficit / days_until_due (or deficit if no due_date)
    """
    # Get all active goals
    goals = await get_goals(supabase, tenant_id, status="active")
    if not goals:
        log.info("daily.no_active_goals", tenant_id=tenant_id)
        return []

    # Aggregate deficits and skill gaps across all active goals
    all_deficits: list[dict] = []
    all_gaps: list[dict] = []

    for goal in goals:
        goal_id = goal["id"]

        deficits = await get_deficit(supabase, tenant_id, goal_id)
        for d in deficits:
            d["goal_id"] = goal_id
        all_deficits.extend(deficits)

        gaps = await get_skill_gaps(supabase, tenant_id, goal_id)
        for g in gaps:
            g["goal_id"] = goal_id
        all_gaps.extend(gaps)

    # Calculate leverage scores for deficits
    today = date.today()
    for deficit in all_deficits:
        if deficit.get("skill_name"):
            # Find matching skill weight
            matching = [
                g for g in all_gaps if g["skill_name"] == deficit["skill_name"]
            ]
            skill_weight = matching[0]["required_weight"] if matching else 0.5
        else:
            skill_weight = 0.5

        # Urgency from due date
        due = deficit.get("due_date")
        if due:
            # Handle both string and date types
            if isinstance(due, str):
                from datetime import datetime
                due_date = datetime.strptime(due, "%Y-%m-%d").date()
            else:
                due_date = due
            days_left = max((due_date - today).days, 1)
            urgency = deficit["deficit"] / days_left
        else:
            urgency = float(deficit["deficit"])

        deficit["leverage_score"] = round(skill_weight * urgency, 4)

    all_deficits.sort(key=lambda d: d["leverage_score"], reverse=True)

    # Get incomplete tasks for the current week to avoid duplicates
    monday = today - timedelta(days=today.weekday())
    existing_result = (
        supabase.table("tasks")
        .select("title")
        .eq("tenant_id", tenant_id)
        .eq("week_start", monday.isoformat())
        .eq("completed", False)
        .execute()
    )
    existing_titles = [t["title"] for t in existing_result.data]

    # Build prompt context
    gaps_text = "\n".join(
        f"- {g['skill_name']}: weight={g['required_weight']}, "
        f"proficiency={g['current_proficiency']}, gap={g['gap']}"
        for g in all_gaps[:8]
    ) or "No skill gaps — expert graph may not be built yet."

    deficits_text = "\n".join(
        f"- {d['title']}: deficit={d['deficit']} {d.get('unit') or 'units'}, "
        f"leverage={d['leverage_score']}"
        for d in all_deficits[:6]
    ) or "No indicator deficits."

    existing_text = "\n".join(
        f"- {t}" for t in existing_titles[:10]
    ) or "None"

    # Ask Claude (Haiku — fast/cheap for task generation)
    client = get_anthropic(api_key)
    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": DAILY_TASK_PROMPT.format(
                    gaps_text=gaps_text,
                    deficits_text=deficits_text,
                    existing_tasks=existing_text,
                ),
            }
        ],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]
    tasks: list[dict] = json.loads(raw)

    # Attach leverage scores from our ranking
    for i, task in enumerate(tasks):
        if i < len(all_deficits):
            task["leverage_score"] = all_deficits[i]["leverage_score"]
        else:
            task["leverage_score"] = 0.0

    log.info("daily.generated", tenant_id=tenant_id, task_count=len(tasks))
    return tasks[:3]
