import asyncio
import logging

from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters

from cascade_memory import MemoryClient
from cascade_api.config import BotConfig
from cascade_api.handlers import make_message_handler, make_export_handler

logger = logging.getLogger(__name__)


async def create_bot_app(
    config: BotConfig,
    memory_client: MemoryClient,
) -> Application:
    """Create a Telegram bot Application for a single persona."""
    app = Application.builder().token(config.token).build()

    message_handler = make_message_handler(config, memory_client)
    export_handler = make_export_handler(config, memory_client)

    app.add_handler(CommandHandler("export", export_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    return app


async def run_all_bots(
    configs: list[BotConfig],
    memory_client: MemoryClient,
):
    """Start all bots in polling mode concurrently."""
    apps = []
    for config in configs:
        app = await create_bot_app(config, memory_client)
        apps.append((config, app))
        logger.info(f"Bot '{config.name}' (tenant: {config.tenant_id}) initialized")

    for config, app in apps:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info(f"Bot '{config.name}' polling started")

    print(f"\n{len(apps)} bots running. Press Ctrl+C to stop.\n")
    for config, _ in apps:
        owner_str = f" (owner: {config.owner_chat_id})" if config.owner_chat_id else " (no owner)"
        print(f"  - {config.name} [{config.tenant_id}]{owner_str}")
    print()

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        for config, app in apps:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
            logger.info(f"Bot '{config.name}' stopped")
