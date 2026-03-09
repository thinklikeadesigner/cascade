from cascade_memory import SearchResult

from cascade_api.consent import (
    ConsentConfig,
    extract_source_from_memory_type,
    get_consent,
    SENSITIVE_TAGS,
)

# Keep for backward compat during ingestion — classify_sensitivity still
# stamps memory_type so we know the source at query time.
PRIVATE_SOURCES = {"bank", "ai_chat"}
PRIVATE_TAGS = SENSITIVE_TAGS
PUBLIC_SOURCES = {"social", "files"}


def classify_sensitivity(record: dict) -> str:
    """Classify during ingestion. Consent doesn't change what's stored,
    only what's shared — so we still tag the source type."""
    source = record.get("source", "")
    tags = set(record.get("tags", []))

    if source in PRIVATE_SOURCES:
        return "private"
    if source in PUBLIC_SOURCES:
        return "public"

    if tags & PRIVATE_TAGS:
        return "private"

    return "public"


def filter_by_permission(
    results: list[SearchResult],
    context: str,  # "group", "dm_owner", "dm_stranger"
    tenant_id: str | None = None,
) -> list[SearchResult]:
    if context == "dm_stranger":
        return []
    if context == "dm_owner":
        return results

    # Group chat: use consent config to determine what's public
    consent = get_consent(tenant_id) if tenant_id else ConsentConfig()
    filtered = []
    for r in results:
        source = extract_source_from_memory_type(r.memory.memory_type)
        if consent.is_public(source, r.memory.tags):
            filtered.append(r)
    return filtered
