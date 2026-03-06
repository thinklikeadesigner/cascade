"""GeminiEmbedder — Google Gemini embedding API (3072-dim, free tier)."""

from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def _get_client(api_key: str):
    from google import genai

    return genai.Client(api_key=api_key)


class GeminiEmbedder:
    def __init__(self, api_key: str, model: str = "gemini-embedding-001"):
        self._api_key = api_key
        self._model = model

    @property
    def dimensions(self) -> int:
        return 3072

    async def embed(self, text: str) -> list[float]:
        client = _get_client(self._api_key)
        result = client.models.embed_content(model=self._model, contents=text)
        return list(result.embeddings[0].values)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]
