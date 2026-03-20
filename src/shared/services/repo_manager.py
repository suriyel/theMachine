"""Repository management service.

This service handles CRUD operations for Git repository records.
"""

from uuid import UUID
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.models import Repository, RepoStatus
from src.shared.models.index_job import IndexJob, JobStatus, TriggerType
from src.shared.utils.git_validator import validate_git_url


class RepoManager:
    """Service class for managing repository records.

    This service provides the business logic for:
    - Registering new repositories (with URL validation)
    - Retrieving repositories by ID or URL
    - Listing all repositories
    - Deleting repositories

    Attributes:
        db: AsyncSession for database operations
    """

    def __init__(self, db: AsyncSession):
        """Initialize RepoManager with database session.

        Args:
            db: SQLAlchemy async session for database operations
        """
        self.db = db

    async def register(
        self,
        url: str,
        name: str,
        languages: List[str],
        validate_url: bool = True,
    ) -> Repository:
        """Register a new repository for indexing.

        This method:
        1. Validates the URL format and reachability (if validate_url=True)
        2. Checks for duplicate URLs
        3. Creates a new Repository record with REGISTERED status

        Args:
            url: Git repository URL (HTTPS preferred)
            name: Display name for the repository
            languages: List of target programming languages to index
            validate_url: Whether to validate URL reachability (default True)

        Returns:
            Created Repository object with generated ID and timestamps

        Raises:
            ValueError: If URL is invalid, unreachable, or already registered
        """
        # Validate URL format and reachability
        if validate_url:
            is_valid, error_msg = await validate_git_url(url)
            if not is_valid:
                raise ValueError(f"Invalid or unreachable Git URL: {error_msg}")

        # Check for duplicate URL
        existing = await self.get_by_url(url)
        if existing:
            raise ValueError(f"Repository with URL '{url}' already registered")

        # Create repository record
        repo = Repository(
            url=url,
            name=name,
            languages=languages,
            status=RepoStatus.REGISTERED,
        )
        self.db.add(repo)
        await self.db.flush()
        await self.db.refresh(repo)
        return repo

    async def get(self, repo_id: UUID) -> Repository:
        """Get a repository by ID.

        Args:
            repo_id: Repository UUID

        Returns:
            Repository object

        Raises:
            ValueError: If repository not found
        """
        result = await self.db.execute(
            select(Repository).where(Repository.id == repo_id)
        )
        repo = result.scalar_one_or_none()
        if repo is None:
            raise ValueError(f"Repository with ID '{repo_id}' not found")
        return repo

    async def get_by_url(self, url: str) -> Optional[Repository]:
        """Get a repository by URL.

        Args:
            url: Git repository URL

        Returns:
            Repository object or None if not found
        """
        result = await self.db.execute(
            select(Repository).where(Repository.url == url)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> List[Repository]:
        """List all registered repositories.

        Returns:
            List of all Repository objects ordered by creation date (newest first)
        """
        result = await self.db.execute(
            select(Repository).order_by(Repository.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, repo_id: UUID) -> None:
        """Delete a repository by ID.

        Args:
            repo_id: Repository UUID

        Raises:
            ValueError: If repository not found
        """
        repo = await self.get(repo_id)
        await self.db.delete(repo)
        await self.db.flush()

    async def queue_indexing(
        self,
        repo_id: UUID,
        trigger_type: TriggerType = TriggerType.MANUAL,
    ) -> IndexJob:
        """Queue an indexing job for a repository.

        Args:
            repo_id: Repository UUID to index
            trigger_type: How the job was triggered (manual or scheduled)

        Returns:
            Created IndexJob object

        Raises:
            ValueError: If repository not found
        """
        repo = await self.get(repo_id)

        # Check if there's already an active job
        if await self.has_active_job(repo_id):
            raise ValueError(f"Repository {repo_id} already has an active indexing job")

        # Create indexing job
        job = IndexJob(
            repo_id=repo_id,
            status=JobStatus.QUEUED,
            trigger_type=trigger_type,
        )
        self.db.add(job)
        await self.db.flush()
        await self.db.refresh(job)

        # Update repository status
        repo.status = RepoStatus.INDEXING
        await self.db.flush()

        return job

    async def has_active_job(self, repo_id: UUID) -> bool:
        """Check if repository has an active (queued or running) job.

        Args:
            repo_id: Repository UUID

        Returns:
            True if there's an active job, False otherwise
        """
        result = await self.db.execute(
            select(IndexJob).where(
                IndexJob.repo_id == repo_id,
                IndexJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]),
            )
        )
        return result.scalar_one_or_none() is not None
