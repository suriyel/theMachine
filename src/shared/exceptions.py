"""Application-level exceptions for Code Context Retrieval."""


class ValidationError(Exception):
    """Raised when input validation fails."""


class ConflictError(Exception):
    """Raised when a resource already exists."""


class CloneError(Exception):
    """Raised when a git clone or update operation fails."""
