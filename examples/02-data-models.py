#!/usr/bin/env python3
"""Example: Data Model & Storage Client usage.

Demonstrates:
1. Creating SQLAlchemy model instances with defaults
2. Instantiating storage client wrappers
3. Checking client interface methods
"""

import asyncio
import uuid

from src.shared.models import (
    ApiKey,
    ApiKeyRepoAccess,
    Base,
    IndexJob,
    QueryLog,
    Repository,
)
from src.shared.clients import (
    ElasticsearchClient,
    QdrantClientWrapper,
    RedisClient,
)


def demo_models() -> None:
    """Create model instances and inspect defaults."""
    print("=== SQLAlchemy Models ===\n")

    # Repository with defaults
    repo = Repository(name="flask", url="https://github.com/pallets/flask")
    print(f"Repository: name={repo.name}, url={repo.url}")
    print(f"  id={repo.id} (UUID auto-generated)")
    print(f"  status={repo.status} (default: 'pending')")

    # IndexJob with defaults
    job = IndexJob(repo_id=repo.id, branch="main")
    print(f"\nIndexJob: repo_id={job.repo_id}, branch={job.branch}")
    print(f"  status={job.status} (default: 'pending')")
    print(f"  phase={job.phase} (default: 'queued')")

    # ApiKey
    key = ApiKey(key_hash="sha256:abc123", name="ci-bot", role="read")
    print(f"\nApiKey: name={key.name}, role={key.role}")
    print(f"  is_active={key.is_active} (default: True)")

    # QueryLog
    log = QueryLog(
        api_key_id=key.id,
        query_text="how to parse json in python",
        query_type="natural_language",
        result_count=3,
        retrieval_ms=45.2,
        rerank_ms=12.1,
        total_ms=57.3,
    )
    print(f"\nQueryLog: query='{log.query_text}'")
    print(f"  timing: retrieval={log.retrieval_ms}ms, rerank={log.rerank_ms}ms, total={log.total_ms}ms")

    print(f"\nAll models in Base.metadata: {sorted(Base.metadata.tables.keys())}")


def demo_clients() -> None:
    """Instantiate client wrappers and inspect interface."""
    print("\n=== Storage Clients ===\n")

    es = ElasticsearchClient(url="http://localhost:9200")
    qd = QdrantClientWrapper(url="http://localhost:6333")
    rd = RedisClient(url="redis://localhost:6379/0")

    for name, client in [("Elasticsearch", es), ("Qdrant", qd), ("Redis", rd)]:
        methods = ["connect", "health_check", "close"]
        has_all = all(hasattr(client, m) for m in methods)
        print(f"{name}: has connect/health_check/close = {has_all}")

    # Demonstrate validation
    print("\nValidation test:")
    try:
        ElasticsearchClient(url="")
    except ValueError as e:
        print(f"  ElasticsearchClient('') -> ValueError: {e}")


if __name__ == "__main__":
    demo_models()
    demo_clients()
