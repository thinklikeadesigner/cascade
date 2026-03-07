import json
from pathlib import Path

from cascade_memory import MemoryClient
from cascade_api.permissions import classify_sensitivity

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

    for record in records:
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

    return stats
