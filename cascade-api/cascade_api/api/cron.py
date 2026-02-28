"""Cron endpoints — called by Railway cron every 15 minutes."""

from __future__ import annotations

from fastapi import APIRouter, Request, HTTPException
import structlog

from cascade_api.config import settings

log = structlog.get_logger()
router = APIRouter(prefix="/api/cron", tags=["cron"])


def _verify_cron_secret(request: Request):
    """Verify the X-Cron-Secret header matches the configured secret."""
    secret = request.headers.get("X-Cron-Secret")
    if not settings.cron_secret:
        log.warning("cron.no_secret_configured")
        return
    if secret != settings.cron_secret:
        raise HTTPException(status_code=403, detail="Invalid cron secret")


@router.post("/daily")
async def cron_daily(request: Request):
    """Send daily message to all eligible tenants at their preferred time."""
    _verify_cron_secret(request)

    from cascade_api.telegram.bot import create_bot
    from cascade_api.telegram.scheduler import send_daily_messages

    bot = create_bot().bot
    result = await send_daily_messages(bot)
    log.info("cron.daily", **result)
    return result


@router.post("/trial-check")
async def cron_trial_check(request: Request):
    """Check for trial-ended users and send payment nudge."""
    _verify_cron_secret(request)

    from cascade_api.telegram.bot import create_bot
    from cascade_api.telegram.scheduler import run_trial_check_pull

    bot = create_bot().bot
    result = await run_trial_check_pull(bot)
    log.info("cron.trial_check", **result)
    return result
