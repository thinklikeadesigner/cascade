"""Pull-based scheduled message logic for NanoClaw Telegram bot.

Consolidates 4 endpoints into 1 daily message per user at their
preferred morning time. Message content varies by day type:
- Normal day: today's Core tasks
- Monday: week overview + today's tasks
- Review day: weekly stats + coaching + today's tasks
- Monday + review day: all of the above
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
from cascade_api.config import settings

log = structlog.get_logger()

# Default schedule preferences (match column defaults in tenants table)
DEFAULT_MORNING_HOUR = 7
DEFAULT_MORNING_MINUTE = 0
DEFAULT_REVIEW_DAY = 0  # Sunday
DEFAULT_TZ = "America/New_York"


def _should_send(local_now: datetime, preferred_hour: int, preferred_minute: int) -> bool:
    """Return True if local time is at or past the preferred send time.

    No-skip logic: once the preferred time passes, the message is eligible.
    The first cron tick after the preferred time sends it.
    Idempotency (message_deliveries) prevents duplicates.
    """
    preferred_min = preferred_hour * 60 + preferred_minute
    now_min = local_now.hour * 60 + local_now.minute
    return now_min >= preferred_min


def _get_daily_message_type(today: date, review_day: int) -> str:
    """Determine what kind of daily message to send.

    Returns one of: 'daily', 'monday_kickoff', 'weekly_review', 'monday_review'.
    review_day uses 0=Sunday convention. Python weekday uses 0=Monday.
    """
    # Convert Python weekday (0=Mon) to our convention (0=Sun)
    local_weekday = (today.weekday() + 1) % 7
    is_monday = today.weekday() == 0
    is_review = local_weekday == review_day

    if is_monday and is_review:
        return "monday_review"
    elif is_monday:
        return "monday_kickoff"
    elif is_review:
        return "weekly_review"
    else:
        return "daily"


def _get_active_tenants(supabase) -> list[dict]:
    """Return tenants with a telegram_id that are active (paying or in trial)."""
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


# ── Message builders (agent loop powered) ──────────────────────────

async def _build_daily_message(tenant_id: str, today: date, message_type: str) -> str:
    """Generate the daily message via agent loop with context based on day type."""
    from cascade_api.agent.loop import run_agent

    day_name = today.strftime("%A")

    if message_type == "daily":
        context = (
            f"You are sending the daily morning message. Today is {today.isoformat()} "
            f"({day_name}). List today's Core tasks. Short, scannable, no preamble. "
            "Mention one Flex task at the end if there is one. If no tasks, say so."
        )
    elif message_type == "monday_kickoff":
        context = (
            f"You are sending the Monday morning message. Today is {today.isoformat()}. "
            "Start with this week's Core goals (brief overview), then list today's tasks. "
            "If no tasks exist, say 'No plan for this week yet. Tell me your top 3 "
            "priorities and I'll create tasks.' Short, scannable."
        )
    elif message_type == "weekly_review":
        week_start = today - timedelta(days=(today.weekday() + 1) % 7 or 7)
        context = (
            f"You are sending the combined weekly review + daily tasks message. "
            f"Today is {today.isoformat()} ({day_name}). "
            f"The week started {week_start.isoformat()}. "
            "First: run the weekly review — completion rates, energy, what worked, "
            "what didn't. One coaching line. Under 150 words for the review section. "
            "Then: list today's Core tasks below the review."
        )
    elif message_type == "monday_review":
        week_start = today - timedelta(days=7)
        context = (
            f"You are sending the combined Monday kickoff + weekly review message. "
            f"Today is {today.isoformat()}. "
            f"Last week started {week_start.isoformat()}. "
            "First: run the weekly review for last week — completion rates, energy, "
            "one coaching line. Under 150 words. "
            "Then: list this week's Core goals and today's tasks."
        )
    else:
        context = (
            f"You are sending the daily morning message. Today is {today.isoformat()} "
            f"({day_name}). List today's Core tasks."
        )

    response, _ = await run_agent(
        tenant_id=tenant_id,
        user_message="Generate today's morning message.",
        conversation_history=[],
        api_key=settings.anthropic_api_key,
        is_scheduled=True,
        scheduled_context=context,
    )
    return response


# ── Pull-based send function (called by cron endpoint) ─────────────

async def send_daily_messages(bot: Bot):
    """Send 1 daily message to each eligible tenant at their preferred time.

    Message content varies by day type:
    - Normal day: today's Core tasks
    - Monday: week overview + today's tasks
    - Review day: weekly stats + today's tasks
    - Monday + review day: both combined
    """
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

        morning_h = tenant.get("morning_hour", DEFAULT_MORNING_HOUR)
        morning_m = tenant.get("morning_minute", DEFAULT_MORNING_MINUTE)
        review_day = tenant.get("review_day", DEFAULT_REVIEW_DAY)

        if not _should_send(local_now, morning_h, morning_m):
            continue

        # Determine message type based on day
        message_type = _get_daily_message_type(today, review_day)

        if _already_sent(supabase, tenant_id, "daily", today):
            continue

        try:
            msg = await _build_daily_message(tenant_id, today, message_type)
            await bot.send_message(chat_id=telegram_id, text=msg)
            _record_delivery(supabase, tenant_id, "daily", today)

            # Increment weekly review counter when review is included
            if message_type in ("weekly_review", "monday_review"):
                reviews = tenant.get("completed_weekly_reviews", 0)
                supabase.table("tenants").update({
                    "completed_weekly_reviews": reviews + 1,
                }).eq("id", tenant_id).execute()

            track_event(tenant.get("user_id", tenant_id), "daily_message_sent", {
                "message_type": message_type,
            })
            log.info("scheduled.sent", tenant_id=tenant_id, type=message_type)
            sent += 1
        except Exception as e:
            log.error("scheduled.failed", tenant_id=tenant_id, type=message_type, error=str(e))

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
