"""OllamaEmbedder — local embeddings via Ollama (no rate limits)."""
import aiohttp


class OllamaEmbedder:
    def __init__(self, model: str = "nomic-embed-text", base_url: str = "http://localhost:11434"):
        self._model = model
        self._base_url = base_url

    @property
    def dimensions(self) -> int:
        return 768

    async def embed(self, text: str) -> list[float]:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": text},
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["embeddings"][0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self._base_url}/api/embed",
                json={"model": self._model, "input": texts},
            ) as resp:
                resp.raise_for_status()
                data = await resp.json()
                return data["embeddings"]
