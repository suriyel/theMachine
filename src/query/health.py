"""Health check endpoint."""

from fastapi import APIRouter

health_router = APIRouter()


@health_router.get("/health")
async def health_check() -> dict:
    """Return service health status."""
    return {"status": "ok", "service": "code-context-retrieval"}
