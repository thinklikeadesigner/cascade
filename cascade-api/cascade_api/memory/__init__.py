"""cascade-memory: Pluggable memory system for AI agents."""

from cascade_api.memory.client import MemoryClient, TenantScopedClient
from cascade_api.memory.core import CoreMemory
from cascade_api.memory.models import (
    Contradiction,
    ExtractedMemory,
    MemoryLink,
    MemoryRecord,
    SearchResult,
)
from cascade_api.memory.errors import (
    CascadeMemoryError,
    ConcurrencyError,
    DimensionMismatchError,
    EmbeddingError,
    ExtractionError,
    MemoryNotFoundError,
    StoreLimitError,
    TenantIsolationError,
)

__all__ = [
    "MemoryClient",
    "TenantScopedClient",
    "CoreMemory",
    "MemoryRecord",
    "SearchResult",
    "MemoryLink",
    "ExtractedMemory",
    "Contradiction",
    "CascadeMemoryError",
    "ConcurrencyError",
    "DimensionMismatchError",
    "EmbeddingError",
    "ExtractionError",
    "MemoryNotFoundError",
    "StoreLimitError",
    "TenantIsolationError",
]
