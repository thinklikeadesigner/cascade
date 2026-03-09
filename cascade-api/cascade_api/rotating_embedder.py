"""GeminiEmbedder wrapper that rotates between multiple API keys on rate limit."""
import logging

from cascade_memory.embedders.gemini import GeminiEmbedder

logger = logging.getLogger(__name__)


class RotatingGeminiEmbedder:
    def __init__(self, api_keys: list[str], model: str = "gemini-embedding-001"):
        if not api_keys:
            raise ValueError("At least one API key required")
        self._embedders = [GeminiEmbedder(api_key=key, model=model) for key in api_keys]
        self._current = 0
        self._dimensions = self._embedders[0].dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        last_error = None
        for _ in range(len(self._embedders)):
            try:
                return await self._embedders[self._current].embed(text)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    last_error = e
                    old = self._current
                    self._current = (self._current + 1) % len(self._embedders)
                    logger.warning(f"Key {old} rate limited, rotating to key {self._current}")
                else:
                    raise
        raise last_error

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]
