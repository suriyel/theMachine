"""Tests for NFR-007: Single-Node Failure Tolerance verification components.

Components: FailureToleranceReportAnalyzer, FailureToleranceVerificationResult.

# [no integration test] — pure function, no external service dependencies
# All components operate on in-memory data or local JSON files via tmp_path.
# Security: N/A — internal utility with no user-facing input
"""

import json

import pytest

from src.loadtest.failure_tolerance_verification_result import FailureToleranceVerificationResult
from src.loadtest.failure_tolerance_report_analyzer import FailureToleranceReportAnalyzer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_json(tmp_path, data: dict, filename: str = "report.json") -> str:
    """Write a JSON failure-tolerance report and return its path."""
    path = tmp_path / filename
    path.write_text(json.dumps(data))
    return str(path)


def _valid_stats(
    total_requests: int = 100,
    failed_requests: int = 0,
    nodes_killed: int = 1,
    nodes_initial: int = 3,
) -> dict:
    """Return a valid stats dict."""
    return {
        "total_requests": total_requests,
        "failed_requests": failed_requests,
        "nodes_killed": nodes_killed,
        "nodes_initial": nodes_initial,
    }


# ---------------------------------------------------------------------------
# T01: Happy path — analyze_from_stats, all conditions pass
# [unit]
# ---------------------------------------------------------------------------


class TestAnalyzeFromStatsHappyPath:
    def test_passes_when_all_conditions_met(self):
        """T01: nodes_killed=1, nodes_initial=3, failed_requests=0, total=100 → PASS."""
        analyzer = FailureToleranceReportAnalyzer()
        result = analyzer.analyze_from_stats(_valid_stats())

        assert result.passed is True
        assert result.failed_requests == 0
        assert result.nodes_killed == 1
        assert result.total_requests == 100
        assert result.nodes_initial == 3


# ---------------------------------------------------------------------------
# T02: Happy path — analyze (JSON file), all conditions pass
# [unit]
# ---------------------------------------------------------------------------


class TestAnalyzeJsonHappyPath:
    def test_passes_reading_from_json_file(self, tmp_path):
        """T02: JSON file with valid data → parsed correctly, passed=True."""
        data = _valid_stats(total_requests=200, failed_requests=0, nodes_killed=1, nodes_initial=2)
        path = _write_json(tmp_path, data)
        analyzer = FailureToleranceReportAnalyzer()
        result = analyzer.analyze(path)

        assert result.passed is True
        assert result.total_requests == 200
        assert result.failed_requests == 0
        assert result.nodes_killed == 1
        assert result.nodes_initial == 2


# ---------------------------------------------------------------------------
# T03: Happy path — max_allowed_failures=2, failed_requests=2 (inclusive boundary)
# [unit]
# ---------------------------------------------------------------------------


class TestMaxAllowedFailuresInclusive:
    def test_passes_at_exact_max_allowed_failures(self):
        """T03: failed_requests == max_allowed_failures → cond3=True → PASS."""
        analyzer = FailureToleranceReportAnalyzer()
        result = analyzer.analyze_from_stats(
            _valid_stats(failed_requests=2),
            max_allowed_failures=2,
        )

        assert result.passed is True
        assert result.failed_requests == 2
        assert result.max_allowed_failures == 2


# ---------------------------------------------------------------------------
# T04: Error — FileNotFoundError on nonexistent path
# [unit]
# ---------------------------------------------------------------------------


class TestFileNotFound:
    def test_raises_file_not_found_for_missing_path(self):
        """T04: nonexistent json_path → FileNotFoundError."""
        analyzer = FailureToleranceReportAnalyzer()
        with pytest.raises(FileNotFoundError):
            analyzer.analyze("/nonexistent/path/report.json")


# ---------------------------------------------------------------------------
# T05: Error — ValueError on malformed JSON
# [unit]
# ---------------------------------------------------------------------------


