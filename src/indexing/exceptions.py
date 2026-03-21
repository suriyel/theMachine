"""Custom exceptions for the indexing package."""


class EmbeddingModelError(Exception):
    """Raised when embedding model fails to load or produce embeddings."""


class IndexWriteError(Exception):
    """Raised when writing to Elasticsearch or Qdrant fails after retries."""
