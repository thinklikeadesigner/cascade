from contextlib import asynccontextmanager

import logging

import sentry_sdk
import structlog
from fastapi import FastAPI

from cascade_api.config import settings
from cascade_api.api.router import api_router
from cascade_api.telegram.bot import create_bot

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        environment="production",
    )

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(
        logging.getLevelName(settings.log_level.upper())
    ),
)

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app):
    bot_app = create_bot()
    app.state.bot_app = bot_app
    if bot_app:
        await bot_app.initialize()
        if settings.telegram_webhook_url:
            try:
                await bot_app.bot.set_webhook(
                    url=settings.telegram_webhook_url,
                    secret_token=settings.telegram_webhook_secret or None,
                )
                log.info("telegram.webhook_set", url=settings.telegram_webhook_url)
            except Exception as e:
                log.error("telegram.webhook_set_failed", error=str(e), url=settings.telegram_webhook_url)
        else:
            log.warning("telegram.no_webhook_url", msg="TELEGRAM_WEBHOOK_URL not set, webhook not registered")
    yield
    if bot_app:
        try:
            await bot_app.bot.delete_webhook()
        except Exception:
            log.warning("telegram.webhook_delete_failed", msg="Could not delete webhook on shutdown")
        await bot_app.shutdown()


app = FastAPI(title="Cascade API", version="0.1.0", lifespan=lifespan)

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cascade-api"}
