"""
Pytest configuration and fixtures for async SQLAlchemy tests.

Handles:
- Session-scoped event loop
- Engine lifecycle management
- Database table setup/teardown via Alembic migrations
"""

import asyncio
import subprocess
import sys
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.query.config import settings


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create session-scoped event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


async def drop_enums_and_tables(engine):
    """Drop all enums and tables directly via SQL."""
    enum_types = ["key_status", "repo_status", "job_status", "trigger_type", "chunk_granularity", "query_type"]
    tables = ["query_logs", "code_chunks", "index_jobs", "repositories", "api_keys"]

    async with engine.begin() as conn:
        # Drop tables first (they depend on enums)
        for table in tables:
            try:
                await conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
            except Exception:
                pass
        # Drop enums
        for enum in enum_types:
            try:
                await conn.execute(text(f"DROP TYPE IF EXISTS {enum} CASCADE"))
            except Exception:
                pass
        # Drop alembic_version table
        try:
            await conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
        except Exception:
            pass


@pytest_asyncio.fixture(scope="session")
async def session_engine():
    """Create session-scoped async engine with tables created via Alembic."""
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

    # Clean up any existing enums and tables first
    await drop_enums_and_tables(engine)

    # Create tables via migration
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Alembic upgrade failed: {result.stderr}")

    yield engine

    # Cleanup: drop all tables/enums and dispose engine
    await drop_enums_and_tables(engine)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(session_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for each test with automatic cleanup."""
    async_session_maker = async_sessionmaker(
        session_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session
        # Rollback any uncommitted changes
        await session.rollback()

    # Cleanup tables after each test
    async with async_session_maker() as session:
        async with session.begin():
            await session.execute(text("DELETE FROM query_logs"))
            await session.execute(text("DELETE FROM code_chunks"))
            await session.execute(text("DELETE FROM index_jobs"))
            await session.execute(text("DELETE FROM repositories"))
            await session.execute(text("DELETE FROM api_keys"))
