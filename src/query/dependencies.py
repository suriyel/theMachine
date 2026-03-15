"""Query API dependencies - FastAPI dependency injection providers."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.query.handler import QueryHandler
from src.query.rank_fusion import RankFusion
from src.query.reranker import NeuralReranker
from src.query.response_builder import ContextResponseBuilder
from src.query.retriever import KeywordRetriever, SemanticRetriever
from src.shared.clients import get_elasticsearch, get_qdrant


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session for dependency injection.

    Yields:
        AsyncSession for database operations
    """
    from src.shared.db.session import async_session_maker

    async with async_session_maker() as session:
        yield session


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
