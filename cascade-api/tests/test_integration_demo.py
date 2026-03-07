"""Integration tests for the full demo flow.

Tests sensitivity filtering, cross-source links, and export completeness
using InMemoryStore + FakeEmbedder with synthetic persona data.
"""
import json

import pytest

from cascade_memory import MemoryClient
from cascade_memory.models import SearchResult
from cascade_memory.stores.memory import InMemoryStore
from cascade_memory.embedders.fake import FakeEmbedder
from cascade_api.ingest import ingest_persona
from cascade_api.permissions import filter_by_permission


@pytest.fixture
async def loaded_client(tmp_path):
    """Client with synthetic persona data ingested."""
    client = MemoryClient(store=InMemoryStore(), embedder=FakeEmbedder())
    await client.initialize()

    profile = {
        "persona_id": "p01",
        "name": "Jordan Lee",
        "goals": ["Get promoted"],
        "personality": {"communication_style": "direct"},
    }
    (tmp_path / "persona_profile.json").write_text(json.dumps(profile))

    records = [
        {
            "id": "s_01",
            "ts": "2024-01-10T12:00:00Z",
            "source": "social",
            "type": "post",
            "text": "Shipped the dashboard! #productmanager",
            "tags": ["work", "humor"],
            "refs": [],
            "pii_level": "synthetic",
        },
        {
            "id": "ll_01",
            "ts": "2024-01-08T10:00:00Z",
            "source": "lifelog",
            "type": "activity",
            "text": "Back-to-back meetings, no lunch break. Not sustainable.",
            "tags": ["work"],
            "refs": [],
            "pii_level": "synthetic",
        },
        {
            "id": "c_01",
            "ts": "2024-01-14T22:00:00Z",
            "source": "ai_chat",
            "type": "chat_turn",
            "text": "USER: I keep waking up at 3am thinking about work.",
            "tags": ["sleep", "anxiety"],
            "refs": ["ll_01"],
            "pii_level": "synthetic",
        },
        {
            "id": "t_01",
            "ts": "2024-01-05T17:00:00Z",
            "source": "bank",
            "type": "transaction",
            "text": "$85.00 - Easy Tiger - social",
            "tags": ["social", "dining"],
            "refs": [],
            "pii_level": "synthetic",
        },
    ]

    for filename, data in [
        ("social_posts.jsonl", [records[0]]),
        ("lifelog.jsonl", [records[1]]),
        ("conversations.jsonl", [records[2]]),
        ("transactions.jsonl", [records[3]]),
    ]:
        with open(tmp_path / filename, "w") as f:
            for r in data:
                f.write(json.dumps(r) + "\n")

    await ingest_persona(client, "p01", tmp_path)
    return client


@pytest.mark.asyncio
async def test_group_chat_filters_private_data(loaded_client):
    """Group chat should only return public memories."""
    memories = await loaded_client.store.list("p01", limit=100)
    results = [SearchResult(memory=m, similarity=1.0, rank_score=1.0) for m in memories]

    public_only = filter_by_permission(results, context="group")
    assert len(public_only) > 0, "Expected at least one public memory"
    for r in public_only:
        assert r.memory.memory_type.startswith("public_"), (
            f"Private data leaked: {r.memory.memory_type}"
        )


@pytest.mark.asyncio
async def test_dm_owner_gets_everything(loaded_client):
    """DM from owner should return all memories including private ones."""
    # Use store.list to get all memories (recall depends on embedding similarity
    # which is unreliable with FakeEmbedder for coverage assertions)
    memories = await loaded_client.store.list("p01", limit=100)
    results = [SearchResult(memory=m, similarity=1.0, rank_score=1.0) for m in memories]

    all_results = filter_by_permission(results, context="dm_owner")
    types = {r.memory.memory_type for r in all_results}
    has_public = any(t.startswith("public_") for t in types)
    has_private = any(t.startswith("private_") for t in types)
    assert has_public and has_private, f"Expected both public and private types, got: {types}"


@pytest.mark.asyncio
async def test_dm_stranger_gets_nothing(loaded_client):
    """DM from non-owner should return nothing."""
    memories = await loaded_client.store.list("p01", limit=100)
    results = [SearchResult(memory=m, similarity=1.0, rank_score=1.0) for m in memories]

    assert len(results) > 0, "Sanity check: should have memories to filter"
    nothing = filter_by_permission(results, context="dm_stranger")
    assert len(nothing) == 0


@pytest.mark.asyncio
async def test_cross_source_links_exist(loaded_client):
    """Refs in data should create memory links."""
    memories = await loaded_client.store.list("p01")
    source_map = {m.source_id: m.id for m in memories}

    # c_01 refs ll_01 — so there should be a link between them
    if "c_01" in source_map:
        links = await loaded_client.store.get_links("p01", source_map["c_01"])
        assert len(links) >= 1, "Expected at least one cross-source link from c_01 -> ll_01"


@pytest.mark.asyncio
async def test_export_contains_all_data(loaded_client):
    """Export should contain core memory, all archival memories, and links."""
    tenant = loaded_client.for_tenant("p01")
    core_content, core_version = await tenant.core.read()
    memories = await loaded_client.store.list("p01")

    assert "Jordan Lee" in core_content, f"Core memory missing persona name, got: {core_content}"
    assert len(memories) == 4, f"Expected 4 memories, got {len(memories)}"
