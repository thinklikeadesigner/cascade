"""OllamaExtractor — extract memories from conversations via local Ollama."""

import json
import logging
import re

import aiohttp

from cascade_api.memory.models import ExtractedMemory

logger = logging.getLogger(__name__)

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

Return ONLY the JSON array, no other text.

/no_think"""


class OllamaExtractor:
    def __init__(self, model: str = "qwen3:8b", base_url: str = "http://localhost:11434"):
        self._model = model
        self._base_url = base_url

    async def extract(self, conversation_text: str) -> list[ExtractedMemory]:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self._base_url}/api/chat",
                    json={
                        "model": self._model,
                        "messages": [
                            {"role": "user", "content": f"{EXTRACTION_PROMPT}\n\n{conversation_text}"}
                        ],
                        "stream": False,
                    },
                ) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
                    text = data["message"]["content"]

            cleaned = re.sub(r"```(?:json)?\n?", "", text).strip().rstrip("`")
            parsed = json.loads(cleaned)

            return [
                ExtractedMemory(
                    content=item["content"],
                    memory_type=item.get("memory_type", "fact"),
                    tags=item.get("tags", []),
                    confidence=item.get("confidence", 1.0),
                )
                for item in parsed
            ]
        except Exception as e:
            logger.warning(f"Ollama extraction failed: {e}")
            return []

    async def check_contradictions(self, new_fact, existing_memories):
        return []  # Best-effort, not implemented for local model
