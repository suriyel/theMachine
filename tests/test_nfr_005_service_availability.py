"""Tests for NFR-005: Service Availability 99.9% verification components.

Components: AvailabilityReportAnalyzer, AvailabilityVerificationResult.

# [no integration test] — pure function, no external I/O
# All components operate on in-memory data or local JSON files via tmp_path.
# Security: N/A — internal utility with no user-facing input
"""

import json

import pytest

from src.loadtest.availability_verification_result import AvailabilityVerificationResult
from src.loadtest.availability_report_analyzer import AvailabilityReportAnalyzer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_list(n_success: int, n_failure: int) -> list[dict]:
    """Generate a list of check dicts with the given success/failure counts."""
    checks = [{"status": "success"} for _ in range(n_success)]
    checks.extend({"status": "failure"} for _ in range(n_failure))
    return checks


def _write_json(tmp_path, checks: list[dict], filename: str = "uptime.json") -> str:
    """Write a JSON uptime report and return its path."""
    path = tmp_path / filename
    data = {"checks": checks}
    path.write_text(json.dumps(data))
    return str(path)


# ---------------------------------------------------------------------------
# [unit] Happy Path — analyze (JSON file)
# ---------------------------------------------------------------------------


class TestAnalyzeHappyPath:
    """Tests A-F from Test Inventory: happy path pass/fail scenarios."""

    # Test A: 1000 checks all success -> passed=True
    def test_passes_all_success(self, tmp_path):
        checks = _check_list(1000, 0)
        path = _write_json(tmp_path, checks)
        analyzer = AvailabilityReportAnalyzer()
        result = analyzer.analyze(path, min_uptime_ratio=0.999)

        assert result.passed is True
        assert result.total_checks == 1000
        assert result.successful_checks == 1000
        assert result.uptime_ratio == 1.0

    # Test B: 10000 checks, 9995 success, 5 failure (99.95%) -> passed=True
    def test_passes_above_threshold(self, tmp_path):
        checks = _check_list(9995, 5)
        path = _write_json(tmp_path, checks)
        analyzer = AvailabilityReportAnalyzer()
        result = analyzer.analyze(path, min_uptime_ratio=0.999)

        assert result.passed is True
        assert result.total_checks == 10000
        assert result.successful_checks == 9995
        assert result.uptime_ratio == pytest.approx(0.9995)

    # Test C: 1000 checks, 998 success, 2 failure (99.8%) -> passed=False
    def test_fails_below_threshold(self, tmp_path):
        checks = _check_list(998, 2)
        path = _write_json(tmp_path, checks)
        analyzer = AvailabilityReportAnalyzer()
        result = analyzer.analyze(path, min_uptime_ratio=0.999)

        assert result.passed is False
        assert result.total_checks == 1000
        assert result.successful_checks == 998
        assert result.uptime_ratio == pytest.approx(0.998)

    # Test D: 5 checks all success, min_total_checks=100 -> passed=False
    def test_fails_insufficient_checks(self, tmp_path):
        checks = _check_list(5, 0)
        path = _write_json(tmp_path, checks)
        analyzer = AvailabilityReportAnalyzer()
        result = analyzer.analyze(path, min_uptime_ratio=0.999, min_total_checks=100)

        assert result.passed is False
        assert result.total_checks == 5
        assert result.successful_checks == 5
        assert result.uptime_ratio == 1.0

    # Test E: 100 checks all success, min_total_checks=100 -> passed=True
    def test_passes_at_exact_min_total_checks(self, tmp_path):
        checks = _check_list(100, 0)
        path = _write_json(tmp_path, checks)
        analyzer = AvailabilityReportAnalyzer()
        result = analyzer.analyze(path, min_uptime_ratio=0.999, min_total_checks=100)

        assert result.passed is True
        assert result.total_checks == 100
        assert result.successful_checks == 100

    # Test F: analyze_from_stats with 43200 total, 43157 success -> passed=True
    def test_stats_passes_above_threshold(self):
        analyzer = AvailabilityReportAnalyzer()
        result = analyzer.analyze_from_stats(
            {"total_checks": 43200, "successful_checks": 43157},
            min_uptime_ratio=0.999,
        )

        assert result.passed is True
        assert result.total_checks == 43200
        assert result.successful_checks == 43157
        assert result.uptime_ratio == pytest.approx(43157 / 43200)


# ---------------------------------------------------------------------------
# [unit] Boundary Tests
# ---------------------------------------------------------------------------


