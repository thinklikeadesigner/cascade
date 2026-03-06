"""Verify protocols are importable and structurally correct."""

from cascade_api.memory.protocols.store import MemoryStore
from cascade_api.memory.protocols.embedder import Embedder
from cascade_api.memory.protocols.extractor import MemoryExtractor


def test_memory_store_has_required_methods():
    methods = [
        "get_core",
        "upsert_core",
        "save",
        "save_batch",
        "get",
        "list",
        "update",
        "search",
        "delete",
        "delete_all",
        "add_link",
        "get_links",
        "update_decay_scores",
        "touch_accessed",
        "initialize",
    ]
    for m in methods:
        assert hasattr(MemoryStore, m), f"MemoryStore missing {m}"


def test_embedder_has_required_methods():
    assert hasattr(Embedder, "embed")
    assert hasattr(Embedder, "embed_batch")
    assert hasattr(Embedder, "dimensions")


def test_extractor_has_required_methods():
    assert hasattr(MemoryExtractor, "extract")
    assert hasattr(MemoryExtractor, "check_contradictions")
