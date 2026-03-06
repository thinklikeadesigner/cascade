"""AnthropicExtractor — extract memories from conversations via Claude."""

from __future__ import annotations

import json
import re

from cascade_api.memory.errors import ExtractionError
from cascade_api.memory.models import Contradiction, ExtractedMemory, MemoryRecord

EXTRACTION_PROMPT = """Extract key facts, decisions, preferences, and state changes from this conversation.
Return a JSON array of objects with these fields:
- content: the fact or preference (one sentence)
- memory_type: one of "fact", "preference", "pattern", "goal_context"
- tags: list of 1-3 context tags
- confidence: 0.0 to 1.0 (how confident you are this is worth remembering)

Rules:
- Skip small talk, acknowledgments, and transient details
- Each memory should be self-contained (understandable without context)
- Return [] if nothing is worth remembering

Return ONLY the JSON array, no other text."""

CONTRADICTION_PROMPT = """Compare this new fact against existing memories.
If any existing memory contradicts the new fact, explain the contradiction.

New fact: {new_fact}

Existing memories:
{existing}

Return a JSON array of contradictions (empty array if none):
[{{"existing_memory_id": "...", "explanation": "..."}}]

Return ONLY the JSON array."""


class AnthropicExtractor:
    def __init__(self, client, model: str = "claude-haiku-4-5-20251001", max_tokens: int = 512):
        self._client = client
        self._model = model
        self._max_tokens = max_tokens

    async def extract(self, conversation_text: str) -> list[ExtractedMemory]:
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[
                    {"role": "user", "content": f"{EXTRACTION_PROMPT}\n\n{conversation_text}"}
                ],
            )
            text = response.content[0].text
            parsed = self._parse_json(text)
            return [
                ExtractedMemory(
                    content=item["content"],
                    memory_type=item.get("memory_type", "fact"),
                    tags=item.get("tags", []),
                    confidence=item.get("confidence", 1.0),
                )
                for item in parsed
            ]
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            raise ExtractionError(f"Failed to parse extraction response: {e}") from e

    async def check_contradictions(
        self,
        new_fact: str,
        existing_memories: list[MemoryRecord],
    ) -> list[Contradiction]:
        if not existing_memories:
            return []
        existing_text = "\n".join(f"- [{m.id}] {m.content}" for m in existing_memories)
        prompt = CONTRADICTION_PROMPT.format(new_fact=new_fact, existing=existing_text)
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text
            parsed = self._parse_json(text)
            result = []
            for item in parsed:
                mid = item["existing_memory_id"]
                mem = next((m for m in existing_memories if m.id == mid), None)
                if mem:
                    result.append(
                        Contradiction(
                            new_fact=new_fact,
                            existing_memory_id=mid,
                            existing_content=mem.content,
                            explanation=item["explanation"],
                        )
                    )
            return result
        except Exception:
            return []  # Contradiction check is best-effort

    @staticmethod
    def _parse_json(text: str) -> list[dict]:
        cleaned = re.sub(r"```(?:json)?\n?", "", text).strip().rstrip("`")
        return json.loads(cleaned)
