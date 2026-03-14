"""Custom exceptions for the indexing module."""


class GitCloneError(Exception):
    """Base exception for git clone/update operations."""

    pass


class GitCloneFailedError(GitCloneError):
    """Raised when git clone operation fails."""

    pass


class GitFetchError(GitCloneError):
    """Raised when git fetch/update operation fails."""

    pass
