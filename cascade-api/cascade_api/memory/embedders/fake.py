"""Deterministic embedder for testing — hash-based, reproducible."""

from __future__ import annotations

import hashlib


class FakeEmbedder:
    def __init__(self, dimensions: int = 768):
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def embed(self, text: str) -> list[float]:
        h = hashlib.sha256(text.encode()).digest()
        vec = []
        for i in range(self._dimensions):
            byte_idx = i % len(h)
            val = (h[byte_idx] + i) % 256
            vec.append((val / 255.0) * 2 - 1)  # normalize to [-1, 1]
        return vec

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [await self.embed(t) for t in texts]
