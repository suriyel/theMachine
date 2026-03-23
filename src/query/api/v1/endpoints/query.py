"""Query endpoint — POST /api/v1/query."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from src.query.api.v1.deps import get_auth_middleware, get_authenticated_key, require_permission
from src.query.api.v1.schemas import QueryRequest
from src.query.exceptions import RetrievalError
from src.query.response_models import QueryResponse
from src.shared.exceptions import ValidationError
from src.shared.models.api_key import ApiKey
from src.shared.services.auth_middleware import AuthMiddleware

query_router = APIRouter(tags=["query"])


@query_router.post("/query", response_model=QueryResponse)
async def post_query(
    body: QueryRequest,
    request: Request,
    api_key: ApiKey = Depends(get_authenticated_key),
    auth_middleware: AuthMiddleware = Depends(get_auth_middleware),
) -> QueryResponse:
    """Submit a code context query."""
    require_permission(api_key, "query", auth_middleware)

    query_handler = request.app.state.query_handler
    query_cache = getattr(request.app.state, "query_cache", None)

    query_type = query_handler.detect_query_type(body.query)

    # Check cache before executing pipeline
    if query_cache is not None:
        cached = await query_cache.get(body.query, body.repo_id, body.languages)
        if cached is not None:
            return cached

    try:
        if query_type == "symbol":
            response = await query_handler.handle_symbol_query(body.query, body.repo_id, body.languages)
        else:
            response = await query_handler.handle_nl_query(
                body.query, body.repo_id, body.languages
            )
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RetrievalError:
        raise HTTPException(status_code=500, detail="Retrieval failed")

    # Store result in cache
    if query_cache is not None:
        await query_cache.set(body.query, body.repo_id, body.languages, response)

    return response
