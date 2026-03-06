import os
import pytest
from cascade_api.memory.embedders.gemini import GeminiEmbedder

SKIP = not os.environ.get("GEMINI_API_KEY")


@pytest.mark.skipif(SKIP, reason="GEMINI_API_KEY not set")
class TestGeminiEmbedder:
    @pytest.fixture
    def embedder(self):
        return GeminiEmbedder(api_key=os.environ["GEMINI_API_KEY"])

    def test_dimensions(self, embedder):
        assert embedder.dimensions == 3072

    async def test_embed(self, embedder):
        vec = await embedder.embed("hello world")
        assert len(vec) == 3072
        assert all(isinstance(v, float) for v in vec)

    async def test_embed_batch(self, embedder):
        vecs = await embedder.embed_batch(["a", "b"])
        assert len(vecs) == 2
        assert all(len(v) == 3072 for v in vecs)
