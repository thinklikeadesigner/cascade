"""Tool definitions for the Cascade agent loop."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone
import json

from supabase import Client as SupabaseClient


# --- Tool definitions (sent to Claude API) ---

TOOLS = [
    {
        "name": "get_tasks",
        "description": "Get tasks for the current week or a specific day. Use when the user asks about their tasks, what to do today, or their schedule.",
        "input_schema": {
            "type": "object",
            "properties": {
                "day": {
                    "type": "string",
                    "description": "Filter by day: 'today', 'monday', 'tuesday', etc., or YYYY-MM-DD. Omit for all week tasks.",
                },
                "category": {
                    "type": "string",
                    "enum": ["core", "flex"],
                    "description": "Filter by category. Omit for both.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "complete_task",
        "description": "Mark a task as completed. Use when the user says they finished, shipped, or completed something. Find the matching task first with get_tasks.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "UUID of the task to complete."},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "log_progress",
        "description": "Log progress data to tracker. Use when the user reports metrics, activities, energy, or any quantifiable progress.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entry_date": {"type": "string", "description": "YYYY-MM-DD. Default: today."},
                "outreach_sent": {"type": "integer"},
                "conversations": {"type": "integer"},
                "new_clients": {"type": "integer"},
                "features_shipped": {"type": "integer"},
                "content_published": {"type": "integer"},
                "mrr": {"type": "number"},
                "energy_level": {"type": "integer", "description": "1-5 scale."},
                "notes": {"type": "string"},
            },
            "required": [],
        },
    },
    {
        "name": "get_status",
        "description": "Get a progress snapshot: velocity, weekly completion, monthly progress, rest debt. Use when the user asks how they're doing, their status, or progress.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_goals",
        "description": "List the user's goals. Use when discussing goals, priorities, or direction.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "paused", "completed", "abandoned"],
                    "description": "Default: active.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "update_goal",
        "description": "Update a goal's title, description, success criteria, target date, or status. Only use after explicit user confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "goal_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "success_criteria": {"type": "string"},
                "target_date": {"type": "string", "description": "YYYY-MM-DD"},
                "status": {"type": "string", "enum": ["active", "paused", "completed", "abandoned"]},
            },
            "required": ["goal_id"],
        },
    },
    {
        "name": "add_task",
        "description": "Add a task to the current or specified week. Use when the user wants to add something to their plan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "scheduled_day": {"type": "string", "description": "YYYY-MM-DD or day name (monday, tuesday...)."},
                "category": {"type": "string", "enum": ["core", "flex"], "description": "Default: core."},
                "estimated_minutes": {"type": "integer"},
            },
            "required": ["title"],
        },
    },
    {
        "name": "move_task",
        "description": "Reschedule a task to a different day. Use when the user wants to move something.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
                "new_day": {"type": "string", "description": "YYYY-MM-DD or day name."},
            },
            "required": ["task_id", "new_day"],
        },
    },
    {
        "name": "remove_task",
        "description": "Remove a task from the plan. Only use after explicit user confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "get_history",
        "description": "Get recent tracker entries. Use when the user asks about past data or trends.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days to look back. Default: 7."},
            },
            "required": [],
        },
    },
    {
        "name": "get_adaptations",
        "description": "Get active adaptation patterns. Use when discussing what Cascade has learned about the user.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "add_adaptation",
        "description": "Record a new pattern detected about the user. Use when you notice a recurring behavior worth tracking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern_type": {
                    "type": "string",
                    "enum": ["velocity", "energy", "day_pattern", "rest_debt", "scope"],
                },
                "description": {"type": "string"},
            },
            "required": ["pattern_type", "description"],
        },
    },
    {
        "name": "update_monthly_targets",
        "description": "Update monthly plan targets. Only use after explicit user confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {
                "targets": {
                    "type": "object",
                    "description": "Key-value pairs of target metrics to update.",
                },
                "month": {"type": "integer", "description": "1-12. Default: current month."},
                "year": {"type": "integer", "description": "Default: current year."},
            },
            "required": ["targets"],
        },
    },
    {
        "name": "get_weekly_review",
        "description": "Get weekly review data: planned vs actual, completion rates, energy, adjustments. Use for end-of-week reviews.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_schedule",
        "description": "Get the user's current notification schedule. Use when the user asks 'what are my times', 'current schedule', or 'when do I get messages'.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "update_schedule",
        "description": "Update the user's daily message time or weekly review day. Use when the user asks to change their morning time or review day. If the user only specifies a day without a time, ask them for the time before calling this tool.",
        "input_schema": {
            "type": "object",
            "properties": {
                "schedule_type": {
                    "type": "string",
                    "enum": ["morning", "review_day"],
                    "description": "'morning' changes daily message time. 'review_day' changes which day the weekly review is included.",
                },
                "hour": {
                    "type": "integer",
                    "description": "Hour (0-23). Required for 'morning'. Not used for 'review_day'.",
                },
                "minute": {
                    "type": "integer",
                    "description": "Minute (0-59). Default: 0.",
                },
                "day_of_week": {
                    "type": "integer",
                    "description": "Day of week (0=Sunday, 1=Monday, ..., 6=Saturday). Required for 'review_day'.",
                },
            },
            "required": ["schedule_type"],
        },
    },
]


# --- Tool executors ---

def _current_week_start() -> str:
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    return monday.isoformat()


def _day_name_to_date(day_name: str, week_start: str) -> str:
    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    start = date.fromisoformat(week_start)
    idx = days.index(day_name.lower())
    return (start + timedelta(days=idx)).isoformat()


async def execute_tool(
    tool_name: str,
    tool_input: dict,
    supabase: SupabaseClient,
    tenant_id: str,
) -> str:
    """Execute a tool and return the result as a JSON string."""
    result = await _EXECUTORS[tool_name](tool_input, supabase, tenant_id)
    return json.dumps(result, default=str)


async def _get_tasks(inp: dict, sb: SupabaseClient, tid: str) -> dict:
    week_start = _current_week_start()
    query = (
        sb.table("tasks").select("*")
        .eq("tenant_id", tid).eq("week_start", week_start)
        .order("sort_order")
    )
    if inp.get("category"):
        query = query.eq("category", inp["category"])
    tasks = query.execute().data

    if inp.get("day"):
        day = inp["day"]
        if day == "today":
            target = date.today().isoformat()
        elif day.lower() in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
            target = _day_name_to_date(day, week_start)
        else:
            target = day
        tasks = [t for t in tasks if t.get("scheduled_day") == target]

    return {"tasks": tasks, "count": len(tasks)}


async def _complete_task(inp: dict, sb: SupabaseClient, tid: str) -> dict:
    result = (
        sb.table("tasks")
        .update({"completed": True, "completed_at": datetime.now(timezone.utc).isoformat()})
        .eq("id", inp["task_id"]).eq("tenant_id", tid).eq("completed", False).execute()
    )
    if result.data:
        return {"status": "completed", "task": result.data[0]}
    return {"error": f"Task {inp['task_id']} not found or already completed"}


async def _log_progress(inp: dict, sb: SupabaseClient, tid: str) -> dict:
    entry_date = inp.get("entry_date") or date.today().isoformat()
    data = {k: v for k, v in inp.items() if v is not None and k != "entry_date"}

    existing = (
        sb.table("tracker_entries").select("*")
        .eq("tenant_id", tid).eq("date", entry_date).execute()
    )
    if existing.data:
        row_id = existing.data[0]["id"]
        result = sb.table("tracker_entries").update(data).eq("id", row_id).execute()
    else:
        row = {"tenant_id": tid, "date": entry_date, **data}
        result = sb.table("tracker_entries").insert(row).execute()

    return {"status": "logged", "entry": result.data[0]}


async def _get_status(inp: dict, sb: SupabaseClient, tid: str) -> dict:
    week_start = _current_week_start()
    week_tasks = (
        sb.table("tasks").select("*")
        .eq("tenant_id", tid).eq("week_start", week_start)
        .order("sort_order").execute().data
    )

    velocity_weeks = sb.rpc(
        "get_weekly_velocity", {"p_tenant_id": tid, "p_weeks": 4}
    ).execute().data

    today = date.today()
    month_start = today.replace(day=1).isoformat()
    month_entries = (
        sb.table("tracker_entries").select("*")
        .eq("tenant_id", tid).gte("date", month_start)
        .order("date", desc=True).execute().data
    )

    recent_entries = (
        sb.table("tracker_entries").select("*")
        .eq("tenant_id", tid).order("date", desc=True)
        .limit(14).execute().data
    )

    core = [t for t in week_tasks if t["category"] == "core"]
    flex = [t for t in week_tasks if t["category"] == "flex"]
    core_done = sum(1 for t in core if t["completed"])
    flex_done = sum(1 for t in flex if t["completed"])

    # Rest debt
    rest_debt = 0
    for i in range(14):
        day = today - timedelta(days=i)
        if any(e["date"] == day.isoformat() for e in recent_entries):
            rest_debt += 1
        else:
            break

    # Trend
    trend = "flat"
    if len(velocity_weeks) >= 2:
        rates = [w.get("completion_rate") or 0 for w in velocity_weeks[:3]]
        if rates[0] > rates[-1] + 5:
            trend = "up"
        elif rates[0] < rates[-1] - 5:
            trend = "down"

    _, days_in_month = calendar.monthrange(today.year, today.month)

    return {
        "week_progress": {
            "core_completed": core_done, "core_total": len(core),
            "flex_completed": flex_done, "flex_total": len(flex),
        },
        "velocity_trend": trend,
        "velocity_weeks": velocity_weeks,
        "monthly_progress": {
            "entries_count": len(month_entries),
            "days_elapsed": today.day,
            "days_in_month": days_in_month,
        },
        "rest_debt_days": rest_debt,
    }


async def _get_goals(inp: dict, sb: SupabaseClient, tid: str) -> dict:
    status = inp.get("status", "active")
    result = (
        sb.table("goals").select("*")
        .eq("tenant_id", tid).eq("status", status)
        .order("created_at", desc=True).execute()
    )
    return {"goals": result.data}


async def _update_goal(inp: dict, sb: SupabaseClient, tid: str) -> dict:
    goal_id = inp.get("goal_id")
    updates = {k: v for k, v in inp.items() if v is not None and k != "goal_id"}
    if not updates:
        return {"error": "No updates specified"}
    result = sb.table("goals").update(updates).eq("id", goal_id).eq("tenant_id", tid).execute()
    if result.data:
        return {"status": "updated", "goal": result.data[0]}
    return {"error": f"Goal {goal_id} not found"}


async def _add_task(inp: dict, sb: SupabaseClient, tid: str) -> dict:
    week_start = _current_week_start()
    row = {
        "tenant_id": tid,
        "title": inp["title"],
        "week_start": week_start,
        "category": inp.get("category", "core"),
    }
    if inp.get("scheduled_day"):
        day = inp["scheduled_day"]
        if day.lower() in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
            row["scheduled_day"] = _day_name_to_date(day, week_start)
        else:
            row["scheduled_day"] = day
    if inp.get("estimated_minutes"):
        row["estimated_minutes"] = inp["estimated_minutes"]

    result = sb.table("tasks").insert(row).execute()
    return {"status": "added", "task": result.data[0]}


async def _move_task(inp: dict, sb: SupabaseClient, tid: str) -> dict:
    week_start = _current_week_start()
    new_day = inp["new_day"]
    if new_day.lower() in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"):
        target = _day_name_to_date(new_day, week_start)
    else:
        target = new_day

    result = (
        sb.table("tasks").update({"scheduled_day": target})
        .eq("id", inp["task_id"]).eq("tenant_id", tid).execute()
    )
    if result.data:
        return {"status": "moved", "task": result.data[0]}
    return {"error": f"Task {inp['task_id']} not found"}


async def _remove_task(inp: dict, sb: SupabaseClient, tid: str) -> dict:
    sb.table("tasks").delete().eq("id", inp["task_id"]).eq("tenant_id", tid).execute()
    return {"status": "removed", "task_id": inp["task_id"]}


async def _get_history(inp: dict, sb: SupabaseClient, tid: str) -> dict:
    days = inp.get("days", 7)
    start = (date.today() - timedelta(days=days)).isoformat()
    result = (
        sb.table("tracker_entries").select("*")
        .eq("tenant_id", tid).gte("date", start)
        .order("date", desc=True).execute()
    )
    return {"entries": result.data}


async def _get_adaptations(inp: dict, sb: SupabaseClient, tid: str) -> dict:
    result = (
        sb.table("adaptations").select("*")
        .eq("tenant_id", tid).eq("active", True)
        .order("detected_at", desc=True).execute()
    )
    return {"adaptations": result.data}


async def _add_adaptation(inp: dict, sb: SupabaseClient, tid: str) -> dict:
    row = {
        "tenant_id": tid,
        "pattern_type": inp["pattern_type"],
        "description": inp["description"],
    }
    result = sb.table("adaptations").insert(row).execute()
    return {"status": "added", "adaptation": result.data[0]}


async def _update_monthly_targets(inp: dict, sb: SupabaseClient, tid: str) -> dict:
    today = date.today()
    m = inp.get("month", today.month)
    y = inp.get("year", today.year)
    new_targets = inp["targets"]

    existing = (
        sb.table("monthly_plans").select("*")
        .eq("tenant_id", tid).eq("month", m).eq("year", y).execute()
    )
    if existing.data:
        plan_id = existing.data[0]["id"]
        current = existing.data[0].get("targets", {})
        merged = {**current, **new_targets}
        result = sb.table("monthly_plans").update({"targets": merged}).eq("id", plan_id).execute()
    else:
        result = sb.table("monthly_plans").insert({
            "tenant_id": tid, "month": m, "year": y, "targets": new_targets,
        }).execute()

    return {"status": "updated", "plan": result.data[0]}


async def _get_weekly_review(inp: dict, sb: SupabaseClient, tid: str) -> dict:
    week_start = _current_week_start()
    week_end = (date.fromisoformat(week_start) + timedelta(days=6)).isoformat()

    tasks_data = (
        sb.table("tasks").select("*")
        .eq("tenant_id", tid).eq("week_start", week_start)
        .order("sort_order").execute().data
    )
    entries = (
        sb.table("tracker_entries").select("*")
        .eq("tenant_id", tid).gte("date", week_start).lte("date", week_end)
        .order("date", desc=True).execute().data
    )

    core = [t for t in tasks_data if t["category"] == "core"]
    flex = [t for t in tasks_data if t["category"] == "flex"]
    core_done = [t for t in core if t["completed"]]
    flex_done = [t for t in flex if t["completed"]]
    core_rate = round(len(core_done) / len(core) * 100, 1) if core else 0
    flex_rate = round(len(flex_done) / len(flex) * 100, 1) if flex else 0

    energy_values = [e["energy_level"] for e in entries if e.get("energy_level")]

    return {
        "planned_vs_actual": {
            "core_planned": len(core), "core_completed": len(core_done),
            "flex_planned": len(flex), "flex_completed": len(flex_done),
        },
        "completion_rate": {"core_pct": core_rate, "flex_pct": flex_rate},
        "what_worked": [t["title"] for t in core_done + flex_done],
        "what_didnt": [t["title"] for t in tasks_data if not t["completed"]],
        "energy": {
            "average": round(sum(energy_values) / len(energy_values), 1) if energy_values else None,
            "low_days": sum(1 for e in energy_values if e <= 2),
            "high_days": sum(1 for e in energy_values if e >= 4),
        },
    }


async def _get_schedule(inp: dict, sb: SupabaseClient, tid: str) -> dict:
    result = sb.table("tenants").select(
        "morning_hour, morning_minute, review_day, timezone"
    ).eq("id", tid).execute()
    if not result.data:
        return {"error": "Tenant not found"}
    t = result.data[0]
    morning_h = t.get("morning_hour", 7)
    morning_m = t.get("morning_minute", 0)
    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    return {
        "daily_message": f"{morning_h:02d}:{morning_m:02d}",
        "review_day": day_names[t.get("review_day", 0)],
        "timezone": t.get("timezone", "America/New_York"),
    }


async def _update_schedule(inp: dict, sb: SupabaseClient, tid: str) -> dict:
    schedule_type = inp["schedule_type"]
    updates = {}
    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

    if schedule_type == "morning":
        hour = inp.get("hour")
        minute = inp.get("minute", 0)
        if hour is None:
            return {"error": "hour is required for morning schedule type."}
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            return {"error": "Invalid time. Hour must be 0-23, minute 0-59."}
        updates["morning_hour"] = hour
        updates["morning_minute"] = minute
        result_msg = f"Daily message moved to {hour:02d}:{minute:02d}."
    elif schedule_type == "review_day":
        day_of_week = inp.get("day_of_week")
        if day_of_week is None:
            return {"error": "day_of_week is required for review_day schedule type."}
        if day_of_week < 0 or day_of_week > 6:
            return {"error": "Invalid day_of_week. Must be 0 (Sunday) through 6 (Saturday)."}
        updates["review_day"] = day_of_week
        result_msg = f"Weekly review moved to {day_names[day_of_week]}."
    else:
        return {"error": f"Unknown schedule_type: {schedule_type}"}

    sb.table("tenants").update(updates).eq("id", tid).execute()
    return {"status": "updated", "message": result_msg}


_EXECUTORS = {
    "get_tasks": _get_tasks,
    "complete_task": _complete_task,
    "log_progress": _log_progress,
    "get_status": _get_status,
    "get_goals": _get_goals,
    "update_goal": _update_goal,
    "add_task": _add_task,
    "move_task": _move_task,
    "remove_task": _remove_task,
    "get_history": _get_history,
    "get_adaptations": _get_adaptations,
    "add_adaptation": _add_adaptation,
    "update_monthly_targets": _update_monthly_targets,
    "get_weekly_review": _get_weekly_review,
    "get_schedule": _get_schedule,
    "update_schedule": _update_schedule,
}
