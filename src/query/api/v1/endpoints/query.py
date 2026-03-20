"""Query API endpoints."""

import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.query.auth import AuthMiddleware
from src.query.cache import QueryCache, get_query_cache
from src.query.dependencies import get_db, get_query_handler
from src.query.handler import QueryHandler
from src.query.language_filter import LanguageFilter
from src.query.models import QueryRequest, QueryResponse
from src.shared.metrics import (
    increment_query_errors,
    increment_query_throughput,
    record_query_latency,
)
from src.shared.models.api_key import APIKey
from src.shared.models.query_log import QueryLog, QueryType

router = APIRouter()

# Language filter instance for validation
_language_filter = LanguageFilter()


async def log_query(
    db: AsyncSession,
    api_key_id: uuid.UUID,
    query_text: str,
    query_type: str,
    repo_filter: Optional[str],
    language_filter: Optional[str],
    result_count: int,
    latency_ms: float,
    correlation_id: uuid.UUID,
):
    """Log query to database."""
    log_entry = QueryLog(
        api_key_id=api_key_id,
        query_text=query_text,
        query_type=QueryType(query_type),
        repo_filter=repo_filter,
        language_filter=language_filter,
        result_count=result_count,
        latency_ms=latency_ms,
        correlation_id=correlation_id,
    )
    db.add(log_entry)
    await db.commit()


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
    query_cache: QueryCache = Depends(get_query_cache),
) -> QueryResponse:
    """Submit a query and retrieve context results."""
    start_time = time.time()
    correlation_id = uuid.uuid4()
    query_type_str = query_request.query_type or "natural_language"

    # Validate language filter if provided
    if query_request.language:
        try:
            _language_filter.validate(query_request.language)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    # Authenticate
    auth = AuthMiddleware(db)
    api_key = await auth.require_auth(request)

    try:
        # Use cache to get or compute result
        result = await query_cache.get_or_compute(
            query_request,
            query_handler.handle
        )

        # Record metrics and log
        latency_ms = (time.time() - start_time) * 1000
        latency_seconds = time.time() - start_time

        # Record success metrics
        record_query_latency(query_type_str, latency_seconds, "success")
        increment_query_throughput(query_type_str, "success")

        # Log query
        await log_query(
            db=db,
            api_key_id=api_key.id,
            query_text=query_request.query,
            query_type=query_type_str,
            repo_filter=query_request.repo,
            language_filter=query_request.language,
            result_count=len(result.results) if result.results else 0,
            latency_ms=latency_ms,
            correlation_id=correlation_id,
        )

        return result
    except (ValueError, ValidationError) as e:
        # Record error metrics
        latency_seconds = time.time() - start_time
        record_query_latency(query_type_str, latency_seconds, "error")
        increment_query_throughput(query_type_str, "error")
        increment_query_errors("validation_error")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # Record error metrics
        latency_seconds = time.time() - start_time
        record_query_latency(query_type_str, latency_seconds, "error")
        increment_query_throughput(query_type_str, "error")
        increment_query_errors("internal_error")
        raise HTTPException(status_code=500, detail=str(e))


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
    start_time = time.time()
    correlation_id = uuid.uuid4()

    # Validate query param
    if not query or not query.strip():
        raise HTTPException(status_code=422, detail="Query parameter is required")

    # Validate language filter if provided
    if language:
        try:
            _language_filter.validate(language)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

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

        # Record metrics and log
        latency_ms = (time.time() - start_time) * 1000
        latency_seconds = time.time() - start_time

        # Record success metrics
        record_query_latency(query_type, latency_seconds, "success")
        increment_query_throughput(query_type, "success")

        # Log query
        await log_query(
            db=db,
            api_key_id=api_key.id,
            query_text=query,
            query_type=query_type,
            repo_filter=repo,
            language_filter=language,
            result_count=len(result.results) if result.results else 0,
            latency_ms=latency_ms,
            correlation_id=correlation_id,
        )

        return result
    except (ValueError, ValidationError) as e:
        # Record error metrics
        latency_seconds = time.time() - start_time
        record_query_latency(query_type, latency_seconds, "error")
        increment_query_throughput(query_type, "error")
        increment_query_errors("validation_error")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # Record error metrics
        latency_seconds = time.time() - start_time
        record_query_latency(query_type, latency_seconds, "error")
        increment_query_throughput(query_type, "error")
        increment_query_errors("internal_error")
        raise HTTPException(status_code=500, detail=str(e))
