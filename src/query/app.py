"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI

from src.query.api.v1.endpoints.keys import keys_router
from src.query.api.v1.endpoints.query import query_router
from src.query.api.v1.endpoints.repos import repos_router
from src.query.health import health_router


def create_app(
    *,
    query_handler=None,
    auth_middleware=None,
    api_key_manager=None,
    session_factory=None,
    es_client=None,
    qdrant_client=None,
    redis_client=None,
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        query_handler: QueryHandler instance for query endpoints.
        auth_middleware: AuthMiddleware instance for authentication.
        api_key_manager: APIKeyManager instance for key management.
        session_factory: Async session factory for database access.
        es_client: ElasticsearchClient for health checks.
        qdrant_client: QdrantClientWrapper for health checks.
        redis_client: RedisClient for health checks.

    Returns:
        Configured FastAPI instance with all routes.
    """
    app = FastAPI(title="Code Context Retrieval", version="0.1.0")

    # Store service instances in app state for dependency injection
    app.state.query_handler = query_handler
    app.state.auth_middleware = auth_middleware
    app.state.api_key_manager = api_key_manager
    app.state.session_factory = session_factory
    app.state.es_client = es_client
    app.state.qdrant_client = qdrant_client
    app.state.redis_client = redis_client

    # Register routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(query_router, prefix="/api/v1")
    app.include_router(repos_router, prefix="/api/v1")
    app.include_router(keys_router, prefix="/api/v1")

    return app
