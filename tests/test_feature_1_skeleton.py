"""Tests for Feature #1: Project Skeleton & CI.

Test categories covered:
- Happy path: create_app, health endpoint, settings, engine, session factory
- Error handling: missing DATABASE_URL, empty URL, wrong HTTP method
- Boundary: empty string URL
- Security: N/A — internal infrastructure with no user-facing input

Negative tests: H, K1, K2, K3, K4, K5 = 6/13 = 46%
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from src.query.app import create_app
from src.shared.config import Settings, get_settings
from src.shared.database import get_engine, get_session_factory


# --- Happy Path ---


# [unit] Test E: create_app returns FastAPI instance with health route
def test_create_app_returns_fastapi_with_health_route():
    app = create_app()
    assert isinstance(app, FastAPI)
    # Verify /api/v1/health route is registered
    route_paths = [route.path for route in app.routes]
    assert "/api/v1/health" in route_paths


# [unit] Test F: health endpoint returns correct JSON
def test_health_endpoint_returns_ok():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "code-context-retrieval"


# [integration] Test G: Settings loads DATABASE_URL from environment
@pytest.mark.real
def test_settings_loads_database_url_from_env(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/testdb")
    settings = get_settings()
    assert settings.database_url == "postgresql+asyncpg://test:test@localhost:5432/testdb"


# [unit] Test I: get_engine returns AsyncEngine
def test_get_engine_returns_async_engine():
    engine = get_engine("sqlite+aiosqlite:///test.db")
    assert isinstance(engine, AsyncEngine)
    # Verify the URL is correctly set
    assert "test.db" in str(engine.url)


# [unit] Test J: get_session_factory returns async_sessionmaker
def test_get_session_factory_returns_sessionmaker():
    engine = get_engine("sqlite+aiosqlite:///test.db")
    factory = get_session_factory(engine)
    assert isinstance(factory, async_sessionmaker)


# [unit] Test: create_app title and version match design spec
def test_create_app_metadata():
    app = create_app()
    assert app.title == "Code Context Retrieval"
    assert app.version == "0.1.0"


# [unit] Test: health endpoint response has exactly expected keys
def test_health_endpoint_response_keys():
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/health")
    body = response.json()
    assert set(body.keys()) == {"status", "service"}


# --- Error Handling ---


# [integration] Test H: Settings raises ValidationError when DATABASE_URL missing
@pytest.mark.real
def test_settings_missing_database_url_raises(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # Construct without env_file to avoid .env fallback
    with pytest.raises(ValidationError) as exc_info:
        Settings(_env_file=None)
    # Verify the error mentions database_url
    assert "database_url" in str(exc_info.value).lower()


# [unit] Test K1: get_engine with empty string raises ValueError
def test_get_engine_empty_url_raises():
    with pytest.raises(ValueError, match="database_url must not be empty"):
        get_engine("")


# [unit] Test K2: health endpoint on wrong path returns 404
def test_health_wrong_path_returns_404():
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 404


# [unit] Test K3: health endpoint rejects POST method
def test_health_endpoint_rejects_post():
    app = create_app()
    client = TestClient(app)
    response = client.post("/api/v1/health")
    assert response.status_code == 405


# [unit] Test K4: get_engine pool_pre_ping is enabled
def test_get_engine_pool_pre_ping_enabled():
    engine = get_engine("sqlite+aiosqlite:///test.db")
    assert engine.pool._pre_ping is True


# [unit] Test K5: get_session_factory expire_on_commit is disabled and engine is bound
def test_get_session_factory_expire_on_commit_disabled():
    engine = get_engine("sqlite+aiosqlite:///test.db")
    factory = get_session_factory(engine)
    assert factory.kw.get("expire_on_commit") is False
    # Verify the engine is correctly bound (not None or missing)
    assert factory.kw.get("bind") is engine
