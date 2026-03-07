import pytest
from cascade_api.permissions import classify_sensitivity, filter_by_permission


def test_social_post_is_public():
    record = {"source": "social", "tags": ["work", "humor"]}
    assert classify_sensitivity(record) == "public"


def test_bank_transaction_is_private():
    record = {"source": "bank", "tags": ["dining"]}
    assert classify_sensitivity(record) == "private"


def test_ai_chat_is_private():
    record = {"source": "ai_chat", "tags": ["sleep", "anxiety"]}
    assert classify_sensitivity(record) == "private"


def test_work_calendar_is_public():
    record = {"source": "calendar", "tags": ["work", "meeting"]}
    assert classify_sensitivity(record) == "public"


def test_therapy_calendar_is_private():
    record = {"source": "calendar", "tags": ["therapy"]}
    assert classify_sensitivity(record) == "private"


def test_work_email_is_public():
    record = {"source": "email", "tags": ["work", "team"]}
    assert classify_sensitivity(record) == "public"


def test_personal_email_is_private():
    record = {"source": "email", "tags": ["personal", "family"]}
    assert classify_sensitivity(record) == "private"


def test_health_lifelog_is_private():
    record = {"source": "lifelog", "tags": ["health"]}
    assert classify_sensitivity(record) == "private"


def test_work_lifelog_is_public():
    record = {"source": "lifelog", "tags": ["work"]}
    assert classify_sensitivity(record) == "public"


def test_relationship_lifelog_is_private():
    record = {"source": "lifelog", "tags": ["relationship"]}
    assert classify_sensitivity(record) == "private"


def test_files_index_is_public():
    record = {"source": "files", "tags": ["work"]}
    assert classify_sensitivity(record) == "public"


def test_filter_public_only():
    from cascade_memory import SearchResult, MemoryRecord
    results = [
        SearchResult(
            memory=MemoryRecord(id="1", content="public post", memory_type="public_social", tags=[]),
            similarity=0.9, rank_score=0.9,
        ),
        SearchResult(
            memory=MemoryRecord(id="2", content="private tx", memory_type="private_finance", tags=[]),
            similarity=0.8, rank_score=0.8,
        ),
    ]
    filtered = filter_by_permission(results, context="group")
    assert len(filtered) == 1
    assert filtered[0].memory.id == "1"


def test_filter_dm_owner_gets_all():
    from cascade_memory import SearchResult, MemoryRecord
    results = [
        SearchResult(
            memory=MemoryRecord(id="1", content="public", memory_type="public_social", tags=[]),
            similarity=0.9, rank_score=0.9,
        ),
        SearchResult(
            memory=MemoryRecord(id="2", content="private", memory_type="private_finance", tags=[]),
            similarity=0.8, rank_score=0.8,
        ),
    ]
    filtered = filter_by_permission(results, context="dm_owner")
    assert len(filtered) == 2


def test_filter_dm_stranger_gets_nothing():
    from cascade_memory import SearchResult, MemoryRecord
    results = [
        SearchResult(
            memory=MemoryRecord(id="1", content="public", memory_type="public_social", tags=[]),
            similarity=0.9, rank_score=0.9,
        ),
    ]
    filtered = filter_by_permission(results, context="dm_stranger")
    assert len(filtered) == 0
