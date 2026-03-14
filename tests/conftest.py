"""Pytest configuration."""

import pytest
import asyncio
from typing import Generator

import pytest_asyncio


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_session():
    """Create database session for tests."""
    # TODO: Add testcontainers for PostgreSQL
    yield
