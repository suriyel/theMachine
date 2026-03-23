"""Repository endpoints — GET/POST /api/v1/repos."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from src.indexing.git_cloner import GitCloner
from src.query.api.v1.deps import get_auth_middleware, get_authenticated_key, require_permission
from src.query.api.v1.schemas import BranchListResponse, RegisterRepoRequest, ReindexResponse, RepoResponse
from src.shared.exceptions import CloneError, ConflictError, ValidationError
from src.shared.models.api_key import ApiKey
from src.shared.models.index_job import IndexJob
from src.shared.models.repository import Repository
from src.shared.services.auth_middleware import AuthMiddleware
from src.shared.services.repo_manager import RepoManager

repos_router = APIRouter(tags=["repos"])


@repos_router.get("/repos", response_model=list[RepoResponse])
async def list_repos(
    request: Request,
    api_key: ApiKey = Depends(get_authenticated_key),
    auth_middleware: AuthMiddleware = Depends(get_auth_middleware),
) -> list[RepoResponse]:
    """List all registered repositories."""
    require_permission(api_key, "list_repos", auth_middleware)

    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        result = await session.execute(select(Repository))
        repos = result.scalars().all()

    return [
        RepoResponse(
            id=r.id,
            name=r.name,
            url=r.url,
            status=r.status,
            indexed_branch=r.indexed_branch,
            last_indexed_at=r.last_indexed_at,
            created_at=r.created_at,
        )
        for r in repos
    ]


@repos_router.post("/repos", response_model=RepoResponse)
async def register_repo(
    body: RegisterRepoRequest,
    request: Request,
    api_key: ApiKey = Depends(get_authenticated_key),
    auth_middleware: AuthMiddleware = Depends(get_auth_middleware),
) -> RepoResponse:
    """Register a new repository."""
    require_permission(api_key, "register_repo", auth_middleware)

    session_factory = request.app.state.session_factory

    try:
        async with session_factory() as session:
            manager = RepoManager(session)
            repo = await manager.register(body.url, body.branch)
            await session.commit()
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    return RepoResponse(
        id=repo.id,
        name=repo.name,
        url=repo.url,
        status=repo.status,
        indexed_branch=repo.indexed_branch,
        last_indexed_at=repo.last_indexed_at,
        created_at=repo.created_at,
    )


@repos_router.post("/repos/{repo_id}/reindex", response_model=ReindexResponse)
async def reindex_repo(
    repo_id: uuid.UUID,
    request: Request,
    api_key: ApiKey = Depends(get_authenticated_key),
    auth_middleware: AuthMiddleware = Depends(get_auth_middleware),
) -> ReindexResponse:
    """Trigger a manual reindex for a repository."""
    require_permission(api_key, "reindex", auth_middleware)

    session_factory = request.app.state.session_factory

    async with session_factory() as session:
        result = await session.execute(
            select(Repository).where(Repository.id == repo_id)
        )
        repo = result.scalar_one_or_none()

        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found")

        branch = repo.indexed_branch or repo.default_branch or "main"
        job = IndexJob(repo_id=repo.id, branch=branch, status="pending")
        session.add(job)
        await session.commit()

        # Invalidate query cache for this repository
        query_cache = getattr(request.app.state, "query_cache", None)
        if query_cache is not None:
            repo_name = repo.name
            await query_cache.invalidate_repo(repo_name)

        return ReindexResponse(
            job_id=job.id,
            repo_id=repo.id,
            status=job.status,
        )


@repos_router.get("/repos/{repo_id}/branches", response_model=BranchListResponse)
async def list_branches(
    repo_id: uuid.UUID,
    request: Request,
    api_key: ApiKey = Depends(get_authenticated_key),
    auth_middleware: AuthMiddleware = Depends(get_auth_middleware),
) -> BranchListResponse:
    """List remote branches for a registered repository."""
    require_permission(api_key, "list_branches", auth_middleware)

    session_factory = request.app.state.session_factory
    async with session_factory() as session:
        result = await session.execute(
            select(Repository).where(Repository.id == repo_id)
        )
        repo = result.scalar_one_or_none()

        if repo is None:
            raise HTTPException(status_code=404, detail="Repository not found")

        if repo.clone_path is None:
            raise HTTPException(
                status_code=409, detail="Repository has not been cloned yet"
            )

        try:
            cloner = GitCloner(storage_path="")
            branches = cloner.list_remote_branches(repo.clone_path)
        except CloneError:
            raise HTTPException(
                status_code=500, detail="Failed to list branches"
            )

        default_branch = repo.default_branch or "main"

    return BranchListResponse(
        branches=branches,
        default_branch=default_branch,
    )
