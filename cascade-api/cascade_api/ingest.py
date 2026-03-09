import json
import logging
import random
from pathlib import Path

from cascade_memory import MemoryClient
from cascade_api.consent import ConsentConfig, set_consent
from cascade_api.permissions import classify_sensitivity, PRIVATE_SOURCES

logger = logging.getLogger(__name__)

SOURCE_TYPE_MAP = {
    "social": "social",
    "bank": "finance",
    "ai_chat": "ai_chat",
    "calendar": "calendar",
    "email": "email",
    "lifelog": "lifelog",
    "files": "files",
}

JSONL_FILES = [
    "lifelog.jsonl",
    "conversations.jsonl",
    "emails.jsonl",
    "calendar.jsonl",
    "social_posts.jsonl",
    "transactions.jsonl",
    "files_index.jsonl",
]

async def ingest_persona(
    client: MemoryClient,
    tenant_id: str,
    persona_dir: Path,
) -> dict:
    """Ingest all JSONL files for a persona into cascade-memory."""
    tenant = client.for_tenant(tenant_id)
    records = []
    source_id_to_memory_id: dict[str, str] = {}
    pending_refs: list[tuple[str, str]] = []
    stats = {"records_ingested": 0, "links_created": 0}

    for filename in JSONL_FILES:
        filepath = persona_dir / filename
        if not filepath.exists():
            continue
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))

    for i, record in enumerate(records):
        if i > 0 and i % 100 == 0:
            logger.info(f"  {i}/{len(records)} records ingested...")

        sensitivity = classify_sensitivity(record)
        source = record.get("source", "unknown")
        type_suffix = SOURCE_TYPE_MAP.get(source, source)
        memory_type = f"{sensitivity}_{type_suffix}"

        memory_id = await tenant.save(
            content=record["text"],
            memory_type=memory_type,
            tags=record.get("tags", []),
            source_id=record.get("id"),
        )

        source_id_to_memory_id[record["id"]] = memory_id
        stats["records_ingested"] += 1

        for ref in record.get("refs", []):
            pending_refs.append((record["id"], ref))

    for source_record_id, ref_target_id in pending_refs:
        source_mem_id = source_id_to_memory_id.get(source_record_id)
        target_mem_id = source_id_to_memory_id.get(ref_target_id)
        if source_mem_id and target_mem_id:
            await tenant.link(source_mem_id, target_mem_id, "cross_reference")
            stats["links_created"] += 1

    # Cross-source similarity linking: sample memories and find connections
    all_memory_ids = list(source_id_to_memory_id.values())
    sample_size = min(200, len(all_memory_ids))
    sampled = random.sample(all_memory_ids, sample_size) if len(all_memory_ids) > sample_size else all_memory_ids

    logger.info(f"  Cross-source linking: sampling {len(sampled)} memories...")
    linked_pairs: set[tuple[str, str]] = set()
    # Collect existing cross_reference pairs to avoid duplicates
    for src_id, tgt_id in [(source_id_to_memory_id.get(s), source_id_to_memory_id.get(t)) for s, t in pending_refs]:
        if src_id and tgt_id:
            linked_pairs.add((src_id, tgt_id))
            linked_pairs.add((tgt_id, src_id))

    for mem_id in sampled:
        mem = await client.store.get(tenant_id, mem_id)
        if not mem or mem.embedding is None:
            continue
        try:
            similar = await client.store.search(tenant_id, mem.embedding, count=6, threshold=0.3)
            for result in similar:
                other_id = result.memory.id
                if other_id == mem_id:
                    continue
                if (mem_id, other_id) in linked_pairs:
                    continue
                # Only link across different source types for cross-source connections
                if result.memory.memory_type != mem.memory_type:
                    await tenant.link(mem_id, other_id, "related")
                    linked_pairs.add((mem_id, other_id))
                    linked_pairs.add((other_id, mem_id))
                    stats["links_created"] += 1
        except Exception as e:
            logger.warning(f"  Cross-source linking failed for {mem_id[:8]}: {e}")

    logger.info(f"  Cross-source linking done: {stats['links_created']} total links")

    profile_path = persona_dir / "persona_profile.json"
    if profile_path.exists():
        with open(profile_path) as f:
            profile = json.load(f)

        await tenant.core.append("Profile", f"- Name: {profile.get('name', 'Unknown')}")
        if profile.get("age"):
            await tenant.core.append("Profile", f"- Age: {profile['age']}")
        if profile.get("location"):
            await tenant.core.append("Profile", f"- Location: {profile['location']}")
        if profile.get("job"):
            await tenant.core.append("Profile", f"- Job: {profile['job']}")

        for goal in profile.get("goals", []):
            await tenant.core.append("Goals", f"- {goal}")

        personality = profile.get("personality", {})
        if personality.get("communication_style"):
            await tenant.core.append("Personality", f"- Communication: {personality['communication_style']}")

    # Load consent.json — the dataset provides a license-level consent file.
    # We honor its constraints (allowed_uses, retention) and derive per-source
    # sharing defaults from the actual data sources present in this persona.
    consent_path = persona_dir / "consent.json"
    dataset_consent = None
    if consent_path.exists():
        with open(consent_path) as f:
            dataset_consent = json.load(f)
        logger.info(
            f"  Dataset consent: allowed_uses={dataset_consent.get('allowed_uses')}, "
            f"retention={dataset_consent.get('retention')}"
        )

    # Build per-source consent from what sources this persona actually has.
    # Sources with sensitive content default to owner_only; others to public.
    sources_present: set[str] = set()
    for record in records:
        src = record.get("source", "")
        if src:
            sources_present.add(src)

    source_consent: dict[str, str] = {}
    for src in sources_present:
        if src in PRIVATE_SOURCES:
            source_consent[src] = "owner_only"
        else:
            source_consent[src] = "public"

    config = ConsentConfig(sources=source_consent)

    # Attach dataset-level metadata so it travels with the export
    if dataset_consent:
        config.dataset_license = {
            "allowed_uses": dataset_consent.get("allowed_uses", []),
            "prohibited_uses": dataset_consent.get("prohibited_uses", []),
            "retention": dataset_consent.get("retention"),
        }

    set_consent(tenant_id, config)
    logger.info(f"  Consent config for {tenant_id}: {len(sources_present)} sources configured")

    return stats
