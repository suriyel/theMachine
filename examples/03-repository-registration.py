"""Example: Repository Registration with RepoManager.

Demonstrates:
- Registering a Git repository URL
- Registering with an explicit branch (Wave 1)
- Registering without a branch (default branch detected at clone time)
- URL validation and normalization
- Duplicate detection (branch-independent)
- Error handling for invalid URLs

Requires: DATABASE_URL environment variable set (or .env file).
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.shared.exceptions import ConflictError, ValidationError
from src.shared.services.repo_manager import RepoManager


async def main() -> None:
    # Use in-memory SQLite for this example (no external DB needed)
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    from src.shared.models.base import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session_factory = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_factory() as session:
        manager = RepoManager(session=session)

        # 1. Register a valid repository (no branch → default detection)
        print("1. Registering https://github.com/pallets/flask (no branch) ...")
        repo = await manager.register("https://github.com/pallets/flask")
        print(f"   -> id={repo.id}")
        print(f"   -> name={repo.name}")
        print(f"   -> url={repo.url}")
        print(f"   -> status={repo.status}")
        print(f"   -> indexed_branch={repo.indexed_branch}  (None = detect default)")

        # 2. Register with explicit branch (Wave 1)
        print("\n2. Registering with branch='develop' ...")
        repo2 = await manager.register(
            "https://github.com/psf/requests", branch="develop"
        )
        print(f"   -> url={repo2.url}")
        print(f"   -> indexed_branch={repo2.indexed_branch}")

        # 3. URL normalization: .git suffix and trailing slash are stripped
        print("\n3. Registering https://github.com/django/django.git/ ...")
        repo3 = await manager.register("https://github.com/django/django.git/")
        print(f"   -> url={repo3.url}  (normalized)")

        # 4. Duplicate detection (branch-independent)
        print("\n4. Attempting duplicate with different branch ...")
        try:
            await manager.register(
                "https://github.com/pallets/flask", branch="develop"
            )
        except ConflictError as e:
            print(f"   -> ConflictError: {e}")

        # 5. Invalid URL handling
        print("\n5. Attempting invalid URL ...")
        try:
            await manager.register("not-a-url")
        except ValidationError as e:
            print(f"   -> ValidationError: {e}")

        # 6. Empty URL handling
        print("\n6. Attempting empty URL ...")
        try:
            await manager.register("")
        except ValidationError as e:
            print(f"   -> ValidationError: {e}")

    await engine.dispose()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
