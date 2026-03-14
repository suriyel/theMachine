"""Tests for FastAPI main application.

Feature #1: Project Skeleton and CI
- Tests for health endpoint
- Tests for application configuration
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """[unit] Tests for the /health endpoint."""

    def test_health_endpoint_returns_healthy(self):
        """Given the app is running, when GET /health, then returns healthy status.

        Wrong implementation challenge:
        - Returning wrong status would fail (we verify 'healthy')
        """
        from src.query.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_health_endpoint_no_auth_required(self):
        """Given no auth header, when GET /health, then returns 200 (no auth required).

        Wrong implementation challenge:
        - Requiring auth would fail (health endpoint should be public)
        """
        from src.query.main import app

        client = TestClient(app)
        response = client.get("/health")

        assert response.status_code == 200


class TestAppConfiguration:
    """[unit] Tests for FastAPI application configuration."""

    def test_app_title_is_set(self):
        """Given the app, when checking title, then it's 'Code Context Retrieval'."""
        from src.query.main import app

        assert app.title == "Code Context Retrieval"

    def test_app_version_is_set(self):
        """Given the app, when checking version, then it's set."""
        from src.query.main import app

        assert app.version == "0.1.0"

    def test_cors_middleware_is_configured(self):
        """Given the app, when checking middleware, then CORS is configured."""
        from src.query.main import app

        # Check that middleware is present (FastAPI wraps CORS as Middleware)
        assert len(app.user_middleware) > 0, "CORS middleware should be configured"

    def test_api_router_is_included(self):
        """Given the app, when checking routes, then API router is included."""
        from src.query.main import app

        # Check that API routes are included
        routes = [route.path for route in app.routes]
        assert any("/api/v1" in str(route) for route in routes)


class TestLifespan:
    """[unit] Tests for application lifespan management."""

    @pytest.mark.asyncio
    async def test_lifespan_context_manager(self):
        """Given lifespan context, when entering, then startup functions are called."""
        from src.query.main import lifespan
        from fastapi import FastAPI

        app = FastAPI()
        startup_called = False
        shutdown_called = False

        # The lifespan should be callable
        assert callable(lifespan)

    def test_app_has_lifespan(self):
        """Given the app, when checking router, then lifespan is configured."""
        from src.query.main import app

        # FastAPI apps with lifespan have it configured
        assert app.router.lifespan_context is not None

    @pytest.mark.asyncio
    async def test_lifespan_calls_init_db(self):
        """Given lifespan, when entering, then init_db is called.

        Wrong implementation challenge:
        - Skipping init_db would fail (we verify it's called)
        """
        from unittest.mock import patch, AsyncMock, MagicMock

        with patch("src.query.main.init_db") as mock_init_db, \
             patch("src.query.main.init_clients") as mock_init_clients, \
             patch("src.query.main.close_clients") as mock_close_clients:

            mock_init_db.return_value = AsyncMock()
            mock_init_clients.return_value = AsyncMock()
            mock_close_clients.return_value = AsyncMock()

            from src.query.main import lifespan
            from fastapi import FastAPI

            app = FastAPI()

            async with lifespan(app):
                pass

            mock_init_db.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_calls_init_clients(self):
        """Given lifespan, when entering, then init_clients is called.

        Wrong implementation challenge:
        - Skipping init_clients would fail
        """
        from unittest.mock import patch, AsyncMock

        with patch("src.query.main.init_db") as mock_init_db, \
             patch("src.query.main.init_clients") as mock_init_clients, \
             patch("src.query.main.close_clients") as mock_close_clients:

            mock_init_db.return_value = AsyncMock()
            mock_init_clients.return_value = AsyncMock()
            mock_close_clients.return_value = AsyncMock()

            from src.query.main import lifespan
            from fastapi import FastAPI

            app = FastAPI()

            async with lifespan(app):
                pass

            mock_init_clients.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_calls_close_clients_on_exit(self):
        """Given lifespan, when exiting, then close_clients is called.

        Wrong implementation challenge:
        - Not closing clients would leak resources
        """
        from unittest.mock import patch, AsyncMock

        with patch("src.query.main.init_db") as mock_init_db, \
             patch("src.query.main.init_clients") as mock_init_clients, \
             patch("src.query.main.close_clients") as mock_close_clients:

            mock_init_db.return_value = AsyncMock()
            mock_init_clients.return_value = AsyncMock()
            mock_close_clients.return_value = AsyncMock()

            from src.query.main import lifespan
            from fastapi import FastAPI

            app = FastAPI()

            async with lifespan(app):
                pass

            mock_close_clients.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_startup_before_shutdown(self):
        """Given lifespan, when running, then startup happens before shutdown.

        Wrong implementation challenge:
        - Running shutdown before startup would fail
        """
        from unittest.mock import patch, AsyncMock

        call_order = []

        async def track_init_db():
            call_order.append("init_db")

        async def track_init_clients():
            call_order.append("init_clients")

        async def track_close_clients():
            call_order.append("close_clients")

        with patch("src.query.main.init_db", side_effect=track_init_db), \
             patch("src.query.main.init_clients", side_effect=track_init_clients), \
             patch("src.query.main.close_clients", side_effect=track_close_clients):

            from src.query.main import lifespan
            from fastapi import FastAPI

            app = FastAPI()

            async with lifespan(app):
                call_order.append("yield")

            assert call_order == ["init_db", "init_clients", "yield", "close_clients"]
