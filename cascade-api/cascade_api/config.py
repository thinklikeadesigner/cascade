import os
from dataclasses import dataclass

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_key: str = ""
    anthropic_api_key: str = ""
    database_url: str = ""
    port: int = 8000
    data_dir: str = "../data"
    log_level: str = "info"
    sentry_dsn: str = ""
    posthog_api_key: str = ""
    posthog_host: str = "https://us.i.posthog.com"
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_founding_price_id: str = ""
    stripe_standard_price_id: str = ""
    frontend_url: str = ""
    telegram_bot_token: str = ""
    telegram_webhook_url: str = ""  # e.g. https://your-app.up.railway.app/api/telegram/webhook
    telegram_webhook_secret: str = ""  # secret token for webhook verification
    cron_secret: str = ""
    gemini_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()


@dataclass
class BotConfig:
    name: str
    tenant_id: str
    token: str
    owner_chat_id: int | None = None


def load_bot_configs() -> list[BotConfig]:
    configs = []

    for name, tenant_id, env_key in [
        ("Jordan", "p01", "TELEGRAM_BOT_TOKEN_JORDAN"),
        ("Maya", "p02", "TELEGRAM_BOT_TOKEN_MAYA"),
        ("Theo", "p05", "TELEGRAM_BOT_TOKEN_THEO"),
    ]:
        token = os.environ.get(env_key)
        if token:
            configs.append(BotConfig(name=name, tenant_id=tenant_id, token=token))

    your_token = os.environ.get("TELEGRAM_BOT_TOKEN_YOU")
    owner_id = os.environ.get("TELEGRAM_OWNER_CHAT_ID")
    if your_token:
        configs.append(BotConfig(
            name="You",
            tenant_id="k2",
            token=your_token,
            owner_chat_id=int(owner_id) if owner_id else None,
        ))

    return configs
