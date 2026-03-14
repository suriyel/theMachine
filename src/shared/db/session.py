"""Database session management."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.query.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""

    pass


async def init_db() -> None:
    """Initialize database connection pool and create tables.

    This creates all tables defined by models inheriting from Base.
    For production, use Alembic migrations instead.
    """
    # Import all models to register them with Base.metadata
    import src.shared.models  # noqa: F401

    async with engine.begin() as conn:
        # Create tables if not exist (for dev; use Alembic in production)
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session.

    Yields an async session that automatically commits on success
    or rolls back on exception.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
