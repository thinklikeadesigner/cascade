"""Cron endpoints — hit by an external scheduler every 5 minutes.

Each endpoint verifies X-Cron-Secret, then calls the pull-based
scheduler functions. Idempotency is handled in scheduler.py via
the message_deliveries table, so calling these multiple times is safe.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Header, HTTPException, Request

from cascade_api.config import settings
from cascade_api.telegram.scheduler import (
    send_morning_messages,
    send_evening_messages,
    run_trial_check_pull,
    send_sunday_review_messages,
    send_monday_kickoff_messages,
)

log = structlog.get_logger()

router = APIRouter(prefix="/api/cron", tags=["cron"])


def _verify_secret(x_cron_secret: str | None):
    if not settings.cron_secret:
        raise HTTPException(status_code=500, detail="CRON_SECRET not configured")
    if x_cron_secret != settings.cron_secret:
        raise HTTPException(status_code=401, detail="Invalid cron secret")


def _get_bot(request: Request):
    """Get the Telegram Bot instance from app.state."""
    bot_app = request.app.state.bot_app
    if not bot_app:
        raise HTTPException(status_code=503, detail="Telegram bot not initialized")
    return bot_app.bot


@router.post("/morning")
async def cron_morning(request: Request, x_cron_secret: str | None = Header(default=None)):
    _verify_secret(x_cron_secret)
    bot = _get_bot(request)
    result = await send_morning_messages(bot)
    log.info("cron.morning", **result)
    return result


@router.post("/evening")
async def cron_evening(request: Request, x_cron_secret: str | None = Header(default=None)):
    _verify_secret(x_cron_secret)
    bot = _get_bot(request)
    result = await send_evening_messages(bot)
    log.info("cron.evening", **result)
    return result


@router.post("/trial-check")
async def cron_trial_check(request: Request, x_cron_secret: str | None = Header(default=None)):
    _verify_secret(x_cron_secret)
    bot = _get_bot(request)
    result = await run_trial_check_pull(bot)
    log.info("cron.trial_check", **result)
    return result


@router.post("/sunday-review")
async def cron_sunday_review(request: Request, x_cron_secret: str | None = Header(default=None)):
    _verify_secret(x_cron_secret)
    bot = _get_bot(request)
    result = await send_sunday_review_messages(bot)
    log.info("cron.sunday_review", **result)
    return result


@router.post("/monday-kickoff")
async def cron_monday_kickoff(request: Request, x_cron_secret: str | None = Header(default=None)):
    _verify_secret(x_cron_secret)
    bot = _get_bot(request)
    result = await send_monday_kickoff_messages(bot)
    log.info("cron.monday_kickoff", **result)
    return result