class TestMalformedJson:
    def test_raises_value_error_on_malformed_json(self, tmp_path):
        """T05: file with invalid JSON content → ValueError 'malformed JSON'."""
        path = tmp_path / "bad.json"
        path.write_text("{bad json!")
        analyzer = FailureToleranceReportAnalyzer()
        with pytest.raises(ValueError, match="malformed JSON"):
            analyzer.analyze(str(path))


# ---------------------------------------------------------------------------
# T06: Error — ValueError on missing key in JSON file
# [unit]
# ---------------------------------------------------------------------------


class TestMissingKeyInJson:
    def test_raises_value_error_when_nodes_killed_absent(self, tmp_path):
        """T06: JSON missing 'nodes_killed' → ValueError 'missing key'."""
        data = {"total_requests": 100, "failed_requests": 0, "nodes_initial": 3}
        path = _write_json(tmp_path, data)
        analyzer = FailureToleranceReportAnalyzer()
        with pytest.raises(ValueError, match="missing key"):
            analyzer.analyze(path)


# ---------------------------------------------------------------------------
# T07: Error — ValueError on missing key in stats dict
# [unit]
# ---------------------------------------------------------------------------


class TestMissingKeyInStats:
    def test_raises_value_error_when_failed_requests_absent(self):
        """T07: stats missing 'failed_requests' → ValueError 'stats must contain'."""
        analyzer = FailureToleranceReportAnalyzer()
        stats = {"total_requests": 100, "nodes_killed": 1, "nodes_initial": 3}
        with pytest.raises(ValueError, match="stats must contain"):
            analyzer.analyze_from_stats(stats)


# ---------------------------------------------------------------------------
# T08: Error — ValueError on negative field value
# [unit]
# ---------------------------------------------------------------------------


class TestNegativeFieldValue:
    def test_raises_value_error_on_negative_total_requests(self):
        """T08: total_requests=-1 → ValueError 'non-negative'."""
        analyzer = FailureToleranceReportAnalyzer()
        stats = _valid_stats(total_requests=-1)
        with pytest.raises(ValueError, match="non-negative"):
            analyzer.analyze_from_stats(stats)


# ---------------------------------------------------------------------------
# T09: Boundary — nodes_killed=0 → cond1=False → FAIL
# [unit]
# ---------------------------------------------------------------------------


class TestNoNodeKilled:
    def test_fails_when_nodes_killed_is_zero(self):
        """T09: nodes_killed=0 → cond1=False → passed=False."""
        analyzer = FailureToleranceReportAnalyzer()
        result = analyzer.analyze_from_stats(_valid_stats(nodes_killed=0))

        assert result.passed is False
        assert result.nodes_killed == 0


# ---------------------------------------------------------------------------
# T10: Boundary — nodes_killed == nodes_initial → cond2=False → FAIL
# [unit]
# ---------------------------------------------------------------------------


class TestAllNodesKilled:
    def test_fails_when_all_nodes_killed(self):
        """T10: nodes_killed=3, nodes_initial=3 → cond2=False → passed=False."""
        analyzer = FailureToleranceReportAnalyzer()
        result = analyzer.analyze_from_stats(
            _valid_stats(nodes_killed=3, nodes_initial=3)
        )

        assert result.passed is False
        assert result.nodes_killed == 3
        assert result.nodes_initial == 3


# ---------------------------------------------------------------------------
# T11: Boundary — total_requests=0 → cond4=False → FAIL
# [unit]
# ---------------------------------------------------------------------------


class TestZeroTotalRequests:
    def test_fails_when_no_requests_made(self):
        """T11: total_requests=0 → cond4=False → passed=False."""
        analyzer = FailureToleranceReportAnalyzer()
        result = analyzer.analyze_from_stats(_valid_stats(total_requests=0))

        assert result.passed is False
        assert result.total_requests == 0


# ---------------------------------------------------------------------------
# T12: Boundary — failed_requests=1, max_allowed_failures=0 → cond3=False → FAIL
# [unit]
# ---------------------------------------------------------------------------


