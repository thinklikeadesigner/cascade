import pytest
import json

from cascade_memory import MemoryClient
from cascade_memory.stores.memory import InMemoryStore
from cascade_memory.embedders.fake import FakeEmbedder


@pytest.fixture
def memory_client():
    return MemoryClient(
        store=InMemoryStore(),
        embedder=FakeEmbedder(),
    )


@pytest.fixture
def persona_dir(tmp_path):
    """Create a minimal persona directory with test data."""
    profile = {
        "persona_id": "p_test",
        "name": "Test User",
        "age": 30,
        "location": "Austin, TX",
        "job": "Engineer",
        "goals": ["Ship MVP"],
        "pain_points": ["Too many meetings"],
        "personality": {"communication_style": "direct"},
    }
    (tmp_path / "persona_profile.json").write_text(json.dumps(profile))

    lifelog = [
        {"id": "ll_01", "ts": "2024-01-08T10:00:00Z", "source": "lifelog", "type": "activity", "text": "Back-to-back meetings all day", "tags": ["work"], "refs": [], "pii_level": "synthetic"},
        {"id": "ll_02", "ts": "2024-01-09T22:00:00Z", "source": "lifelog", "type": "reflection", "text": "Feeling burned out lately", "tags": ["health"], "refs": ["ll_01"], "pii_level": "synthetic"},
    ]
    with open(tmp_path / "lifelog.jsonl", "w") as f:
        for r in lifelog:
            f.write(json.dumps(r) + "\n")

    social = [
        {"id": "s_01", "ts": "2024-01-10T12:00:00Z", "source": "social", "type": "post", "text": "Shipped the new dashboard!", "tags": ["work"], "refs": [], "pii_level": "synthetic"},
    ]
    with open(tmp_path / "social_posts.jsonl", "w") as f:
        for r in social:
            f.write(json.dumps(r) + "\n")

    txns = [
        {"id": "t_01", "ts": "2024-01-05T17:00:00Z", "source": "bank", "type": "transaction", "text": "$85.00 - Easy Tiger", "tags": ["social", "dining"], "refs": [], "pii_level": "synthetic"},
    ]
    with open(tmp_path / "transactions.jsonl", "w") as f:
        for r in txns:
            f.write(json.dumps(r) + "\n")

    return tmp_path


@pytest.mark.asyncio
async def test_ingest_creates_memories(memory_client, persona_dir):
    from cascade_api.ingest import ingest_persona

    await memory_client.initialize()
    stats = await ingest_persona(memory_client, "p_test", persona_dir)

    assert stats["records_ingested"] == 4  # 2 lifelog + 1 social + 1 transaction
    assert stats["links_created"] >= 1  # ll_02 refs ll_01


@pytest.mark.asyncio
async def test_ingest_classifies_sensitivity(memory_client, persona_dir):
    from cascade_api.ingest import ingest_persona

    await memory_client.initialize()
    await ingest_persona(memory_client, "p_test", persona_dir)

    memories = await memory_client.store.list("p_test")

    types = {m.memory_type for m in memories}
    assert "public_social" in types
    assert "private_finance" in types


@pytest.mark.asyncio
async def test_ingest_builds_core_memory(memory_client, persona_dir):
    from cascade_api.ingest import ingest_persona

    await memory_client.initialize()
    await ingest_persona(memory_client, "p_test", persona_dir)

    tenant = memory_client.for_tenant("p_test")
    content, version = await tenant.core.read()
    assert "Test User" in content
    assert "Ship MVP" in content


@pytest.mark.asyncio
async def test_ingest_creates_ref_links(memory_client, persona_dir):
    from cascade_api.ingest import ingest_persona

    await memory_client.initialize()
    await ingest_persona(memory_client, "p_test", persona_dir)

    memories = await memory_client.store.list("p_test")
    source_ids = {m.source_id: m.id for m in memories}

    if "ll_01" in source_ids and "ll_02" in source_ids:
        links = await memory_client.store.get_links("p_test", source_ids["ll_02"])
        assert len(links) >= 1
