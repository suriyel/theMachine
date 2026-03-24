"""Pydantic request/response models for REST API v1 endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class QueryRequest(BaseModel):
    """Request body for POST /api/v1/query."""

    query: str
    repo_id: str
    languages: list[str] | None = None


class RegisterRepoRequest(BaseModel):
    """Request body for POST /api/v1/repos."""

    url: str
    branch: str | None = None


class CreateKeyRequest(BaseModel):
    """Request body for POST /api/v1/keys."""

    name: str
    role: str
    repo_ids: list[uuid.UUID] | None = None


class RepoResponse(BaseModel):
    """Response model for repository endpoints."""

    id: uuid.UUID
    name: str
    url: str
    status: str
    indexed_branch: str | None = None
    last_indexed_at: datetime | None = None
    created_at: datetime | None = None


class BranchListResponse(BaseModel):
    """Response model for GET /api/v1/repos/{repo_id}/branches."""

    branches: list[str]
    default_branch: str


class ReindexResponse(BaseModel):
    """Response model for POST /api/v1/repos/{repo_id}/reindex."""

    job_id: uuid.UUID
    repo_id: uuid.UUID
    status: str


class CreateKeyResponse(BaseModel):
    """Response model for key creation/rotation (includes plaintext key)."""

    id: uuid.UUID
    key: str
    name: str
    role: str


class KeyResponse(BaseModel):
    """Response model for key listing (no plaintext)."""

    id: uuid.UUID
    name: str
    role: str
    is_active: bool
    created_at: datetime | None = None
    expires_at: datetime | None = None


class ServiceHealth(BaseModel):
    """Per-service health status."""

    elasticsearch: str
    qdrant: str
    redis: str
    postgresql: str


class HealthResponse(BaseModel):
    """Response model for GET /api/v1/health."""

    status: str
    service: str
    services: ServiceHealth
