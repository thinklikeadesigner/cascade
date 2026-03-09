import os
from dataclasses import dataclass


@dataclass
class BotConfig:
    name: str
    tenant_id: str
    token: str
    owner_chat_id: int | None = None


def load_bot_configs() -> list[BotConfig]:
    configs = []
    owner_id = os.environ.get("TELEGRAM_OWNER_CHAT_ID")
    owner_chat_id = int(owner_id) if owner_id else None

    for name, tenant_id, env_key in [
        ("Jordan", "p01", "TELEGRAM_BOT_TOKEN_JORDAN"),
        ("Maya", "p02", "TELEGRAM_BOT_TOKEN_MAYA"),
        ("Theo", "p05", "TELEGRAM_BOT_TOKEN_THEO"),
    ]:
        token = os.environ.get(env_key)
        if token:
            # Jordan's owner gets set so we can demo /privacy, /forget, /export in DM
            bot_owner = owner_chat_id if tenant_id == "p01" else None
            configs.append(BotConfig(name=name, tenant_id=tenant_id, token=token, owner_chat_id=bot_owner))

    your_token = os.environ.get("TELEGRAM_BOT_TOKEN_YOU")
    if your_token:
        configs.append(BotConfig(
            name="You",
            tenant_id="k2",
            token=your_token,
            owner_chat_id=owner_chat_id,
        ))

    return configs
