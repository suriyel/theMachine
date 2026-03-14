"""Repository management API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID

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

    url: str
    name: str
    languages: List[str] = Field(default_factory=lambda: ["Java", "Python"])


class ReindexResponse(BaseModel):
    """Reindex response model."""

    job_id: UUID
    repo_id: UUID
    status: str
    message: str


@router.get("", response_model=List[RepositoryResponse])
async def list_repos(
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> List[RepositoryResponse]:
    """List all registered repositories."""
    # TODO: Implement repository listing
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("", response_model=RepositoryResponse, status_code=201)
async def create_repo(
    request: RepositoryCreate,
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> RepositoryResponse:
    """Register a new repository for indexing."""
    # TODO: Implement repository registration (FR-001)
    raise HTTPException(status_code=501, detail="Not implemented")


@router.post("/{repo_id}/reindex", response_model=ReindexResponse)
async def trigger_reindex(
    repo_id: UUID,
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> ReindexResponse:
    """Trigger manual reindex for a specific repository."""
    # TODO: Implement manual reindex trigger (FR-017)
    raise HTTPException(status_code=501, detail="Not implemented")
