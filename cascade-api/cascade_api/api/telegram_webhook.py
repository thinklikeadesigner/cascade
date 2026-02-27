"""Telegram webhook endpoint — receives updates pushed by Telegram."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Request, HTTPException
from telegram import Update

from cascade_api.config import settings

log = structlog.get_logger()

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


@router.post("/set-webhook")
async def set_telegram_webhook(request: Request):
    """Manually trigger webhook registration (for debugging)."""
    if settings.cron_secret:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {settings.cron_secret}":
            raise HTTPException(status_code=401, detail="Unauthorized")

    bot_app = request.app.state.bot_app
    if not bot_app:
        raise HTTPException(status_code=503, detail="Bot not initialized")

    url = settings.telegram_webhook_url
    if not url:
        return {"ok": False, "error": "TELEGRAM_WEBHOOK_URL not set"}

    try:
        result = await bot_app.bot.set_webhook(
            url=url,
            secret_token=settings.telegram_webhook_secret or None,
        )
        info = await bot_app.bot.get_webhook_info()
        return {
            "ok": result,
            "url": info.url,
            "pending_update_count": info.pending_update_count,
            "last_error_message": info.last_error_message,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "attempted_url": url}


@router.get("/webhook-info")
async def webhook_info(request: Request):
    """Check current webhook status."""
    if settings.cron_secret:
        auth = request.headers.get("Authorization", "")
        if auth != f"Bearer {settings.cron_secret}":
            raise HTTPException(status_code=401, detail="Unauthorized")

    bot_app = request.app.state.bot_app
    if not bot_app:
        raise HTTPException(status_code=503, detail="Bot not initialized")

    info = await bot_app.bot.get_webhook_info()
    return {
        "url": info.url,
        "pending_update_count": info.pending_update_count,
        "last_error_message": info.last_error_message,
        "has_custom_certificate": info.has_custom_certificate,
        "max_connections": info.max_connections,
    }


@router.post("/webhook")
async def telegram_webhook(request: Request):
    """Receive an update from Telegram and process it through the bot application."""
    # Verify the secret token header
    if settings.telegram_webhook_secret:
        header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if header_secret != settings.telegram_webhook_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    bot_app = request.app.state.bot_app
    if not bot_app:
        raise HTTPException(status_code=503, detail="Telegram bot not initialized")

    body = await request.json()
    update = Update.de_json(body, bot_app.bot)
    await bot_app.process_update(update)

    return {"ok": True}
