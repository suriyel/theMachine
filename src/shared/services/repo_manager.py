"""RepoManager service — validates and registers Git repositories."""

from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.exceptions import ConflictError, ValidationError
from src.shared.models.index_job import IndexJob
from src.shared.models.repository import Repository

_ALLOWED_SCHEMES = {"http", "https", "ssh", "git"}


class RepoManager:
    """Manages repository registration and lifecycle."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(self, url: str) -> Repository:
        """Register a new repository.

        Args:
            url: Git repository URL.

        Returns:
            The created Repository record.

        Raises:
            ValidationError: If the URL is invalid.
            ConflictError: If the URL is already registered.
        """
        normalized = self._validate_url(url)
        name = self._derive_name(normalized)

        # Check for duplicate
        result = await self._session.execute(
            select(Repository).where(Repository.url == normalized)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            raise ConflictError(f"Repository already registered: {normalized}")

        # Create repository record
        repo = Repository(name=name, url=normalized, status="pending")
        self._session.add(repo)
        await self._session.flush()

        # Create initial index job
        job = IndexJob(repo_id=repo.id, branch="main", status="pending")
        self._session.add(job)
        await self._session.flush()

        return repo

    @staticmethod
    def _validate_url(url: str) -> str:
        """Validate and normalize a Git repository URL.

        Returns:
            Normalized URL string.

        Raises:
            ValidationError: If the URL is invalid.
        """
        if not url or not url.strip():
            raise ValidationError("URL must not be empty")

        stripped = url.strip()

        # Handle SSH shorthand: git@github.com:owner/repo.git
        if ":" in stripped and "@" in stripped and "://" not in stripped:
            # SSH shorthand format
            at_idx = stripped.index("@")
            colon_idx = stripped.index(":", at_idx)
            host = stripped[at_idx + 1 : colon_idx].lower()
            path = "/" + stripped[colon_idx + 1 :]

            # Normalize path
            path = path.rstrip("/")
            if path.endswith(".git"):
                path = path[:-4]

            return f"ssh://{host}{path}"

        parsed = urlparse(stripped)

        if parsed.scheme not in _ALLOWED_SCHEMES:
            raise ValidationError(
                f"Unsupported URL scheme: {parsed.scheme!r}"
            )

        if not parsed.hostname:
            raise ValidationError("URL has no host")

        path = parsed.path
        if not path or path == "/":
            raise ValidationError("URL has no repository path")

        # Normalize
        normalized_path = path.rstrip("/")
        if normalized_path.endswith(".git"):
            normalized_path = normalized_path[:-4]

        return f"{parsed.scheme}://{parsed.hostname.lower()}{normalized_path}"

    @staticmethod
    def _derive_name(url: str) -> str:
        """Derive a human-readable name from a normalized URL.

        Returns:
            "{owner}/{repo}" from the last two path segments.
        """
        parsed = urlparse(url)
        path = parsed.path.strip("/")
        segments = path.split("/")
        if len(segments) >= 2:
            return f"{segments[-2]}/{segments[-1]}"
        return path
