"""Repository management API endpoints."""

from typing import List, Optional
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.db.session import get_db
from src.shared.services.repo_manager import RepoManager
from src.shared.models import RepoStatus


router = APIRouter()


class RepositoryResponse(BaseModel):
    """Repository response model."""

    id: UUID
    url: str
    name: str
    languages: List[str]
    status: str
    created_at: datetime
    last_indexed_at: Optional[datetime] = None


class RepositoryCreate(BaseModel):
    """Repository creation request model."""

    url: str = Field(..., min_length=1, max_length=2048)
    name: str = Field(..., min_length=1, max_length=255)
    languages: List[str] = Field(default_factory=lambda: ["Java", "Python"])

    @field_validator("url")
    @classmethod
    def validate_url_format(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class ReindexResponse(BaseModel):
    """Reindex response model."""

    job_id: UUID
    repo_id: UUID
    status: str
    message: str


@router.get("", response_model=List[RepositoryResponse])
async def list_repos(
    db: AsyncSession = Depends(get_db),
) -> List[RepositoryResponse]:
    """List all registered repositories."""
    repo_manager = RepoManager(db)
    repos = await repo_manager.list_all()
    return [
        RepositoryResponse(
            id=repo.id,
            url=repo.url,
            name=repo.name,
            languages=repo.languages,
            status=repo.status.value,
            created_at=repo.created_at,
            last_indexed_at=repo.last_indexed_at,
        )
        for repo in repos
    ]


@router.post("", response_model=RepositoryResponse, status_code=201)
async def create_repo(
    request: RepositoryCreate,
    db: AsyncSession = Depends(get_db),
    skip_validation: bool = False,
) -> RepositoryResponse:
    """Register a new repository for indexing.

    Args:
        skip_validation: If true, skips Git URL validation (for testing only)
    """
    repo_manager = RepoManager(db)
    try:
        repo = await repo_manager.register(
            url=request.url,
            name=request.name,
            languages=request.languages,
            validate_url=not skip_validation,
        )
        return RepositoryResponse(
            id=repo.id,
            url=repo.url,
            name=repo.name,
            languages=repo.languages,
            status=repo.status.value,
            created_at=repo.created_at,
            last_indexed_at=repo.last_indexed_at,
        )
    except ValueError as e:
        error_msg = str(e)
        if "already registered" in error_msg.lower() or "duplicate" in error_msg.lower():
            raise HTTPException(status_code=409, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)


@router.post("/{repo_id}/reindex", response_model=ReindexResponse)
async def trigger_reindex(
    repo_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> ReindexResponse:
    """Trigger manual reindex for a specific repository.

    Args:
        repo_id: UUID of the repository to reindex
        db: Database session

    Returns:
        ReindexResponse with job details

    Raises:
        HTTPException: 404 if repo not found, 409 if active job exists
    """
    from src.shared.models.index_job import TriggerType

    repo_manager = RepoManager(db)

    try:
        # Check for existing active job
        if await repo_manager.has_active_job(repo_id):
            raise HTTPException(
                status_code=409,
                detail="Repository already has an active indexing job in progress",
            )

        # Queue the indexing job
        job = await repo_manager.queue_indexing(repo_id, TriggerType.MANUAL)

        return ReindexResponse(
            job_id=job.id,
            repo_id=repo_id,
            status=job.status.value,
            message="Indexing job queued successfully",
        )

    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        if "active" in error_msg.lower():
            raise HTTPException(status_code=409, detail=error_msg)
        raise HTTPException(status_code=400, detail=error_msg)
