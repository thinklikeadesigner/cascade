import json
import logging
from io import BytesIO

import anthropic
from telegram import Update
from telegram.ext import ContextTypes

from cascade_memory import MemoryClient
from cascade_api.config import BotConfig
from cascade_api.permissions import filter_by_permission
from cascade_api.synthesize import synthesize_answer

logger = logging.getLogger(__name__)


def determine_context(update: Update, config: BotConfig) -> str:
    """Determine permission context from the update."""
    chat_type = update.effective_chat.type
    user_id = update.effective_user.id

    if chat_type in ("group", "supergroup"):
        return "group"
    if chat_type == "private":
        if config.owner_chat_id and user_id == config.owner_chat_id:
            return "dm_owner"
        return "dm_stranger"
    return "group"


def make_message_handler(config: BotConfig, memory_client: MemoryClient):
    """Create a message handler closure for a specific bot/persona."""
    tenant = memory_client.for_tenant(config.tenant_id)
    anthropic_client = anthropic.AsyncAnthropic()

    async def handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        question = update.message.text
        context = determine_context(update, config)

        if context == "dm_stranger":
            await update.message.reply_text("I only talk to my user in private.")
            return

        results = await tenant.recall(question, count=10, threshold=0.3)
        filtered = filter_by_permission(results, context)
        core_content, _ = await tenant.core.read()

        answer = await synthesize_answer(
            client=anthropic_client,
            persona_name=config.name,
            core_memory=core_content,
            results=filtered,
            question=question,
            context=context,
        )

        await update.message.reply_text(answer)

    return handler


def make_export_handler(config: BotConfig, memory_client: MemoryClient):
    """Create an /export handler that sends the user's memory as JSON."""
    tenant = memory_client.for_tenant(config.tenant_id)

    async def handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        context = determine_context(update, config)

        if context != "dm_owner":
            await update.message.reply_text("Export is only available to my user in a private chat.")
            return

        core_content, core_version = await tenant.core.read()
        memories = await memory_client.store.list(config.tenant_id)

        all_links = []
        for mem in memories:
            links = await memory_client.store.get_links(config.tenant_id, mem.id)
            for link in links:
                link_dict = {"source_id": link.source_id, "target_id": link.target_id, "link_type": link.link_type}
                if link_dict not in all_links:
                    all_links.append(link_dict)

        export = {
            "tenant_id": config.tenant_id,
            "persona_name": config.name,
            "core_memory": {"content": core_content, "version": core_version},
            "memories": [
                {
                    "id": m.id,
                    "content": m.content,
                    "memory_type": m.memory_type,
                    "tags": m.tags,
                    "confidence": m.confidence,
                    "decay_score": m.decay_score,
                    "source_id": m.source_id,
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in memories
            ],
            "links": all_links,
        }

        export_json = json.dumps(export, indent=2)
        buf = BytesIO(export_json.encode())
        buf.name = f"memory_export_{config.tenant_id}.json"
        await update.message.reply_document(
            document=buf,
            caption=f"Your memory export — {len(memories)} memories, {len(all_links)} connections.",
        )

    return handler
