"""Exception hierarchy for cascade-memory."""


class CascadeMemoryError(Exception):
    """Base exception for cascade-memory."""


class ConcurrencyError(CascadeMemoryError):
    """Core memory version mismatch — modified by another process."""


class MemoryNotFoundError(CascadeMemoryError):
    """Memory ID does not exist or is not accessible for this tenant."""


class EmbeddingError(CascadeMemoryError):
    """Embedding generation failed."""


class ExtractionError(CascadeMemoryError):
    """Memory extraction from conversation failed."""


class StoreLimitError(CascadeMemoryError):
    """Core memory size limit exceeded."""


class DimensionMismatchError(CascadeMemoryError):
    """Embedder dimensions don't match database column."""


class TenantIsolationError(CascadeMemoryError):
    """Cross-tenant operation detected."""
