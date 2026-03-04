def test_top_level_imports():
    from cascade_memory import (  # noqa: F401
        MemoryClient, TenantScopedClient, CoreMemory,
        MemoryRecord, SearchResult, MemoryLink, ExtractedMemory, Contradiction,
        CascadeMemoryError, ConcurrencyError, MemoryNotFoundError,
        EmbeddingError, ExtractionError, StoreLimitError,
        DimensionMismatchError, TenantIsolationError,
    )
    assert MemoryClient is not None
