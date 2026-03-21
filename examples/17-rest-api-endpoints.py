#!/usr/bin/env python3
"""Feature #17 — REST API Endpoints demo.

Demonstrates all REST API endpoints using httpx against the FastAPI app
via TestClient (no running server required).

Usage:
    python examples/17-rest-api-endpoints.py
"""

import json
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from src.query.api.v1.deps import get_authenticated_key
from src.query.app import create_app
from src.query.response_models import CodeResult, QueryResponse
from src.shared.models.api_key import ApiKey


def _mock_api_key(role: str = "admin") -> ApiKey:
    key = MagicMock(spec=ApiKey)
    key.id = uuid.uuid4()
    key.name = "demo-key"
    key.role = role
    key.is_active = True
    key.created_at = None
    key.expires_at = None
    key.key_hash = "demohash"
    return key


def _mock_session_factory():
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = []
    result_mock.scalar_one_or_none.return_value = None
    session.execute.return_value = result_mock
    session.commit = AsyncMock()
    session.add = MagicMock()

    @asynccontextmanager
    async def factory():
        yield session

    return factory


def build_app():
    qh = MagicMock()
    qh.detect_query_type.return_value = "nl"
    qh.handle_nl_query = AsyncMock(
        return_value=QueryResponse(
            query="how to parse JSON",
            query_type="nl",
            code_results=[
                CodeResult(
                    file_path="src/utils/parser.py",
                    content="def parse_json(data): ...",
                    relevance_score=0.92,
                )
            ],
        )
    )

    auth = MagicMock()
    auth.check_permission.return_value = True

    akm = AsyncMock()
    new_key = _mock_api_key("read")
    akm.create_key.return_value = ("ccr_demo_key_abc123", new_key)
    akm.list_keys.return_value = [new_key]
    akm.revoke_key = AsyncMock()
    akm.rotate_key.return_value = ("ccr_rotated_xyz789", new_key)

    es = AsyncMock()
    es.health_check.return_value = True
    qdrant = AsyncMock()
    qdrant.health_check.return_value = True
    redis = AsyncMock()
    redis.health_check.return_value = True

    app = create_app(
        query_handler=qh,
        auth_middleware=auth,
        api_key_manager=akm,
        session_factory=_mock_session_factory(),
        es_client=es,
        qdrant_client=qdrant,
        redis_client=redis,
    )
    app.dependency_overrides[get_authenticated_key] = lambda: _mock_api_key("admin")
    return app


def pp(label: str, resp):
    print(f"\n{'='*60}")
    print(f"{label}  [{resp.status_code}]")
    print(json.dumps(resp.json(), indent=2, default=str))


def main():
    app = build_app()
    c = TestClient(app)

    # 1. Health check (no auth required)
    pp("GET /api/v1/health", c.get("/api/v1/health"))

    # 2. Query endpoint
    pp(
        "POST /api/v1/query",
        c.post("/api/v1/query", json={"query": "how to parse JSON"}),
    )

    # 3. List repos
    pp("GET /api/v1/repos", c.get("/api/v1/repos"))

    # 4. Create API key
    pp(
        "POST /api/v1/keys",
        c.post("/api/v1/keys", json={"name": "ci-reader", "role": "read"}),
    )

    # 5. List API keys
    pp("GET /api/v1/keys", c.get("/api/v1/keys"))

    # 6. Rotate key
    key_id = uuid.uuid4()
    pp(f"POST /api/v1/keys/{key_id}/rotate", c.post(f"/api/v1/keys/{key_id}/rotate"))

    # 7. Delete key
    pp(f"DELETE /api/v1/keys/{key_id}", c.delete(f"/api/v1/keys/{key_id}"))

    print("\n" + "=" * 60)
    print("All REST API endpoints demonstrated successfully.")


if __name__ == "__main__":
    main()
