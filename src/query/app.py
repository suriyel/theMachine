"""FastAPI application factory."""

from fastapi import FastAPI

from src.query.health import health_router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI instance with health route.
    """
    app = FastAPI(title="Code Context Retrieval", version="0.1.0")
    app.include_router(health_router, prefix="/api/v1")
    return app