class TestAnalyzeBoundary:
    """Tests G-K from Test Inventory: boundary conditions."""

    # Test G: 1000 checks, 999 success (ratio=0.999 exactly) -> passed=True (>=)
    def test_passes_at_exact_threshold(self, tmp_path):
        checks = _check_list(999, 1)
        path = _write_json(tmp_path, checks)
        analyzer = AvailabilityReportAnalyzer()
        result = analyzer.analyze(path, min_uptime_ratio=0.999)

        assert result.passed is True
        assert result.total_checks == 1000
        assert result.successful_checks == 999
        assert result.uptime_ratio == pytest.approx(0.999)

    # Test H: 10000 checks, 9989 success (ratio=0.9989) -> passed=False
    def test_fails_just_below_threshold(self, tmp_path):
        checks = _check_list(9989, 11)
        path = _write_json(tmp_path, checks)
        analyzer = AvailabilityReportAnalyzer()
        result = analyzer.analyze(path, min_uptime_ratio=0.999)

        assert result.passed is False
        assert result.total_checks == 10000
        assert result.successful_checks == 9989
        assert result.uptime_ratio == pytest.approx(0.9989)

    # Test I: stats with total_checks=0 -> passed=False, no ZeroDivisionError
    def test_zero_total_checks_no_division_error(self):
        analyzer = AvailabilityReportAnalyzer()
        result = analyzer.analyze_from_stats(
            {"total_checks": 0, "successful_checks": 0},
            min_uptime_ratio=0.999, min_total_checks=1,
        )

        assert result.passed is False
        assert result.total_checks == 0
        assert result.successful_checks == 0
        assert result.uptime_ratio == 0.0

    # Test J: 1 check success -> passed=True (single-element list)
    def test_single_check_success(self, tmp_path):
        checks = _check_list(1, 0)
        path = _write_json(tmp_path, checks)
        analyzer = AvailabilityReportAnalyzer()
        result = analyzer.analyze(path, min_uptime_ratio=0.999)

        assert result.passed is True
        assert result.total_checks == 1
        assert result.successful_checks == 1
        assert result.uptime_ratio == 1.0

    # Test K: 1 check failure -> passed=False
    def test_single_check_failure(self, tmp_path):
        checks = _check_list(0, 1)
        path = _write_json(tmp_path, checks)
        analyzer = AvailabilityReportAnalyzer()
        result = analyzer.analyze(path, min_uptime_ratio=0.999)

        assert result.passed is False
        assert result.total_checks == 1
        assert result.successful_checks == 0
        assert result.uptime_ratio == 0.0


# ---------------------------------------------------------------------------
# [unit] Error Handling Tests
# ---------------------------------------------------------------------------


class TestAnalyzeErrors:
    """Tests L-Q from Test Inventory: error handling."""

    # Test L: nonexistent file -> FileNotFoundError
    def test_file_not_found(self):
        analyzer = AvailabilityReportAnalyzer()
        with pytest.raises(FileNotFoundError):
            analyzer.analyze("/nonexistent/report.json")

    # Test M: invalid JSON -> ValueError
    def test_malformed_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{not valid json!!!")
        analyzer = AvailabilityReportAnalyzer()
        with pytest.raises(ValueError, match="malformed JSON"):
            analyzer.analyze(str(path))

    # Test N: missing 'checks' key -> ValueError
    def test_missing_checks_key(self, tmp_path):
        path = tmp_path / "no_checks.json"
        path.write_text(json.dumps({"other": []}))
        analyzer = AvailabilityReportAnalyzer()
        with pytest.raises(ValueError, match="checks"):
            analyzer.analyze(str(path))

    # Test O: empty checks list -> ValueError
    def test_empty_checks_list(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text(json.dumps({"checks": []}))
        analyzer = AvailabilityReportAnalyzer()
        with pytest.raises(ValueError, match="empty"):
            analyzer.analyze(str(path))

    # Test P: stats missing keys -> ValueError
    def test_stats_missing_keys(self):
        analyzer = AvailabilityReportAnalyzer()
        with pytest.raises(ValueError, match="total_checks"):
            analyzer.analyze_from_stats({"successful_checks": 10})

    # Test Q: stats with negative total_checks -> ValueError
    def test_stats_negative_count(self):
        analyzer = AvailabilityReportAnalyzer()
        with pytest.raises(ValueError, match="non-negative"):
            analyzer.analyze_from_stats({"total_checks": -1, "successful_checks": 0})


# ---------------------------------------------------------------------------
# [unit] Summary Tests
# ---------------------------------------------------------------------------


class TestVerificationResultSummary:
    """Tests R-S from Test Inventory: summary() output."""

    # Test R: passed=True -> summary contains "NFR-007", "PASS", metrics
    def test_summary_pass_format(self):
        result = AvailabilityVerificationResult(
            passed=True,
            total_checks=1000,
            successful_checks=1000,
            uptime_ratio=1.0,
            min_uptime_ratio=0.999,
            min_total_checks=1,
        )
        s = result.summary()
        assert "NFR-007" in s
        assert "PASS" in s
        assert "1000" in s
        assert "0.999" in s

    # Test S: passed=False -> summary contains "FAIL", thresholds
    def test_summary_fail_format(self):
        result = AvailabilityVerificationResult(
            passed=False,
            total_checks=1000,
            successful_checks=998,
            uptime_ratio=0.998,
            min_uptime_ratio=0.999,
            min_total_checks=1,
        )
        s = result.summary()
        assert "NFR-007" in s
        assert "FAIL" in s
        assert "998" in s
        assert "0.999" in s


# ---------------------------------------------------------------------------
# [integration] Real Test — JSON file I/O roundtrip
# ---------------------------------------------------------------------------


@pytest.mark.real
class TestRealAvailabilityReportFeature30:
    """Real test: exercises actual JSON file I/O for feature #30."""

    def test_real_json_roundtrip_analyze_feature_30(self, tmp_path):
        """Real test: write a JSON uptime report, parse it, verify availability metrics."""
        checks = _check_list(10000, 0)
        path = _write_json(tmp_path, checks)
        analyzer = AvailabilityReportAnalyzer()
        result = analyzer.analyze(path, min_uptime_ratio=0.999, min_total_checks=100)

        assert result.passed is True
        assert result.total_checks == 10000
        assert result.successful_checks == 10000
        assert result.uptime_ratio == 1.0
        assert result.min_uptime_ratio == 0.999
        assert result.min_total_checks == 100
