"""Query models - Request/Response DTOs."""

from typing import List, Optional

from pydantic import BaseModel, Field


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
