"""FastAPI dependency injection helpers."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from src.shared.models.api_key import ApiKey
from src.shared.services.auth_middleware import AuthMiddleware


async def get_auth_middleware(request: Request) -> AuthMiddleware:
    """Retrieve AuthMiddleware from app state."""
    return request.app.state.auth_middleware


async def get_authenticated_key(
    request: Request,
    auth_middleware: AuthMiddleware = Depends(get_auth_middleware),
) -> ApiKey:
    """Authenticate the request and return the ApiKey."""
    return await auth_middleware(request)


def require_permission(api_key: ApiKey, action: str, auth_middleware: AuthMiddleware) -> None:
    """Check permission; raise 403 if denied."""
    if not auth_middleware.check_permission(api_key, action):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
