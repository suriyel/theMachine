"""Prometheus metrics endpoint."""

from fastapi import APIRouter, Response

from src.shared.clients import get_metrics

router = APIRouter()


@router.get("")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
