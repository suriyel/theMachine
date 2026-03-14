"""API v1 router."""

from fastapi import APIRouter

from src.query.api.v1.endpoints import query, repos, health, metrics

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(repos.router, prefix="/repos", tags=["repos"])
