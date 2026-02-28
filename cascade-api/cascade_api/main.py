from contextlib import asynccontextmanager

import logging

import sentry_sdk
import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from cascade_api.config import settings
from cascade_api.api.router import api_router
from cascade_api.telegram.bot import create_bot
from cascade_api.observability.posthog_client import get_posthog

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
    bot_app = None
    try:
        bot_app = create_bot()
        if bot_app:
            await bot_app.initialize()
            log.info("telegram.initialized")
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
                log.warning("telegram.no_webhook_url")
    except Exception as e:
        log.error("telegram.startup_failed", error=str(e))
        bot_app = None
    app.state.bot_app = bot_app
    log.info("app.started")
    yield
    ph = get_posthog()
    if ph:
        ph.flush()
        ph.shutdown()
    if bot_app:
        try:
            await bot_app.bot.delete_webhook()
        except Exception:
            pass
        try:
            await bot_app.shutdown()
        except Exception:
            pass


app = FastAPI(title="Cascade API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://cascade-landing-beige.vercel.app",
        "https://cascade-flame.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "cascade-api"}
