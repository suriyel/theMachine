#!/usr/bin/env python
"""
Example: Data Model and Migrations (Feature #2)

Demonstrates SQLAlchemy async models for:
- Repository: Git repository metadata
- IndexJob: Indexing job tracking
- CodeChunk: Indexed code segments
- APIKey: API authentication keys
- QueryLog: Query execution logs

Prerequisites:
1. PostgreSQL running (DATABASE_URL in .env)
2. Tables created: alembic upgrade head

Run: python examples/02-data-models.py
"""

import asyncio
import hashlib
import uuid
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.db.session import async_session_maker
from src.shared.models import (
    APIKey,
    ChunkGranularity,
    CodeChunk,
    IndexJob,
    JobStatus,
    KeyStatus,
    QueryLog,
    QueryType,
    RepoStatus,
    Repository,
    TriggerType,
)


async def demo_repository(session: AsyncSession) -> Repository:
    """Demonstrate Repository model CRUD operations."""
    print("\n=== Repository Model ===")

    # Create a repository
    repo = Repository(
        url="https://github.com/example/demo-repo.git",
        name="demo-repo",
        languages=["Python", "TypeScript"],
        status=RepoStatus.REGISTERED,
    )
    session.add(repo)
    await session.flush()

    print(f"Created Repository:")
    print(f"  ID: {repo.id}")
    print(f"  URL: {repo.url}")
    print(f"  Name: {repo.name}")
    print(f"  Languages: {repo.languages}")
    print(f"  Status: {repo.status.value}")
    print(f"  Created at: {repo.created_at}")

    return repo


async def demo_index_job(session: AsyncSession, repo: Repository) -> IndexJob:
    """Demonstrate IndexJob model with relationship to Repository."""
    print("\n=== IndexJob Model ===")

    # Create an indexing job
    job = IndexJob(
        repo_id=repo.id,
        status=JobStatus.QUEUED,
        trigger_type=TriggerType.MANUAL,
    )
    session.add(job)
    await session.flush()

    print(f"Created IndexJob:")
    print(f"  ID: {job.id}")
    print(f"  Repo ID: {job.repo_id}")
    print(f"  Status: {job.status.value}")
    print(f"  Trigger: {job.trigger_type.value}")
    print(f"  Chunk count: {job.chunk_count}")

    return job


async def demo_code_chunk(session: AsyncSession, repo: Repository) -> CodeChunk:
    """Demonstrate CodeChunk model with composite ID generation."""
    print("\n=== CodeChunk Model ===")

    # Generate composite ID
    chunk_id = CodeChunk.generate_id(repo.id, "src/main.py", "main_function")
    print(f"Generated chunk ID: {chunk_id}")

    # Create a code chunk
    chunk = CodeChunk(
        id=chunk_id,
        repo_id=repo.id,
        file_path="src/main.py",
        language="Python",
        granularity=ChunkGranularity.FUNCTION,
        symbol_name="main_function",
        content='def main_function():\n    print("Hello, World!")\n',
        start_line=1,
        end_line=2,
    )
    session.add(chunk)
    await session.flush()

    print(f"Created CodeChunk:")
    print(f"  ID: {chunk.id}")
    print(f"  File path: {chunk.file_path}")
    print(f"  Language: {chunk.language}")
    print(f"  Granularity: {chunk.granularity.value}")
    print(f"  Symbol: {chunk.symbol_name}")
    print(f"  Lines: {chunk.start_line}-{chunk.end_line}")

    return chunk


async def demo_api_key(session: AsyncSession) -> APIKey:
    """Demonstrate APIKey model with secure hash storage."""
    print("\n=== APIKey Model ===")

    # Generate a secure key hash (SHA-256)
    raw_key = "sk-demo-key-example-12345"
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    # Create an API key
    api_key = APIKey(
        key_hash=key_hash,
        name="Demo API Key",
    )
    session.add(api_key)
    await session.flush()

    print(f"Created APIKey:")
    print(f"  ID: {api_key.id}")
    print(f"  Name: {api_key.name}")
    print(f"  Key hash (first 16 chars): {api_key.key_hash[:16]}...")
    print(f"  Status: {api_key.status.value}")
    print(f"  Is active: {api_key.is_active()}")

    return api_key


async def demo_query_log(session: AsyncSession, api_key: APIKey) -> QueryLog:
    """Demonstrate QueryLog model with correlation ID."""
    print("\n=== QueryLog Model ===")

    # Create a query log entry
    log = QueryLog(
        api_key_id=api_key.id,
        query_text="how to use async context manager",
        query_type=QueryType.NATURAL_LANGUAGE,
        repo_filter="demo-repo",
        language_filter="Python",
        result_count=3,
        latency_ms=142.5,
    )
    session.add(log)
    await session.flush()

    print(f"Created QueryLog:")
    print(f"  ID: {log.id}")
    print(f"  Correlation ID: {log.correlation_id}")
    print(f"  Query: {log.query_text}")
    print(f"  Type: {log.query_type.value}")
    print(f"  Results: {log.result_count}")
    print(f"  Latency: {log.latency_ms}ms")

    return log


async def demo_relationships(session: AsyncSession, repo: Repository):
    """Demonstrate ORM relationships."""
    print("\n=== ORM Relationships ===")

    # Query repository with relationships
    result = await session.execute(
        select(Repository).where(Repository.id == repo.id)
    )
    loaded_repo = result.scalar_one()

    print(f"Repository '{loaded_repo.name}' has:")
    print(f"  - {len(loaded_repo.index_jobs)} index job(s)")
    print(f"  - {len(loaded_repo.code_chunks)} code chunk(s)")


async def main():
    """Run all model demonstrations."""
    print("=" * 60)
    print("Feature #2: Data Model and Migrations - Examples")
    print("=" * 60)

    async with async_session_maker() as session:
        # Demo each model
        repo = await demo_repository(session)
        job = await demo_index_job(session, repo)
        chunk = await demo_code_chunk(session, repo)
        api_key = await demo_api_key(session)
        log = await demo_query_log(session, api_key)

        # Demo relationships
        await demo_relationships(session, repo)

        # Commit all changes
        await session.commit()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
