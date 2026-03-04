"""Embedder protocol — vector embedding generation."""
from __future__ import annotations

from typing import Protocol


class Embedder(Protocol):
    async def embed(self, text: str) -> list[float]: ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...

    @property
    def dimensions(self) -> int: ...
