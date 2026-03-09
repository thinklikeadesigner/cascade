import asyncio
import logging
import os
import pickle
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from cascade_memory import MemoryClient
from cascade_memory.stores.memory import InMemoryStore
from cascade_memory.embedders.fake import FakeEmbedder

from cascade_api.config import load_bot_configs
from cascade_api.consent import ConsentConfig, get_consent, set_consent, _consent_configs
from cascade_api.ingest import ingest_persona
from cascade_api.ingest_supabase import ingest_from_supabase
from cascade_api.multi_bot import run_all_bots
from cascade_api.ollama_embedder import OllamaEmbedder
from cascade_api.ollama_extractor import OllamaExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data" / "personadata" / "personas"
CACHE_FILE = Path(__file__).parent / ".memory_cache.pkl"

PERSONA_DIRS = {
    "p01": DATA_DIR / "persona_p01",
    "p02": DATA_DIR / "persona_p02",
    "p05": DATA_DIR / "persona_p05",
}


def save_store_cache(store: InMemoryStore):
    data = {
        "_core": store._core,
        "_memories": store._memories,
        "_tenant_memories": store._tenant_memories,
        "_links": store._links,
        "_embedding_dims": store._embedding_dims,
        "_consent": {tid: c.to_dict() for tid, c in _consent_configs.items()},
    }
    with open(CACHE_FILE, "wb") as f:
        pickle.dump(data, f)
    logger.info(f"Saved memory cache to {CACHE_FILE}")


def load_store_cache() -> InMemoryStore | None:
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "rb") as f:
            data = pickle.load(f)
        store = InMemoryStore()
        store._core = data["_core"]
        store._memories = data["_memories"]
        store._tenant_memories = data["_tenant_memories"]
        store._links = data["_links"]
        store._embedding_dims = data["_embedding_dims"]
        total = len(store._memories)
        embedded = sum(1 for m in store._memories.values() if m.embedding is not None)
        logger.info(f"Loaded cache: {total} memories ({embedded} with embeddings)")
        # Restore consent configs
        for tid, cdata in data.get("_consent", {}).items():
            set_consent(tid, ConsentConfig.from_dict(cdata))
        logger.info(f"Restored consent configs for {len(data.get('_consent', {}))} tenants")
        return store
    except Exception as e:
        logger.warning(f"Failed to load cache: {e}")
        return None


def build_embedder():
    """Build embedder — uses local Ollama with nomic-embed-text."""
    logger.info("Using OllamaEmbedder (nomic-embed-text, local)")
    return OllamaEmbedder()


async def main():
    embedder = build_embedder()
    extractor = OllamaExtractor()

    # Try loading from cache
    store = load_store_cache()
    if store:
        logger.info("Using cached memory store — skipping ingestion")
        client = MemoryClient(store=store, embedder=embedder, extractor=extractor)
    else:
        store = InMemoryStore()
        client = MemoryClient(store=store, embedder=embedder, extractor=extractor)
        await client.initialize()

        for tenant_id, persona_dir in PERSONA_DIRS.items():
            if persona_dir.exists():
                logger.info(f"Ingesting {tenant_id} from {persona_dir}...")
                stats = await ingest_persona(client, tenant_id, persona_dir)
                logger.info(f"  {stats['records_ingested']} records, {stats['links_created']} links")
            else:
                logger.warning(f"Persona dir not found: {persona_dir}")

        # Ingest existing Cascade data from Supabase for the "You" bot
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
        if supabase_url and supabase_key:
            from supabase import create_client
            supabase = create_client(supabase_url, supabase_key)
            # Pull all tenants from Supabase and ingest their data into "k2" memory
            try:
                tenants = supabase.table("tenants").select("id").execute()
                for t in tenants.data or []:
                    supa_tid = t["id"]
                    logger.info(f"Ingesting Supabase data for tenant {supa_tid[:8]}... into k2")
                    stats = await ingest_from_supabase(client, supabase, supa_tid, memory_tenant="k2")
                    logger.info(f"  Supabase ingest: {stats}")
            except Exception as e:
                logger.warning(f"Supabase ingest failed: {e}")
        else:
            logger.info("No SUPABASE_URL/SUPABASE_SERVICE_KEY — skipping Supabase ingest")

        save_store_cache(store)

    # Wire cache persistence so new memories survive restarts
    from cascade_api.handlers import set_save_cache_fn
    set_save_cache_fn(lambda: save_store_cache(store))

    configs = load_bot_configs()
    if not configs:
        print("No bot tokens configured. Set TELEGRAM_BOT_TOKEN_JORDAN, etc. in .env")
        return

    await run_all_bots(configs, client, persona_dirs=PERSONA_DIRS)


if __name__ == "__main__":
    asyncio.run(main())
