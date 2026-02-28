"""Telegram bot message handlers."""

from __future__ import annotations

import structlog
from telegram import Update
from telegram.ext import ContextTypes

from cascade_api.dependencies import get_supabase
from cascade_api.observability.posthog_client import track_event
from cascade_api.config import settings
from cascade_api.telegram.tokens import verify_token
from cascade_api.utils import is_user_active

log = structlog.get_logger()


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
    """Route all messages through the agent loop."""
    supabase = get_supabase()
    telegram_id = update.effective_user.id
    text = update.message.text.strip()

    if not text:
        return

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

    # Get conversation history
    from cascade_api.db.conversation_history import get_history, save_turn
    from cascade_api.agent.loop import run_agent

    history = await get_history(supabase, tenant_id)

    # Run the agent loop
    try:
        response_text, _updated_messages = await run_agent(
            tenant_id=tenant_id,
            user_message=text,
            conversation_history=history,
            api_key=settings.anthropic_api_key,
        )

        # Save turns
        await save_turn(supabase, tenant_id, "user", text)
        await save_turn(supabase, tenant_id, "assistant", response_text)

        # Send response with HTML formatting (split if > 4096 chars for Telegram limit)
        if len(response_text) <= 4096:
            await update.message.reply_text(response_text, parse_mode="HTML")
        else:
            for i in range(0, len(response_text), 4096):
                await update.message.reply_text(response_text[i:i + 4096], parse_mode="HTML")

        track_event(tenant.get("user_id", tenant_id), "message_processed", {"intent": "agent_loop"})

    except Exception as e:
        log.error("agent.failed", tenant_id=tenant_id, error=str(e))
        await update.message.reply_text(
            "Something went wrong. Try again, or rephrase your message."
        )
