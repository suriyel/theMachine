"""Example: Feature #43 — query-api Docker Image.

Demonstrates calling build_app() to wire all production services
from environment variables, verifying that the FastAPI instance has
all expected service instances on app.state.

This example uses in-process environment variables with fake/test URLs
so it can be run without actual running services (all clients are lazy —
they do not connect until their async connect() method is called).

Usage:
    Set required env vars, then run:
        python examples/43-query-api-entrypoint.py
"""

import os
import sys

# Provide fake env vars so build_app() can wire the app without real services
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/demo")
os.environ.setdefault("ELASTICSEARCH_URL", "http://localhost:9200")
os.environ.setdefault("QDRANT_URL", "http://localhost:6333")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SECRET_KEY", "demo-secret-key")

# Add src to path for direct-script execution outside the installed package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI  # noqa: E402

from src.query.main import build_app  # noqa: E402
from src.query.query_handler import QueryHandler  # noqa: E402
from src.shared.clients.elasticsearch import ElasticsearchClient  # noqa: E402
from src.shared.clients.qdrant import QdrantClientWrapper  # noqa: E402
from src.shared.clients.redis import RedisClient  # noqa: E402


def main() -> None:
    print("Building query-api app from environment variables...")

    app = build_app()

    # Verify it's a real FastAPI instance
    assert isinstance(app, FastAPI), f"Expected FastAPI, got {type(app)}"
    print(f"  app type: {type(app).__name__}")
    print(f"  app title: {app.title}")

    # Verify service wiring on app.state
    assert isinstance(app.state.query_handler, QueryHandler)
    print(f"  query_handler: {type(app.state.query_handler).__name__}")

    assert isinstance(app.state.es_client, ElasticsearchClient)
    print(f"  es_client: {type(app.state.es_client).__name__} (url={app.state.es_client._url})")

    assert isinstance(app.state.qdrant_client, QdrantClientWrapper)
    print(f"  qdrant_client: {type(app.state.qdrant_client).__name__} (url={app.state.qdrant_client._url})")

    assert isinstance(app.state.redis_client, RedisClient)
    print(f"  redis_client: {type(app.state.redis_client).__name__} (url={app.state.redis_client._url})")

    assert app.state.session_factory is not None
    print(f"  session_factory: {type(app.state.session_factory).__name__}")

    assert app.state.auth_middleware is not None
    print(f"  auth_middleware: {type(app.state.auth_middleware).__name__}")

    assert app.state.api_key_manager is not None
    print(f"  api_key_manager: {type(app.state.api_key_manager).__name__}")

    assert app.state.query_cache is not None
    print(f"  query_cache: {type(app.state.query_cache).__name__}")

    print()
    print("Routes registered:")
    for route in app.routes:
        if hasattr(route, "path"):
            methods = getattr(route, "methods", {"*"})
            print(f"  {sorted(methods)} {route.path}")

    print()
    print("OK — build_app() wires all services. "
          "Run 'python -m src.query.main' inside the Docker container to start the server.")


if __name__ == "__main__":
    main()
