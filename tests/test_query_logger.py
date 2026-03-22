"""Tests for Feature #24 — Query Logging (structured JSON to stdout)."""

import io
import json
import logging
from datetime import datetime
from unittest.mock import patch

import pytest

from src.query.query_logger import QueryLogger


def _make_logger_with_capture():
    """Create a QueryLogger and a StringIO buffer capturing its output."""
    buf = io.StringIO()
    # Use unique logger names to avoid handler accumulation across tests
    import uuid
    name = f"test_query_logger_{uuid.uuid4().hex[:8]}"
    logger = QueryLogger(logger_name=name)
    # Add our capture handler
    handler = logging.StreamHandler(buf)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger._logger.addHandler(handler)
    return logger, buf


def _parse_entries(buf):
    """Parse JSON entries from captured buffer."""
    entries = []
    for line in buf.getvalue().strip().splitlines():
        try:
            parsed = json.loads(line)
            if "query" in parsed:
                entries.append(parsed)
        except json.JSONDecodeError:
            continue
    return entries


class TestQueryLoggerHappyPath:
    """Happy-path tests for QueryLogger.log_query."""

    def test_log_query_produces_json_with_all_required_fields(self):
        """T1: log_query produces JSON containing all 8 required fields."""
        logger, buf = _make_logger_with_capture()
        logger.log_query(
            query="find auth",
            query_type="nl",
            api_key_id="key-1",
            result_count=5,
            retrieval_ms=12.3,
            rerank_ms=4.5,
            total_ms=18.0,
        )

        entries = _parse_entries(buf)
        assert len(entries) == 1
        entry = entries[0]
        assert entry["query"] == "find auth"
        assert entry["query_type"] == "nl"
        assert entry["api_key_id"] == "key-1"
        assert entry["result_count"] == 5
        assert entry["retrieval_ms"] == 12.3
        assert entry["rerank_ms"] == 4.5
        assert entry["total_ms"] == 18.0
        assert "timestamp" in entry

    def test_timestamp_is_iso_8601(self):
        """T2: timestamp field is valid ISO 8601 format."""
        logger, buf = _make_logger_with_capture()
        logger.log_query("test", "nl", None, 0, 0.0, 0.0, 0.0)

        entries = _parse_entries(buf)
        assert len(entries) == 1
        ts = entries[0]["timestamp"]
        # Should parse without error; ends with Z for UTC
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        assert dt.year >= 2026

    def test_multiple_queries_produce_multiple_log_entries(self):
        """T3: calling log_query twice produces two separate JSON entries."""
        logger, buf = _make_logger_with_capture()
        logger.log_query("q1", "nl", "k1", 1, 1.0, 1.0, 2.0)
        logger.log_query("q2", "symbol", "k2", 2, 2.0, 2.0, 4.0)

        entries = _parse_entries(buf)
        assert len(entries) == 2
        assert entries[0]["query"] == "q1"
        assert entries[1]["query"] == "q2"


class TestQueryLoggerErrorHandling:
    """Error-handling tests — logging must be non-fatal."""

    def test_io_failure_does_not_raise(self):
        """T4: I/O failure in logger does not propagate exception."""
        logger, _ = _make_logger_with_capture()
        # Patch the internal logger's info method to raise IOError
        with patch.object(logger._logger, "info", side_effect=IOError("disk full")):
            # Must not raise
            logger.log_query("test", "nl", "k1", 1, 1.0, 1.0, 2.0)

    def test_none_and_empty_values_handled_gracefully(self):
        """T5: None/empty values do not cause exceptions."""
        logger, buf = _make_logger_with_capture()
        # Should not raise
        logger.log_query(
            query=None,
            query_type=None,
            api_key_id=None,
            result_count=None,
            retrieval_ms=None,
            rerank_ms=None,
            total_ms=None,
        )

        entries = _parse_entries(buf)
        assert len(entries) == 1
        assert entries[0]["query"] is None
        assert entries[0]["api_key_id"] is None


# [unit] T-init: Re-creating QueryLogger with same name reuses existing handler
def test_existing_handler_not_duplicated():
    """QueryLogger with same logger name does not add duplicate handlers."""
    import uuid
    name = f"test_dup_{uuid.uuid4().hex[:8]}"
    logger1 = QueryLogger(logger_name=name)
    handler_count_1 = len(logger1._logger.handlers)
    logger2 = QueryLogger(logger_name=name)
    handler_count_2 = len(logger2._logger.handlers)
    assert handler_count_2 == handler_count_1, "Duplicate handler added"


class TestQueryLoggerBoundary:
    """Boundary tests."""

    def test_very_long_query_string(self):
        """T6: very long query string (10000 chars) logged without error."""
        logger, buf = _make_logger_with_capture()
        long_query = "x" * 10000
        logger.log_query(long_query, "nl", "k1", 1, 1.0, 1.0, 2.0)

        entries = _parse_entries(buf)
        assert len(entries) == 1
        assert len(entries[0]["query"]) == 10000

    def test_zero_values_for_timing_fields(self):
        """T7: zero values for all timing fields and result_count."""
        logger, buf = _make_logger_with_capture()
        logger.log_query("q", "nl", "k1", 0, 0.0, 0.0, 0.0)

        entries = _parse_entries(buf)
        assert len(entries) == 1
        assert entries[0]["result_count"] == 0
        assert entries[0]["retrieval_ms"] == 0.0
        assert entries[0]["rerank_ms"] == 0.0
        assert entries[0]["total_ms"] == 0.0
