"""Data models for cascade-memory."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MemoryRecord:
    id: str
    content: str
    memory_type: str
    tags: list[str] = field(default_factory=list)
    confidence: float = 1.0
    decay_score: float = 1.0
    status: str = "active"
    embedding: list[float] | None = None
    superseded_by: str | None = None
    source_id: str | None = None
    created_at: datetime | None = None
    last_accessed_at: datetime | None = None
    last_confirmed_at: datetime | None = None


@dataclass
class SearchResult:
    memory: MemoryRecord
    similarity: float
    rank_score: float


@dataclass
class MemoryLink:
    id: str
    source_id: str
    target_id: str
    link_type: str


@dataclass
class ExtractedMemory:
    content: str
    memory_type: str
    tags: list[str]
    confidence: float = 1.0


@dataclass
class Contradiction:
    new_fact: str
    existing_memory_id: str
    existing_content: str
    explanation: str
