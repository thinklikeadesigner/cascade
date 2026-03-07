from cascade_memory import SearchResult

PRIVATE_SOURCES = {"bank", "ai_chat"}
PRIVATE_TAGS = {"therapy", "health", "relationship", "anxiety", "personal", "mental_health", "finance"}
PUBLIC_SOURCES = {"social", "files"}


def classify_sensitivity(record: dict) -> str:
    source = record.get("source", "")
    tags = set(record.get("tags", []))

    if source in PRIVATE_SOURCES:
        return "private"
    if source in PUBLIC_SOURCES:
        return "public"

    # For calendar, email, lifelog: check tags
    if tags & PRIVATE_TAGS:
        return "private"
    if "work" in tags or "humor" in tags:
        return "public"

    return "private"  # default to private (safe)


def filter_by_permission(
    results: list[SearchResult],
    context: str,  # "group", "dm_owner", "dm_stranger"
) -> list[SearchResult]:
    if context == "dm_stranger":
        return []
    if context == "dm_owner":
        return results
    # group: public only
    return [r for r in results if r.memory.memory_type.startswith("public_")]
