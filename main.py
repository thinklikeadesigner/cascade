import asyncio
import logging
from pathlib import Path

from cascade_memory import MemoryClient
from cascade_memory.stores.memory import InMemoryStore
from cascade_memory.embedders.fake import FakeEmbedder

from cascade_api.config import load_bot_configs
from cascade_api.ingest import ingest_persona
from cascade_api.multi_bot import run_all_bots

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent / "data"

PERSONA_DIRS = {
    "p01": DATA_DIR / "persona_p01",
    "p02": DATA_DIR / "persona_p02",
    "p05": DATA_DIR / "persona_p05",
}


async def main():
    # Initialize memory client
    # Swap to GeminiEmbedder + SupabaseStore for production
    client = MemoryClient(
        store=InMemoryStore(),
        embedder=FakeEmbedder(),
    )
    await client.initialize()

    # Ingest persona data
    for tenant_id, persona_dir in PERSONA_DIRS.items():
        if persona_dir.exists():
            logger.info(f"Ingesting {tenant_id} from {persona_dir}...")
            stats = await ingest_persona(client, tenant_id, persona_dir)
            logger.info(f"  {stats['records_ingested']} records, {stats['links_created']} links")
        else:
            logger.warning(f"Persona dir not found: {persona_dir}")

    # Load bot configs from env
    configs = load_bot_configs()
    if not configs:
        print("No bot tokens configured. Set TELEGRAM_BOT_TOKEN_JORDAN, etc. in .env")
        return

    # Run all bots
    await run_all_bots(configs, client)


if __name__ == "__main__":
    asyncio.run(main())
