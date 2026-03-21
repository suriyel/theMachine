"""API key management endpoints — /api/v1/keys."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from src.query.api.v1.deps import get_auth_middleware, get_authenticated_key, require_permission
from src.query.api.v1.schemas import CreateKeyRequest, CreateKeyResponse, KeyResponse
from src.shared.models.api_key import ApiKey
from src.shared.services.auth_middleware import AuthMiddleware

keys_router = APIRouter(tags=["keys"])


@keys_router.post("/keys", response_model=CreateKeyResponse)
async def create_key(
    body: CreateKeyRequest,
    request: Request,
    api_key: ApiKey = Depends(get_authenticated_key),
    auth_middleware: AuthMiddleware = Depends(get_auth_middleware),
) -> CreateKeyResponse:
    """Create a new API key (admin only)."""
    require_permission(api_key, "manage_keys", auth_middleware)

    api_key_manager = request.app.state.api_key_manager

    try:
        plaintext, new_key = await api_key_manager.create_key(
            body.name, body.role, body.repo_ids
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return CreateKeyResponse(
        id=new_key.id,
        key=plaintext,
        name=new_key.name,
        role=new_key.role,
    )


@keys_router.get("/keys", response_model=list[KeyResponse])
async def list_keys(
    request: Request,
    api_key: ApiKey = Depends(get_authenticated_key),
    auth_middleware: AuthMiddleware = Depends(get_auth_middleware),
) -> list[KeyResponse]:
    """List all API keys (admin only)."""
    require_permission(api_key, "manage_keys", auth_middleware)

    api_key_manager = request.app.state.api_key_manager
    keys = await api_key_manager.list_keys()

    return [
        KeyResponse(
            id=k.id,
            name=k.name,
            role=k.role,
            is_active=k.is_active,
            created_at=k.created_at,
            expires_at=k.expires_at,
        )
        for k in keys
    ]


@keys_router.delete("/keys/{key_id}")
async def delete_key(
    key_id: uuid.UUID,
    request: Request,
    api_key: ApiKey = Depends(get_authenticated_key),
    auth_middleware: AuthMiddleware = Depends(get_auth_middleware),
) -> dict:
    """Revoke an API key (admin only)."""
    require_permission(api_key, "manage_keys", auth_middleware)

    api_key_manager = request.app.state.api_key_manager

    try:
        await api_key_manager.revoke_key(key_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="API key not found")

    return {"status": "revoked"}


@keys_router.post("/keys/{key_id}/rotate", response_model=CreateKeyResponse)
async def rotate_key(
    key_id: uuid.UUID,
    request: Request,
    api_key: ApiKey = Depends(get_authenticated_key),
    auth_middleware: AuthMiddleware = Depends(get_auth_middleware),
) -> CreateKeyResponse:
    """Rotate an API key (admin only)."""
    require_permission(api_key, "manage_keys", auth_middleware)

    api_key_manager = request.app.state.api_key_manager

    try:
        plaintext, new_key = await api_key_manager.rotate_key(key_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="API key not found")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return CreateKeyResponse(
        id=new_key.id,
        key=plaintext,
        name=new_key.name,
        role=new_key.role,
    )
