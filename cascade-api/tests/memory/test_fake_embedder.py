import pytest
from cascade_api.memory.embedders.fake import FakeEmbedder


class TestFakeEmbedder:
    @pytest.fixture
    def embedder(self):
        return FakeEmbedder(dimensions=768)

    async def test_dimensions(self, embedder):
        assert embedder.dimensions == 768

    async def test_returns_correct_length(self, embedder):
        vec = await embedder.embed("hello")
        assert len(vec) == 768

    async def test_deterministic(self, embedder):
        v1 = await embedder.embed("hello")
        v2 = await embedder.embed("hello")
        assert v1 == v2

    async def test_different_inputs_different_vectors(self, embedder):
        v1 = await embedder.embed("hello")
        v2 = await embedder.embed("world")
        assert v1 != v2

    async def test_embed_batch(self, embedder):
        results = await embedder.embed_batch(["a", "b", "c"])
        assert len(results) == 3
        assert all(len(v) == 768 for v in results)
