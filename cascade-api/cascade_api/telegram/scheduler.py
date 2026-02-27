"""Pull-based scheduled message logic for NanoClaw Telegram bot.

Instead of in-process job queues (which die on container restart),
this module exposes functions that are called by cron endpoints.
Each function queries Supabase for eligible tenants, checks timezone
windows, and uses message_deliveries for idempotent delivery.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import structlog
from telegram import Bot

from cascade_api.dependencies import get_supabase
from cascade_api.observability.posthog_client import track_event
from cascade_api.telegram.trial_manager import get_trial_actions
from cascade_api.utils import is_user_active

log = structlog.get_logger()

# Local-time windows for scheduled messages (inclusive start, exclusive end)
MORNING_WINDOW = (7, 0, 7, 30)   # 07:00–07:30 local
EVENING_WINDOW = (20, 0, 20, 30)  # 20:00–20:30 local
DEFAULT_TZ = "America/New_York"


def _in_window(local_now: datetime, window: tuple[int, int, int, int]) -> bool:
    """Check if local_now falls within [HH:MM, HH:MM)."""
    start_h, start_m, end_h, end_m = window
    t = local_now.hour * 60 + local_now.minute
    return start_h * 60 + start_m <= t < end_h * 60 + end_m


def _get_active_tenants(supabase) -> list[dict]:
    """Return tenants with a telegram_id that are active (paying or in trial).

    Since the is_active column was replaced with a computed function,
    we query all tenants with telegram_id set and filter in application
    code using the shared is_user_active() utility.
    """
    tenants = supabase.table("tenants").select("*") \
        .not_.is_("telegram_id", "null") \
        .execute().data
    return [t for t in tenants if is_user_active(t)]


def _already_sent(supabase, tenant_id: str, message_type: str, today: date) -> bool:
    """Check message_deliveries for an existing record."""
    rows = supabase.table("message_deliveries").select("id") \
        .eq("tenant_id", tenant_id) \
        .eq("message_type", message_type) \
        .eq("scheduled_for", today.isoformat()) \
        .execute().data
    return len(rows) > 0


def _record_delivery(supabase, tenant_id: str, message_type: str, today: date):
    """Insert a delivery record (idempotent via UNIQUE constraint)."""
    supabase.table("message_deliveries").insert({
        "tenant_id": tenant_id,
        "message_type": message_type,
        "scheduled_for": today.isoformat(),
    }).execute()


# ── Message builders (unchanged business logic) ────────────────────

async def build_morning_message(tenant_id: str, today: date) -> str:
    """Build morning message with Core tasks only.

    Mentions one Flex task at the bottom if available.
    """
    supabase = get_supabase()
    week_start = today - timedelta(days=today.weekday())

    tasks = supabase.table("tasks").select("*") \
        .eq("tenant_id", tenant_id) \
        .eq("week_start", week_start.isoformat()) \
        .execute().data

    day_tasks = [
        t for t in tasks
        if t.get("scheduled_day") == today.isoformat()
        and t.get("category") == "core"
        and not t.get("completed")
    ]

    if not day_tasks:
        return f"{today.strftime('%A')} — no Core tasks scheduled. Rest day or use Flex time."

    day_name = today.strftime("%A")
    lines = [f"{day_name} — {len(day_tasks)} Core task{'s' if len(day_tasks) != 1 else ''}:"]
    for t in day_tasks:
        mins = t.get("estimated_minutes", "")
        time_str = f" ({mins} min)" if mins else ""
        lines.append(f"  {t['title']}{time_str}")

    # Check for flex tasks to mention at bottom
    flex_tasks = [
        t for t in tasks
        if t.get("scheduled_day") == today.isoformat()
        and t.get("category") == "flex"
        and not t.get("completed")
    ]
    if flex_tasks:
        lines.append(f"\nFlex if you have energy: {flex_tasks[0]['title']}")

    return "\n".join(lines)


async def build_evening_message() -> str:
    """Evening check-in prompt."""
    return "How'd today go?"


async def build_sunday_review_message(tenant_id: str, week_start: date) -> str:
    """Build Sunday review with stats and a coaching line."""
    supabase = get_supabase()
    week_end = week_start + timedelta(days=6)

    # Get tasks for this week
    tasks = supabase.table("tasks").select("*") \
        .eq("tenant_id", tenant_id) \
        .eq("week_start", week_start.isoformat()) \
        .execute().data

    core = [t for t in tasks if t.get("category") == "core"]
    flex = [t for t in tasks if t.get("category") == "flex"]
    core_done = len([t for t in core if t.get("completed")])
    flex_done = len([t for t in flex if t.get("completed")])

    # Get tracker entries for energy
    entries = supabase.table("tracker_entries").select("energy_level") \
        .eq("tenant_id", tenant_id) \
        .gte("date", week_start.isoformat()) \
        .lte("date", week_end.isoformat()) \
        .execute().data

    energy_values = [e["energy_level"] for e in entries if e.get("energy_level")]
    avg_energy = sum(energy_values) / len(energy_values) if energy_values else None

    # Build message
    core_pct = round(core_done / len(core) * 100) if core else 0
    lines = ["Week done.\n"]
    lines.append(f"Core: {core_done}/{len(core)} tasks ({core_pct}%)")
    lines.append(f"Flex: {flex_done}/{len(flex)} tasks")
    if avg_energy is not None:
        lines.append(f"Energy: averaged {avg_energy:.1f}/5")

    # Coaching line — honest, no cheerleading
    if core_pct >= 80:
        lines.append(f"\nStrong week. {core_pct}% Core completion.")
    elif core_pct >= 60:
        lines.append(f"\nSolid. {core_pct}% Core — room to tighten up next week.")
    elif core_pct >= 40:
        lines.append(f"\n{core_pct}% Core. Below target. Was scope too high or was it a rough week?")
    else:
        lines.append(f"\n{core_pct}% Core. Let's figure out what happened and adjust next week's plan.")

    return "\n".join(lines)


async def build_monday_kickoff_message(tenant_id: str, today: date) -> str:
    """Build Monday kickoff with week's Core goals and today's tasks."""
    supabase = get_supabase()
    week_start = today  # Monday IS the week start

    # Check if a weekly plan exists
    plan = supabase.table("weekly_plans").select("id") \
        .eq("tenant_id", tenant_id) \
        .eq("week_start", week_start.isoformat()) \
        .execute().data

    if not plan:
        return (
            "No plan for this week yet. Open Claude Code and run `plan`, "
            "or tell me your top 3 priorities and I'll track those."
        )

    # Get tasks for the week
    tasks = supabase.table("tasks").select("*") \
        .eq("tenant_id", tenant_id) \
        .eq("week_start", week_start.isoformat()) \
        .order("sort_order") \
        .execute().data

    core = [t for t in tasks if t.get("category") == "core"]

    lines = ["This week's Core:"]
    for t in core:
        lines.append(f"  {t['title']}")

    # Today's tasks
    today_tasks = [
        t for t in tasks
        if t.get("scheduled_day") == today.isoformat()
        and t.get("category") == "core"
    ]

    if today_tasks:
        lines.append(f"\nToday (Monday):")
        for t in today_tasks:
            mins = t.get("estimated_minutes", "")
            time_str = f" ({mins} min)" if mins else ""
            lines.append(f"  {t['title']}{time_str}")

    return "\n".join(lines)


# ── Pull-based send functions (called by cron endpoints) ───────────

async def send_morning_messages(bot: Bot):
    """Send morning messages to all eligible tenants in the morning window."""
    supabase = get_supabase()
    utc_now = datetime.now(timezone.utc)
    tenants = _get_active_tenants(supabase)
    sent = 0

    for tenant in tenants:
        tenant_id = tenant["id"]
        telegram_id = tenant["telegram_id"]
        tz_name = tenant.get("timezone") or DEFAULT_TZ

        try:
            tz = ZoneInfo(tz_name)
        except (KeyError, Exception):
            tz = ZoneInfo(DEFAULT_TZ)

        local_now = utc_now.astimezone(tz)
        today = local_now.date()

        if not _in_window(local_now, MORNING_WINDOW):
            continue

        if _already_sent(supabase, tenant_id, "morning", today):
            continue

        try:
            msg = await build_morning_message(tenant_id, today)
            await bot.send_message(chat_id=telegram_id, text=msg)
            _record_delivery(supabase, tenant_id, "morning", today)
            track_event(tenant.get("user_id", tenant_id), "scheduled_morning_sent", {})
            log.info("scheduled.sent", tenant_id=tenant_id, type="morning")
            sent += 1
        except Exception as e:
            log.error("scheduled.failed", tenant_id=tenant_id, type="morning", error=str(e))

    return {"sent": sent, "eligible": len(tenants)}


async def send_evening_messages(bot: Bot):
    """Send evening messages to all eligible tenants in the evening window."""
    supabase = get_supabase()
    utc_now = datetime.now(timezone.utc)
    tenants = _get_active_tenants(supabase)
    sent = 0

    for tenant in tenants:
        tenant_id = tenant["id"]
        telegram_id = tenant["telegram_id"]
        tz_name = tenant.get("timezone") or DEFAULT_TZ

        try:
            tz = ZoneInfo(tz_name)
        except (KeyError, Exception):
            tz = ZoneInfo(DEFAULT_TZ)

        local_now = utc_now.astimezone(tz)
        today = local_now.date()

        if not _in_window(local_now, EVENING_WINDOW):
            continue

        if _already_sent(supabase, tenant_id, "evening", today):
            continue

        try:
            msg = await build_evening_message()
            await bot.send_message(chat_id=telegram_id, text=msg)
            _record_delivery(supabase, tenant_id, "evening", today)
            track_event(tenant.get("user_id", tenant_id), "scheduled_evening_sent", {})
            log.info("scheduled.sent", tenant_id=tenant_id, type="evening")
            sent += 1
        except Exception as e:
            log.error("scheduled.failed", tenant_id=tenant_id, type="evening", error=str(e))

    return {"sent": sent, "eligible": len(tenants)}


async def send_sunday_review_messages(bot: Bot):
    """Send Sunday review to all eligible tenants in the evening window on Sunday."""
    supabase = get_supabase()
    utc_now = datetime.now(timezone.utc)
    tenants = _get_active_tenants(supabase)
    sent = 0

    for tenant in tenants:
        tenant_id = tenant["id"]
        telegram_id = tenant["telegram_id"]
        tz_name = tenant.get("timezone") or DEFAULT_TZ

        try:
            tz = ZoneInfo(tz_name)
        except (KeyError, Exception):
            tz = ZoneInfo(DEFAULT_TZ)

        local_now = utc_now.astimezone(tz)
        today = local_now.date()

        # Only on Sundays
        if today.weekday() != 6:
            continue

        if not _in_window(local_now, EVENING_WINDOW):
            continue

        if _already_sent(supabase, tenant_id, "weekly_review", today):
            continue

        try:
            week_start = today - timedelta(days=6)  # Monday of this week
            msg = await build_sunday_review_message(tenant_id, week_start)
            await bot.send_message(chat_id=telegram_id, text=msg)

            # Record delivery FIRST for idempotency guard
            _record_delivery(supabase, tenant_id, "weekly_review", today)

            # Increment completed_weekly_reviews
            reviews = tenant.get("completed_weekly_reviews", 0)
            supabase.table("tenants").update({
                "completed_weekly_reviews": reviews + 1,
            }).eq("id", tenant_id).execute()

            track_event(tenant.get("user_id", tenant_id), "weekly_review_sent", {
                "week_number": reviews + 1,
            })
            log.info("scheduled.sent", tenant_id=tenant_id, type="weekly_review")
            sent += 1
        except Exception as e:
            log.error("scheduled.failed", tenant_id=tenant_id, type="weekly_review", error=str(e))

    return {"sent": sent, "eligible": len(tenants)}


async def send_monday_kickoff_messages(bot: Bot):
    """Send Monday kickoff to all eligible tenants in the morning window on Monday."""
    supabase = get_supabase()
    utc_now = datetime.now(timezone.utc)
    tenants = _get_active_tenants(supabase)
    sent = 0

    for tenant in tenants:
        tenant_id = tenant["id"]
        telegram_id = tenant["telegram_id"]
        tz_name = tenant.get("timezone") or DEFAULT_TZ

        try:
            tz = ZoneInfo(tz_name)
        except (KeyError, Exception):
            tz = ZoneInfo(DEFAULT_TZ)

        local_now = utc_now.astimezone(tz)
        today = local_now.date()

        # Only on Mondays
        if today.weekday() != 0:
            continue

        if not _in_window(local_now, MORNING_WINDOW):
            continue

        if _already_sent(supabase, tenant_id, "weekly_kickoff", today):
            continue

        try:
            msg = await build_monday_kickoff_message(tenant_id, today)
            await bot.send_message(chat_id=telegram_id, text=msg)
            _record_delivery(supabase, tenant_id, "weekly_kickoff", today)
            track_event(tenant.get("user_id", tenant_id), "weekly_kickoff_sent", {})
            log.info("scheduled.sent", tenant_id=tenant_id, type="weekly_kickoff")
            sent += 1
        except Exception as e:
            log.error("scheduled.failed", tenant_id=tenant_id, type="weekly_kickoff", error=str(e))

    return {"sent": sent, "eligible": len(tenants)}


async def run_trial_check_pull(bot: Bot):
    """Check for users who've completed 2+ weekly reviews but haven't paid.

    Sends a payment nudge once. Uses message_deliveries for idempotency.
    Deactivation is automatic via is_user_active() — no status change needed.
    """
    from cascade_api.config import settings

    supabase = get_supabase()
    utc_now = datetime.now(timezone.utc)

    # Get ALL tenants with telegram (not just active — we need to reach trial-ended users)
    tenants = supabase.table("tenants").select("*") \
        .not_.is_("telegram_id", "null") \
        .execute().data

    actions = get_trial_actions(tenants)
    processed = 0

    for action in actions:
        tenant = action["tenant"]
        tenant_id = tenant["id"]
        telegram_id = tenant["telegram_id"]
        today = utc_now.date()

        if _already_sent(supabase, tenant_id, "trial_reminder", today):
            continue

        try:
            checkout_url = (
                f"{settings.frontend_url or 'https://cascade-flame.vercel.app'}"
                f"/payment?tenant={tenant_id}"
            )
            await bot.send_message(
                chat_id=telegram_id,
                text=(
                    "You've completed 2 weeks with Cascade. "
                    "To keep your daily rhythm going, activate your subscription: "
                    f"{checkout_url}"
                ),
            )
            _record_delivery(supabase, tenant_id, "trial_reminder", today)
            track_event(tenant.get("user_id", tenant_id), "payment_link_sent", {
                "completed_reviews": tenant.get("completed_weekly_reviews", 0),
            })
            processed += 1
        except Exception as e:
            log.error("trial_check.failed", tenant_id=tenant_id, error=str(e))

    return {"processed": processed, "actions": len(actions)}
