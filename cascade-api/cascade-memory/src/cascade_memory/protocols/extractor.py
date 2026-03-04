"""MemoryExtractor protocol — LLM-based fact extraction."""
from __future__ import annotations

from typing import Protocol

from cascade_memory.models import Contradiction, ExtractedMemory, MemoryRecord


class MemoryExtractor(Protocol):
    async def extract(self, conversation_text: str) -> list[ExtractedMemory]: ...

    async def check_contradictions(
        self, new_fact: str, existing_memories: list[MemoryRecord],
    ) -> list[Contradiction]:
        return []
