#!/usr/bin/env python3
"""Example: Query Logging (Feature #24).

Demonstrates structured JSON logging for the query service.
Each log_query call produces one JSON line to stdout.
"""

from src.query.query_logger import QueryLogger


def main():
    logger = QueryLogger()

    # Simulate logging two queries
    logger.log_query(
        query="how to configure spring http client timeout",
        query_type="nl",
        api_key_id="ak_demo_001",
        result_count=3,
        retrieval_ms=45.2,
        rerank_ms=12.8,
        total_ms=62.1,
    )

    logger.log_query(
        query="UserService.getById",
        query_type="symbol",
        api_key_id="ak_demo_002",
        result_count=1,
        retrieval_ms=8.5,
        rerank_ms=3.2,
        total_ms=14.7,
    )

    print("\n--- Two JSON log entries printed above ---")


if __name__ == "__main__":
    main()
