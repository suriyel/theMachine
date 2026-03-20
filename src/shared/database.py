"""Database engine and session factory."""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)


def get_engine(database_url: str) -> AsyncEngine:
    """Create an async SQLAlchemy engine.

    Args:
        database_url: Database connection URL.

    Returns:
        Configured AsyncEngine instance.

    Raises:
        ValueError: If database_url is empty.
    """
    if not database_url:
        raise ValueError("database_url must not be empty")
    return create_async_engine(database_url, echo=False, pool_pre_ping=True)


def get_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    """Create an async session factory bound to the given engine.

    Args:
        engine: AsyncEngine to bind sessions to.

    Returns:
        Configured async_sessionmaker instance.
    """
    return async_sessionmaker(engine, expire_on_commit=False)