class TestFailureExceedsThreshold:
    def test_fails_when_failure_count_exceeds_max(self):
        """T12: failed_requests=1, max_allowed_failures=0 → cond3=False → FAIL."""
        analyzer = FailureToleranceReportAnalyzer()
        result = analyzer.analyze_from_stats(_valid_stats(failed_requests=1))

        assert result.passed is False
        assert result.failed_requests == 1
        assert result.max_allowed_failures == 0


# ---------------------------------------------------------------------------
# T13: Boundary — minimum valid cluster (nodes_killed=1, nodes_initial=2) → PASS
# [unit]
# ---------------------------------------------------------------------------


class TestMinimumValidCluster:
    def test_passes_with_minimum_cluster_configuration(self):
        """T13: nodes_killed=1, nodes_initial=2 → smallest passing cluster → PASS."""
        analyzer = FailureToleranceReportAnalyzer()
        result = analyzer.analyze_from_stats(
            _valid_stats(total_requests=50, nodes_killed=1, nodes_initial=2)
        )

        assert result.passed is True
        assert result.nodes_killed == 1
        assert result.nodes_initial == 2


# ---------------------------------------------------------------------------
# T14: Happy path — summary() contains required fields on PASS
# [unit]
# ---------------------------------------------------------------------------


class TestSummaryPass:
    def test_summary_contains_nfr_label_and_pass_verdict(self):
        """T14: passed=True → summary() contains 'NFR-008', 'PASS', node and failure counts."""
        result = FailureToleranceVerificationResult(
            passed=True,
            total_requests=100,
            failed_requests=0,
            nodes_killed=1,
            nodes_initial=3,
            max_allowed_failures=0,
        )
        s = result.summary()

        assert "NFR-008" in s
        assert "PASS" in s
        assert "1" in s  # nodes_killed
        assert "0" in s  # failed_requests


# ---------------------------------------------------------------------------
# T15: Error path in summary — summary() contains FAIL verdict
# [unit]
# ---------------------------------------------------------------------------


class TestSummaryFail:
    def test_summary_contains_fail_verdict(self):
        """T15: passed=False → summary() contains 'FAIL'."""
        result = FailureToleranceVerificationResult(
            passed=False,
            total_requests=100,
            failed_requests=5,
            nodes_killed=0,
            nodes_initial=3,
            max_allowed_failures=0,
        )
        s = result.summary()

        assert "NFR-008" in s
        assert "FAIL" in s
        assert "5" in s  # failed_requests


# ---------------------------------------------------------------------------
# T16: Boundary — nodes_killed > nodes_initial → cond2=False → FAIL
# [unit]
# ---------------------------------------------------------------------------


class TestMoreKilledThanInitial:
    def test_fails_when_nodes_killed_exceeds_nodes_initial(self):
        """T16: nodes_killed=5, nodes_initial=3 → cond2=False → passed=False."""
        analyzer = FailureToleranceReportAnalyzer()
        result = analyzer.analyze_from_stats(
            _valid_stats(nodes_killed=5, nodes_initial=3)
        )

        assert result.passed is False
        assert result.nodes_killed == 5
        assert result.nodes_initial == 3


# ---------------------------------------------------------------------------
# [integration] Real test — JSON file I/O roundtrip
# ---------------------------------------------------------------------------


@pytest.mark.real
class TestRealFailureToleranceReportFeature32:
    """Real test: exercises actual JSON file I/O for feature #32."""

    def test_real_json_roundtrip_analyze_feature_32(self, tmp_path):
        """Real test: write a JSON failure-tolerance report, parse it, verify metrics."""
        data = {
            "total_requests": 500,
            "failed_requests": 0,
            "nodes_killed": 1,
            "nodes_initial": 3,
        }
        path = _write_json(tmp_path, data)
        analyzer = FailureToleranceReportAnalyzer()
        result = analyzer.analyze(path, max_allowed_failures=0)

        assert result.passed is True
        assert result.total_requests == 500
        assert result.failed_requests == 0
        assert result.nodes_killed == 1
        assert result.nodes_initial == 3
        assert result.max_allowed_failures == 0
