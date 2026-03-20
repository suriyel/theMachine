"""Tests for Web UI routes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


class TestLoginPage:
    """Tests for GET /login."""

    def test_login_page_returns_html(self):
        """Test login page returns HTML content."""
        from src.query.api.web import login_page
        from fastapi import Request

        # Create mock request
        mock_request = MagicMock(spec=Request)
        mock_request.cookies.get.return_value = None

        # Call the function directly
        import asyncio
        result = asyncio.run(login_page(mock_request))

        # Result is HTML string, not response object
        assert isinstance(result, str)
        assert '<form' in result

    def test_login_page_contains_form(self):
        """Test login page contains form elements."""
        from src.query.api.web import login_page
        from fastapi import Request

        mock_request = MagicMock(spec=Request)
        mock_request.cookies.get.return_value = None

        import asyncio
        result = asyncio.run(login_page(mock_request))

        assert '<form' in result
        assert 'name="api_key"' in result


class TestSessionManagement:
    """Tests for session management."""

    def test_create_session_generates_token(self):
        """Test session creation generates token."""
        from src.query.dependencies import create_session, _sessions

        # Clear sessions
        _sessions.clear()

        # Create session
        token = create_session(1, "test-key")

        # Verify token exists and session stored
        assert token is not None
        assert token in _sessions
        assert _sessions[token]["api_key_id"] == 1

        # Cleanup
        del _sessions[token]

    def test_get_session_returns_none_for_invalid(self):
        """Test get_session returns None for invalid token."""
        from src.query.dependencies import get_session

        # Create mock request
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = None

        result = get_session(mock_request)
        assert result is None

    def test_get_session_returns_data_for_valid_token(self):
        """Test get_session returns data for valid token."""
        from src.query.dependencies import create_session, get_session, _sessions

        # Clear and setup
        _sessions.clear()
        token = create_session(1, "test-key")

        mock_request = MagicMock()
        mock_request.cookies.get.return_value = token

        result = get_session(mock_request)
        assert result is not None
        assert result["api_key_id"] == 1

        # Cleanup
        del _sessions[token]


class TestRequireAuth:
    """Tests for require_auth function."""

    def test_require_auth_raises_for_no_session(self):
        """Test require_auth raises HTTPException for no session."""
        from fastapi import HTTPException
        from src.query.dependencies import require_auth

        mock_request = MagicMock()
        mock_request.cookies.get.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            require_auth(mock_request)

        assert exc_info.value.status_code == 401

    def test_require_auth_returns_session_for_valid(self):
        """Test require_auth returns session for valid token."""
        from src.query.dependencies import create_session, require_auth, _sessions

        # Clear and setup
        _sessions.clear()
        token = create_session(1, "test-key")

        mock_request = MagicMock()
        mock_request.cookies.get.return_value = token

        result = require_auth(mock_request)
        assert result["api_key_id"] == 1

        # Cleanup
        del _sessions[token]


class TestLogout:
    """Tests for logout functionality."""

    def test_destroy_session_removes_session(self):
        """Test destroy_session removes session."""
        from src.query.dependencies import create_session, destroy_session, _sessions

        # Clear and setup
        _sessions.clear()
        token = create_session(1, "test-key")

        mock_request = MagicMock()
        mock_request.cookies.get.return_value = token

        # Destroy session
        destroy_session(mock_request)

        # Verify removed
        assert token not in _sessions


class TestWebRoutesMount:
    """Tests that routes are properly mounted."""

    def test_login_route_exists(self):
        """Test /login route exists."""
        from src.query.main import app

        routes = [r.path for r in app.routes]
        assert "/login" in routes

    def test_search_route_exists(self):
        """Test /search route exists."""
        from src.query.main import app

        routes = [r.path for r in app.routes]
        assert "/search" in routes

    def test_logout_route_exists(self):
        """Test /logout route exists."""
        from src.query.main import app

        routes = [r.path for r in app.routes]
        assert "/logout" in routes


class TestSupportedLanguages:
    """Tests for supported languages."""

    def test_supported_languages_defined(self):
        """Test all required languages are defined."""
        from src.query.api.web import SUPPORTED_LANGUAGES

        assert "java" in SUPPORTED_LANGUAGES
        assert "python" in SUPPORTED_LANGUAGES
        assert "typescript" in SUPPORTED_LANGUAGES
        assert "javascript" in SUPPORTED_LANGUAGES
        assert "c" in SUPPORTED_LANGUAGES
        assert "cpp" in SUPPORTED_LANGUAGES


class TestTemplateRendering:
    """Tests for template rendering."""

    def test_search_template_renders(self):
        """Test search template can render with context."""
        from src.query.api.web import jinja_env

        template = jinja_env.get_template("search.html")
        content = template.render(
            query="test",
            language_filter="python",
            results=[],
            error=None,
            initial=False,
        )

        assert "Search code context" in content
        assert "test" in content
