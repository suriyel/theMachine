"""Query API endpoints."""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

router = APIRouter()


class QueryRequest(BaseModel):
    """Query request model."""

    query: str = Field(..., min_length=1, description="Query text")
    query_type: str = Field(default="natural_language", description="Query type: natural_language or symbol")
    repo: Optional[str] = Field(None, description="Repository filter")
    language: Optional[str] = Field(None, description="Language filter")
    top_k: int = Field(default=3, ge=1, le=10, description="Number of results")


class ContextResult(BaseModel):
    """Single context result."""

    repository: str
    file_path: str
    symbol: Optional[str] = None
    score: float
    content: str


class QueryResponse(BaseModel):
    """Query response model."""

    results: List[ContextResult]
    query_time_ms: float


@router.post("", response_model=QueryResponse)
async def post_query(
    request: QueryRequest,
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> QueryResponse:
    """Submit a query and retrieve context results."""
    # TODO: Implement query handler invocation
    raise HTTPException(status_code=501, detail="Not implemented")


@router.get("", response_model=QueryResponse)
async def get_query(
    query: str,
    query_type: str = "natural_language",
    repo: Optional[str] = None,
    language: Optional[str] = None,
    top_k: int = 3,
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> QueryResponse:
    """Submit a query via GET and retrieve context results."""
    # TODO: Implement query handler invocation
    raise HTTPException(status_code=501, detail="Not implemented")
