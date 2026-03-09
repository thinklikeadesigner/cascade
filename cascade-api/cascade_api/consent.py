"""User-controlled consent layer for memory sharing.

Each tenant has a consent config that controls per-source sharing levels:
  - owner_only: visible only in private DM and personal export
  - public: visible in group chats and to other apps

The config is stored in the memory store alongside core memory,
and travels with the Portable Memory Format export.
"""

import logging

logger = logging.getLogger(__name__)

# All data sources from the hackathon dataset + Cascade
ALL_SOURCES = [
    "calendar",
    "email",
    "social",
    "lifelog",
    "bank",
    "ai_chat",
    "files",
    "goal_context",
    "fact",
    "preference",
    "pattern",
]

# Defaults: financial and AI chat data are owner-only, everything else is public
DEFAULT_CONSENT = {
    "calendar": "public",
    "email": "public",
    "social": "public",
    "lifelog": "public",
    "bank": "owner_only",
    "ai_chat": "owner_only",
    "files": "public",
    "goal_context": "public",
    "fact": "public",
    "preference": "owner_only",
    "pattern": "owner_only",
}

VALID_LEVELS = {"owner_only", "public"}

# Tags that override source-level consent to owner_only regardless
SENSITIVE_TAGS = {
    "therapy", "anxiety", "mental_health", "finance", "salary", "debt",
    "health", "personal", "family", "relationship",
}


class ConsentConfig:
    """Per-tenant consent configuration."""

    def __init__(self, sources: dict[str, str] | None = None):
        self.sources = dict(DEFAULT_CONSENT)
        self.dataset_license: dict | None = None  # upstream license constraints
        if sources:
            for source, level in sources.items():
                if level in VALID_LEVELS:
                    self.sources[source] = level

    def get_level(self, source: str) -> str:
        """Get sharing level for a source type."""
        return self.sources.get(source, "owner_only")

    def set_level(self, source: str, level: str) -> bool:
        """Set sharing level. Returns True if valid."""
        if level not in VALID_LEVELS:
            return False
        self.sources[source] = level
        return True

    def is_public(self, source: str, tags: list[str] | None = None) -> bool:
        """Check if a source is publicly shareable, considering sensitive tags."""
        if tags and set(tags) & SENSITIVE_TAGS:
            return False
        return self.get_level(source) == "public"

    def to_dict(self) -> dict:
        d = {"sources": self.sources}
        if self.dataset_license:
            d["dataset_license"] = self.dataset_license
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ConsentConfig":
        return cls(sources=data.get("sources"))

    def summary(self) -> str:
        """Human-readable summary for Telegram."""
        lines = ["Your privacy settings:\n"]
        for source in ALL_SOURCES:
            level = self.get_level(source)
            icon = "🔒" if level == "owner_only" else "🌐"
            lines.append(f"  {icon} {source}: {level}")
        lines.append(f"\nSensitive tags (always private): {', '.join(sorted(SENSITIVE_TAGS))}")
        lines.append("\nChange with: /privacy set <source> <public|owner_only>")
        return "\n".join(lines)


# ── Storage: consent configs keyed by tenant ──

_consent_configs: dict[str, ConsentConfig] = {}


def get_consent(tenant_id: str) -> ConsentConfig:
    """Get or create consent config for a tenant."""
    if tenant_id not in _consent_configs:
        _consent_configs[tenant_id] = ConsentConfig()
    return _consent_configs[tenant_id]


def set_consent(tenant_id: str, config: ConsentConfig):
    """Store consent config for a tenant."""
    _consent_configs[tenant_id] = config


def extract_source_from_memory_type(memory_type: str) -> str:
    """Extract the source from a memory_type like 'public_email' or 'private_bank'."""
    # Strip sensitivity prefix if present
    for prefix in ("public_", "private_"):
        if memory_type.startswith(prefix):
            return memory_type[len(prefix):]
    return memory_type
