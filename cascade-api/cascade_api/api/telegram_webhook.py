"""Telegram webhook endpoint — receives updates pushed by Telegram."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Request, HTTPException
from telegram import Update

from cascade_api.config import settings

log = structlog.get_logger()

router = APIRouter(prefix="/api/telegram", tags=["telegram"])


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
