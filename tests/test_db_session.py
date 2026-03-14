"""Tests for database session management.

Feature #1: Project Skeleton and CI
- Tests for get_db session management
- Tests for engine configuration
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestGetDb:
    """[unit] Tests for get_db session generator."""

    @pytest.mark.asyncio
    async def test_get_db_yields_session(self):
        """Given get_db, when called, then yields AsyncSession.

        Wrong implementation challenge:
        - Yielding None would fail (we verify session is valid)
        """
        from sqlalchemy.ext.asyncio import AsyncSession
        from src.shared.db import session as session_module

        sessions = []
        async for session in session_module.get_db():
            sessions.append(session)
            assert isinstance(session, AsyncSession)

        assert len(sessions) == 1

    @pytest.mark.asyncio
    async def test_get_db_commits_on_success(self):
        """Given get_db, when no exception, then commits session.

        Wrong implementation challenge:
        - Not committing would fail (we verify commit is called)
        """
        from src.shared.db import session as session_module

        with patch("src.shared.db.session.async_session_maker") as mock_maker:
            mock_session = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.rollback = AsyncMock()

            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_maker.return_value = mock_context

            async for _ in session_module.get_db():
                pass

            mock_session.commit.assert_called_once()
            mock_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_db_reraises_exception(self):
        """Given get_db, when exception raised, then reraises after rollback.

        Wrong implementation challenge:
        - Swallowing exception would fail (we verify it's raised)
        """
        from src.shared.db import session as session_module

        with patch("src.shared.db.session.async_session_maker") as mock_maker:
            mock_session = AsyncMock()
            mock_session.rollback = AsyncMock()

            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=mock_session)
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_maker.return_value = mock_context

            raised = False
            try:
                async for _ in session_module.get_db():
                    raise RuntimeError("db error")
            except RuntimeError as e:
                raised = True
                assert str(e) == "db error"

            assert raised, "Exception should be reraised"


class TestBase:
    """[unit] Tests for SQLAlchemy Base class."""

    def test_base_is_declarative_base(self):
        """Given Base, when checking type, then is DeclarativeBase subclass.

        Wrong implementation challenge:
        - Using wrong base class would fail
        """
        from sqlalchemy.orm import DeclarativeBase
        from src.shared.db.session import Base

        assert issubclass(Base, DeclarativeBase)

    def test_base_has_metadata(self):
        """Given Base, when checking metadata, then has SQLAlchemy metadata.

        Wrong implementation challenge:
        - Missing metadata would fail (required for ORM models)
        """
        from src.shared.db.session import Base

        assert hasattr(Base, "metadata")
        assert Base.metadata is not None


class TestEngineConfiguration:
    """[unit] Tests for SQLAlchemy engine configuration."""

    def test_engine_echo_disabled(self):
        """Given engine, when checking echo, then is False for production.

        Wrong implementation challenge:
        - echo=True would expose SQL in logs (security concern)
        """
        from src.shared.db.session import engine

        assert engine.echo is False

    def test_engine_uses_asyncpg(self):
        """Given engine, when checking URL, then uses asyncpg driver.

        Wrong implementation challenge:
        - Using wrong driver (psycopg2) would fail async operations
        """
        from src.shared.db.session import engine

        assert "asyncpg" in str(engine.url)

    def test_session_maker_expire_on_commit_false(self):
        """Given session maker, when checking config, then expire_on_commit is False.

        Wrong implementation challenge:
        - expire_on_commit=True would cause lazy load issues after commit
        """
        from src.shared.db.session import async_session_maker

        assert async_session_maker.kw.get("expire_on_commit") is False
