"""Query API endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.query.auth import AuthMiddleware
from src.query.dependencies import get_db, get_query_handler
from src.query.handler import QueryHandler
from src.query.models import QueryRequest, QueryResponse
from src.shared.models.api_key import APIKey

router = APIRouter()


async def require_api_key(request: Request, db: AsyncSession = Depends(get_db)) -> APIKey:
    """Require valid API key in request.

    Args:
        request: FastAPI Request object
        db: Database session

    Returns:
        APIKey record for valid requests

    Raises:
        HTTPException: 401 if key missing, invalid, or revoked
    """
    auth = AuthMiddleware(db)
    return await auth.require_auth(request)


@router.post("", response_model=QueryResponse)
async def post_query(
    request: Request,
    query_request: QueryRequest,
    db: AsyncSession = Depends(get_db),
    query_handler: QueryHandler = Depends(get_query_handler),
) -> QueryResponse:
    """Submit a query and retrieve context results."""
    # Authenticate
    auth = AuthMiddleware(db)
    api_key = await auth.require_auth(request)

    try:
        # Call query handler
        result = await query_handler.handle(query_request)
        return result
    except (ValueError, ValidationError) as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get("", response_model=QueryResponse)
async def get_query(
    request: Request,
    query: Optional[str] = None,
    query_type: str = "natural_language",
    repo: Optional[str] = None,
    language: Optional[str] = None,
    top_k: int = 3,
    db: AsyncSession = Depends(get_db),
    query_handler: QueryHandler = Depends(get_query_handler),
) -> QueryResponse:
    """Submit a query via GET and retrieve context results."""
    # Validate query param
    if not query or not query.strip():
        raise HTTPException(status_code=422, detail="Query parameter is required")

    # Authenticate
    auth = AuthMiddleware(db)
    api_key = await auth.require_auth(request)

    # Build request from query params
    query_request = QueryRequest(
        query=query,
        query_type=query_type,
        repo=repo,
        language=language,
        top_k=top_k,
    )

    try:
        # Call query handler
        result = await query_handler.handle(query_request)
        return result
    except (ValueError, ValidationError) as e:
        raise HTTPException(status_code=422, detail=str(e))
