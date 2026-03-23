"""FastAPI application factory."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.staticfiles import StaticFiles

from src.query.api.v1.endpoints.keys import keys_router
from src.query.api.v1.endpoints.query import query_router
from src.query.api.v1.endpoints.repos import repos_router
from src.query.health import health_router
from src.query.metrics_registry import metrics_router
from src.query.web_router import WebRouter


def create_app(
    *,
    query_handler=None,
    auth_middleware=None,
    api_key_manager=None,
    session_factory=None,
    es_client=None,
    qdrant_client=None,
    redis_client=None,
    git_cloner=None,
    query_cache=None,
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
    @asynccontextmanager
    async def _lifespan(app: FastAPI):
        # Startup: connect all non-None infrastructure clients
        if es_client is not None:
            await es_client.connect()
        if qdrant_client is not None:
            await qdrant_client.connect()
        if redis_client is not None:
            await redis_client.connect()
        yield
        # Shutdown: close all non-None infrastructure clients.
        # Each close() is attempted independently so a failure on one client
        # does not prevent the remaining clients from being closed.
        for client in (es_client, qdrant_client, redis_client):
            if client is not None:
                try:
                    await client.close()
                except Exception:
                    pass

    app = FastAPI(title="Code Context Retrieval", version="0.1.0", lifespan=_lifespan)

    # Store service instances in app state for dependency injection
    app.state.query_handler = query_handler
    app.state.auth_middleware = auth_middleware
    app.state.api_key_manager = api_key_manager
    app.state.session_factory = session_factory
    app.state.es_client = es_client
    app.state.qdrant_client = qdrant_client
    app.state.redis_client = redis_client
    app.state.git_cloner = git_cloner
    app.state.query_cache = query_cache

    # Register routers
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(query_router, prefix="/api/v1")
    app.include_router(repos_router, prefix="/api/v1")
    app.include_router(keys_router, prefix="/api/v1")

    # Metrics (unauthenticated, Prometheus scrape)
    app.include_router(metrics_router)

    # Web UI router (SSR)
    web_router = WebRouter()
    app.include_router(web_router.router)

    # Mount static files
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    if os.path.isdir(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    return app
