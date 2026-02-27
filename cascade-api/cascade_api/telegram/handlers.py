"""Telegram bot message handlers."""

from __future__ import annotations

import json
import structlog
from telegram import Update
from telegram.ext import ContextTypes

from cascade_api.dependencies import get_supabase
from cascade_api.observability.posthog_client import track_event
from cascade_api.observability.langfuse_client import traced_ask
from cascade_api.config import settings
from cascade_api.telegram.tokens import verify_token
from cascade_api.utils import is_user_active

log = structlog.get_logger()

LOG_PARSE_PROMPT = """You are a progress log parser. Extract structured data from the user's message.
Return JSON with these fields (include only what's mentioned):
- tasks_completed: list of task titles mentioned as done
- energy_level: integer 1-5 if mentioned
- notes: any other info as a string
- metrics: dict of any quantifiable data (e.g. {"outreach_sent": 5, "conversations": 1})

Return valid JSON only."""

STATUS_PROMPT = """You are Cascade, a goal coach. Given the user's progress data, give a brief status update.
Be honest about numbers. No preamble. Under 200 words. Follow this format:
- Week progress (tasks done / total)
- Key metric highlights
- One honest coaching sentence

Data:
{data}"""


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command — link Telegram to tenant via secure deep link token."""
    supabase = get_supabase()
    telegram_id = update.effective_user.id
    name = update.effective_user.first_name

    if not context.args:
        await update.message.reply_text(
            "Welcome to Cascade! To get started, sign up at our website and connect your Telegram from there."
        )
        return

    raw_token = context.args[0]

    # Verify and consume the one-time token
    tenant_id = verify_token(supabase, raw_token)
    if not tenant_id:
        await update.message.reply_text(
            "Invalid or expired link. Please generate a new one from the website."
        )
        return

    # Fetch tenant for user_id (needed for analytics)
    result = supabase.table("tenants").select("*").eq("id", tenant_id).execute()
    tenant = result.data[0]

    # Link Telegram ID
    supabase.table("tenants").update({
        "telegram_id": telegram_id,
        "onboarding_status": "tg_connected",
    }).eq("id", tenant_id).execute()

    track_event(tenant["user_id"], "telegram_connected", {"telegram_id": telegram_id})

    await update.message.reply_text(
        f"You're set, {name}. I'll send your first tasks tomorrow morning.\n\n"
        "You can text me anytime to log progress. Try: \"finished 2 tasks, energy was high\""
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inbound text messages — parse for logging, status, or task completion."""
    supabase = get_supabase()
    telegram_id = update.effective_user.id
    text = update.message.text.strip().lower()

    # Find tenant
    result = supabase.table("tenants").select("*").eq("telegram_id", telegram_id).execute()
    if not result.data:
        await update.message.reply_text("I don't recognize this account. Sign up at our website first.")
        return

    tenant = result.data[0]
    tenant_id = tenant["id"]

    if not is_user_active(tenant):
        await update.message.reply_text(
            "Your trial has ended. To keep using Cascade, activate your subscription at our website."
        )
        return

    # Status check
    if text in ("status", "how am i doing", "where do i stand"):
        await _handle_status(update, tenant)
        return

    # Default: parse as progress log
    await _handle_log(update, tenant, update.message.text)


async def _handle_status(update: Update, tenant: dict):
    """Send a status snapshot."""
    from cascade_api.db.tasks import get_week_tasks
    from cascade_api.db.tracker import get_entries
    from datetime import date, timedelta

    supabase = get_supabase()
    tenant_id = tenant["id"]
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    tasks = await get_week_tasks(supabase, tenant_id, week_start.isoformat())
    core_tasks = [t for t in tasks if t.get("category") == "core"]
    core_done = len([t for t in core_tasks if t.get("completed")])

    entries = await get_entries(supabase, tenant_id, week_start.isoformat(), today.isoformat())

    data = {
        "core_completed": core_done,
        "core_total": len(core_tasks),
        "days_this_week": len(entries),
        "today": today.isoformat(),
    }

    response = await traced_ask(
        system_prompt=STATUS_PROMPT.format(data=json.dumps(data)),
        user_message="Give me my status.",
        api_key=settings.anthropic_api_key,
        user_id=tenant_id,
        context="status_check",
    )

    await update.message.reply_text(response)


async def _handle_log(update: Update, tenant: dict, text: str):
    """Parse a progress update and log it."""
    from cascade_api.db.tracker import log_entry
    from cascade_api.db.tasks import get_week_tasks, complete_task
    from datetime import date, timedelta

    supabase = get_supabase()
    tenant_id = tenant["id"]

    parsed_text = await traced_ask(
        system_prompt=LOG_PARSE_PROMPT,
        user_message=text,
        api_key=settings.anthropic_api_key,
        user_id=tenant_id,
        context="log_parse",
    )

    try:
        parsed = json.loads(parsed_text)
    except json.JSONDecodeError:
        await update.message.reply_text(
            "I couldn't parse that. Try something like: \"sent 5 DMs, energy was good\""
        )
        return

    # Build tracker data
    data = parsed.get("metrics", {})
    if parsed.get("energy_level"):
        data["energy_level"] = parsed["energy_level"]
    if parsed.get("notes"):
        data["notes"] = parsed["notes"]

    await log_entry(supabase, tenant_id, date.today().isoformat(), data)

    # Mark completed tasks
    if parsed.get("tasks_completed"):
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        tasks = await get_week_tasks(supabase, tenant_id, week_start.isoformat())

        for task_title in parsed["tasks_completed"]:
            for task in tasks:
                if task_title.lower() in task["title"].lower() and not task["completed"]:
                    await complete_task(supabase, task["id"])
                    break

    track_event(tenant.get("user_id", tenant_id), "progress_logged", data)

    # Confirmation
    lines = ["Got it."]
    for k, v in data.items():
        if k != "notes":
            lines.append(f"  {k}: {v}")
    if data.get("notes"):
        lines.append(f"  notes: \"{data['notes']}\"")
    lines.append(f"\nLogged for {date.today().strftime('%b %d')}.")

    await update.message.reply_text("\n".join(lines))
