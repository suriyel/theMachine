"""Query layer exceptions."""


class RetrievalError(Exception):
    """Raised when a retrieval operation fails (e.g., ES/Qdrant unreachable)."""
