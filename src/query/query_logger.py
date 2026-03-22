"""Query Logging — structured JSON log entries for each query (Feature #24, FR-022).

Writes a structured JSON log entry to stdout for every processed query.
Logging failures are non-fatal and never block query responses.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone


class QueryLogger:
    """Structured JSON logger for query service telemetry."""

    def __init__(self, logger_name: str = "query_logger") -> None:
        self._logger = logging.getLogger(logger_name)
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.INFO)
            # Raw message format — we produce the JSON ourselves
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)
        self._logger.setLevel(logging.INFO)

    def log_query(
        self,
        query: str | None,
        query_type: str | None,
        api_key_id: str | None,
        result_count: int | None,
        retrieval_ms: float | None,
        rerank_ms: float | None,
        total_ms: float | None,
    ) -> None:
        """Write a structured JSON log entry to stdout. Non-fatal."""
        try:
            entry = {
                "query": query,
                "query_type": query_type,
                "api_key_id": api_key_id,
                "result_count": result_count,
                "retrieval_ms": retrieval_ms,
                "rerank_ms": rerank_ms,
                "total_ms": total_ms,
                "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            }
            self._logger.info(json.dumps(entry))
        except Exception:
            pass
