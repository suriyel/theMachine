"""Query API dependencies - FastAPI dependency injection providers."""

import secrets
from typing import AsyncGenerator, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.query.cache import QueryCache
from src.query.handler import QueryHandler
from src.query.rank_fusion import RankFusion
from src.query.reranker import NeuralReranker
from src.query.response_builder import ContextResponseBuilder
from src.query.retriever import KeywordRetriever, SemanticRetriever
from src.shared.clients import get_elasticsearch, get_qdrant


# Session cookie name
SESSION_COOKIE_NAME = "ccr_session"
SESSION_COOKIE_MAX_AGE = 7 * 24 * 60 * 60  # 7 days in seconds

# In-memory session store (in production, use Redis)
_sessions: dict[str, dict] = {}


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection.

    Yields:
        AsyncSession for database operations
    """
    from src.shared.db.session import async_session_maker

    async with async_session_maker() as session:
        yield session


def create_session(api_key_id: int, api_key_name: str) -> str:
    """Create a new session for authenticated user.

    Args:
        api_key_id: The API key ID
        api_key_name: The API key name

    Returns:
        Session token
    """
    session_token = secrets.token_urlsafe(32)
    _sessions[session_token] = {
        "api_key_id": api_key_id,
        "api_key_name": api_key_name,
    }
    return session_token


def get_session(request: Request) -> Optional[dict]:
    """Get session data from request.

    Args:
        request: FastAPI Request object

    Returns:
        Session data dict if valid, None otherwise
    """
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_token:
        return None

    session_data = _sessions.get(session_token)
    if not session_data:
        return None

    return session_data


def require_auth(request: Request) -> dict:
    """Require authenticated session.

    Args:
        request: FastAPI Request object

    Returns:
        Session data

    Raises:
        HTTPException: 401 if not authenticated
    """
    from fastapi import HTTPException

    session_data = get_session(request)
    if not session_data:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please log in to continue.",
            headers={"WWW-Authenticate": "Cookie"},
        )
    return session_data


def destroy_session(request: Request) -> None:
    """Destroy session on logout.

    Args:
        request: FastAPI Request object
    """
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token and session_token in _sessions:
        del _sessions[session_token]


async def get_query_handler() -> QueryHandler:
    """Get QueryHandler instance with all dependencies wired.

    Returns:
        QueryHandler with all components configured
    """
    # Get clients
    es_client = get_elasticsearch()
    qdrant_client = get_qdrant()

    # Create components
    keyword_retriever = KeywordRetriever(es_client=es_client)
    semantic_retriever = SemanticRetriever(qdrant_client=qdrant_client)
    rank_fusion = RankFusion()
    reranker = NeuralReranker()
    response_builder = ContextResponseBuilder()

    # Create and return handler
    return QueryHandler(
        keyword_retriever=keyword_retriever,
        semantic_retriever=semantic_retriever,
        rank_fusion=rank_fusion,
        reranker=reranker,
        response_builder=response_builder,
    )


async def get_query_cache() -> QueryCache:
    """Get QueryCache instance for dependency injection.

    Returns:
        QueryCache instance
    """
    from src.query.cache import get_query_cache as _get_cache
    return await _get_cache()
