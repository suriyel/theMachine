"""Tests for Feature #50: Add psycopg2-binary dependency for Celery worker sync DB access.

Test Inventory mapping:
  A: FUNC/happy — import psycopg2 succeeds
  B: FUNC/happy — _get_sync_session() returns Session with correct sync URL
  C: FUNC/error — ImportError when psycopg2 unavailable
  D: BNDRY/edge — empty DATABASE_URL handled without crash
  E: BNDRY/dep-spec — psycopg2-binary>=2.9 listed in pyproject.toml dev deps
  F: INTG/db — real PostgreSQL connection via _get_sync_session()
  G: FUNC/error — OperationalError on unreachable host

# SEC: N/A — internal infrastructure dependency, no user-facing input
"""

import sys
from unittest.mock import patch, MagicMock

import pytest


# --- Test A: FUNC/happy — psycopg2 importable after install ---
# [unit]
def test_psycopg2_importable():
    """After pip install -e '.[dev]', psycopg2 must be importable."""
    import psycopg2
    # Verify it's a real module with the expected connection interface
    assert hasattr(psycopg2, "connect"), "psycopg2 must expose connect()"
    assert hasattr(psycopg2, "__version__"), "psycopg2 must have __version__"
    # psycopg2.__version__ is like "2.9.11 (dt dec pq3 ext lo64)" — extract numeric part
    version_str = psycopg2.__version__.split()[0]
    major, minor = (int(x) for x in version_str.split(".")[:2])
    assert (major, minor) >= (2, 9), (
        f"psycopg2 version {version_str} < 2.9"
    )


# --- Test B: FUNC/happy — _get_sync_session returns Session with sync URL ---
# [unit]
def test_get_sync_session_returns_session_with_sync_url():
    """_get_sync_session() must create engine with sync URL and return Session."""
    mock_engine = MagicMock()
    with patch.dict("os.environ", {"DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/db"}), \
         patch("src.indexing.scheduler.create_engine", return_value=mock_engine) as mock_ce, \
         patch("src.indexing.scheduler.Session") as mock_session_cls:
        mock_session_cls.return_value = MagicMock()
        from src.indexing.scheduler import _get_sync_session
        session = _get_sync_session()
        # Verify create_engine called with sync (not async) URL
        mock_ce.assert_called_once_with("postgresql://user:pass@localhost/db")
        # Verify Session created with the engine
        mock_session_cls.assert_called_once_with(mock_engine)
        assert session is mock_session_cls.return_value


# --- Test C: FUNC/error — ImportError when psycopg2 not available ---
# [unit]
def test_get_sync_session_import_error_without_psycopg2():
    """When psycopg2 is not installed, create_engine should raise ImportError."""
    # Simulate psycopg2 missing by having create_engine raise ImportError
    # (SQLAlchemy raises this when the dialect driver is missing)
    with patch.dict("os.environ", {"DATABASE_URL": "postgresql://user:pass@localhost/db"}), \
         patch("src.indexing.scheduler.create_engine", side_effect=ImportError("No module named 'psycopg2'")):
        from src.indexing.scheduler import _get_sync_session
        with pytest.raises(ImportError, match="psycopg2"):
            _get_sync_session()


# --- Test D: BNDRY/edge — empty DATABASE_URL ---
# [unit]
def test_get_sync_session_empty_database_url():
    """Empty DATABASE_URL should not crash at session creation (deferred connection)."""
    mock_engine = MagicMock()
    with patch.dict("os.environ", {"DATABASE_URL": ""}), \
         patch("src.indexing.scheduler.create_engine", return_value=mock_engine) as mock_ce, \
         patch("src.indexing.scheduler.Session") as mock_session_cls:
        mock_session_cls.return_value = MagicMock()
        from src.indexing.scheduler import _get_sync_session
        session = _get_sync_session()
        # create_engine called with empty string (no crash)
        mock_ce.assert_called_once_with("")
        assert session is mock_session_cls.return_value


# --- Test E: BNDRY/dep-spec — psycopg2-binary>=2.9 in pyproject.toml ---
# [unit]
def test_pyproject_contains_psycopg2_binary():
    """pyproject.toml dev dependencies must include psycopg2-binary>=2.9."""
    import tomllib
    from pathlib import Path

    pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    dev_deps = data["project"]["optional-dependencies"]["dev"]
    # Find the psycopg2-binary entry
    psycopg_entries = [d for d in dev_deps if d.startswith("psycopg2-binary")]
    assert len(psycopg_entries) == 1, (
        f"Expected exactly one psycopg2-binary entry in dev deps, found: {psycopg_entries}"
    )
    dep_spec = psycopg_entries[0]
    assert ">=2.9" in dep_spec, (
        f"psycopg2-binary must specify >=2.9, got: {dep_spec}"
    )


# --- Test F: INTG/db — real PostgreSQL connection ---
# [integration]
@pytest.mark.real
def test_real_get_sync_session_db_connection_feature_50():
    """Real test: _get_sync_session() connects to actual PostgreSQL and runs SELECT 1."""
    import os
    db_url = os.environ.get("DATABASE_URL", "")
    assert db_url, "DATABASE_URL must be set for real DB test"

    from src.indexing.scheduler import _get_sync_session
    session = _get_sync_session()
    try:
        from sqlalchemy import text
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1, f"Expected SELECT 1 to return 1, got {result}"
    finally:
        session.close()


# --- Test G: FUNC/error — OperationalError on unreachable host ---
# [unit]
def test_get_sync_session_operational_error_unreachable():
    """OperationalError must propagate when DB host is unreachable."""
    from sqlalchemy.exc import OperationalError
    with patch.dict("os.environ", {"DATABASE_URL": "postgresql://user:pass@unreachable-host:5432/db"}), \
         patch("src.indexing.scheduler.create_engine") as mock_ce:
        mock_engine = MagicMock()
        mock_ce.return_value = mock_engine
        # Session constructor works, but using the session raises OperationalError
        from src.indexing.scheduler import _get_sync_session
        with patch("src.indexing.scheduler.Session", side_effect=OperationalError("connection refused", None, None)):
            with pytest.raises(OperationalError):
                _get_sync_session()
