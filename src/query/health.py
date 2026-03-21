"""Health check endpoint with per-service status."""

from fastapi import APIRouter, Request

from src.query.api.v1.schemas import HealthResponse, ServiceHealth

health_router = APIRouter()


@health_router.get("/health", response_model=HealthResponse)
async def health_check(request: Request) -> HealthResponse:
    """Return service health status with per-service connectivity checks.

    This endpoint is unauthenticated so monitoring systems can check without API keys.
    """
    es_status = "down"
    qdrant_status = "down"
    redis_status = "down"
    pg_status = "down"

    # Check Elasticsearch
    es_client = getattr(request.app.state, "es_client", None)
    if es_client is not None:
        try:
            if await es_client.health_check():
                es_status = "up"
        except Exception:
            pass

    # Check Qdrant
    qdrant_client = getattr(request.app.state, "qdrant_client", None)
    if qdrant_client is not None:
        try:
            if await qdrant_client.health_check():
                qdrant_status = "up"
        except Exception:
            pass

    # Check Redis
    redis_client = getattr(request.app.state, "redis_client", None)
    if redis_client is not None:
        try:
            if await redis_client.health_check():
                redis_status = "up"
        except Exception:
            pass

    # Check PostgreSQL
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is not None:
        try:
            from sqlalchemy import text

            async with session_factory() as session:
                await session.execute(text("SELECT 1"))
            pg_status = "up"
        except Exception:
            pass

    services = ServiceHealth(
        elasticsearch=es_status,
        qdrant=qdrant_status,
        redis=redis_status,
        postgresql=pg_status,
    )

    all_up = all(
        v == "up"
        for v in [es_status, qdrant_status, redis_status, pg_status]
    )
    overall = "healthy" if all_up else "degraded"

    return HealthResponse(
        status=overall,
        service="code-context-retrieval",
        services=services,
    )
