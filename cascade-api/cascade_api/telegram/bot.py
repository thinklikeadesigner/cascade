"""Telegram bot initialization — runs inside FastAPI process.

Handles incoming messages only. Scheduling is pull-based via cron endpoints.
The bot runs in webhook mode: Telegram pushes updates to our endpoint.
"""

from __future__ import annotations

import structlog
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from cascade_api.config import settings
from cascade_api.telegram.handlers import handle_start, handle_message

log = structlog.get_logger()


def create_bot() -> Application | None:
    """Create the Telegram bot application. Returns None if no token configured."""
    if not settings.telegram_bot_token:
        log.warning("telegram.no_token", msg="TELEGRAM_BOT_TOKEN not set, bot disabled")
        return None

    app = Application.builder().token(settings.telegram_bot_token).build()

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    log.info("telegram.bot_created")
    return app
