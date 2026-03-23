"""Production entrypoint for the codecontext-api Docker image.

This module is the top-level entry point run by the container:
    CMD ["python", "-m", "src.query.main"]

Design split:
  - build_app() — testable construction unit. Reads env vars, wires all
    service clients and services, returns a configured FastAPI instance.
    Can be called in tests without starting a server process.
  - main() — process entry. Calls build_app(), starts uvicorn. Not testable
    in unit tests without patching uvicorn.run.
"""

from __future__ import annotations

import os
import sys

import uvicorn

from src.query.app import create_app
from src.query.query_cache import QueryCache
from src.query.query_handler import QueryHandler
from src.query.rank_fusion import RankFusion
from src.query.reranker import Reranker
from src.query.response_builder import ResponseBuilder
from src.query.retriever import Retriever
from src.shared.clients.elasticsearch import ElasticsearchClient
from src.shared.clients.qdrant import QdrantClientWrapper
from src.shared.clients.redis import RedisClient
from src.shared.database import get_engine, get_session_factory
from src.shared.services.api_key_manager import APIKeyManager
from src.shared.services.auth_middleware import AuthMiddleware

_REQUIRED_ENV_VARS = (
    "DATABASE_URL",
    "ELASTICSEARCH_URL",
    "QDRANT_URL",
    "REDIS_URL",
    "SECRET_KEY",
)


def build_app():
    """Read env vars, wire all services, and return a configured FastAPI app.

    Postconditions:
    - Returns a FastAPI instance.
    - app.state.query_handler is a QueryHandler.
    - app.state.es_client is an ElasticsearchClient.
    - create_app() is called exactly once.

    Raises:
        KeyError: If any required env var is absent from os.environ.
    """
    database_url = os.environ["DATABASE_URL"]
    es_url = os.environ["ELASTICSEARCH_URL"]
    qdrant_url = os.environ["QDRANT_URL"]
    redis_url = os.environ["REDIS_URL"]
    os.environ["SECRET_KEY"]  # fail-fast check; value used by auth middleware

    es_client = ElasticsearchClient(url=es_url)
    qdrant_client = QdrantClientWrapper(url=qdrant_url)
    redis_client = RedisClient(url=redis_url)
    engine = get_engine(database_url)
    session_factory = get_session_factory(engine)

    retriever = Retriever(es_client=es_client, qdrant_client=qdrant_client)
    rank_fusion = RankFusion()
    reranker = Reranker()
    response_builder = ResponseBuilder()
    query_handler = QueryHandler(
        retriever=retriever,
        rank_fusion=rank_fusion,
        reranker=reranker,
        response_builder=response_builder,
    )
    auth_middleware = AuthMiddleware(
        session_factory=session_factory,
        redis_client=redis_client,
    )
    api_key_manager = APIKeyManager(
        session_factory=session_factory,
        redis_client=redis_client,
    )
    query_cache = QueryCache(redis_client=redis_client)

    return create_app(
        query_handler=query_handler,
        auth_middleware=auth_middleware,
        api_key_manager=api_key_manager,
        session_factory=session_factory,
        es_client=es_client,
        qdrant_client=qdrant_client,
        redis_client=redis_client,
        query_cache=query_cache,
    )


def main() -> None:
    """Process entry: build the wired app and start uvicorn on 0.0.0.0:8000.

    Exits with code 1 if a required env var is missing.
    """
    try:
        app = build_app()
    except KeyError as exc:
        print(f"ERROR: Required environment variable not set: {exc}", file=sys.stderr)
        sys.exit(1)

    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")


if __name__ == "__main__":
    main()
