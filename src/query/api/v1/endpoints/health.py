"""Health check endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
