"""Tests for NFR-002: Query Throughput >= 1000 QPS verification components.

Components: ThroughputReportAnalyzer, ThroughputVerificationResult.

# [no integration test] — pure function, no external I/O
# All components operate on in-memory data or local CSV files via tmp_path.
# Security: N/A — internal utility with no user-facing input
"""

import csv

import pytest

from src.loadtest.throughput_verification_result import ThroughputVerificationResult
from src.loadtest.throughput_report_analyzer import ThroughputReportAnalyzer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LOCUST_CSV_HEADERS = [
    "Type", "Name", "Request Count", "Failure Count", "Median Response Time",
    "Average Response Time", "Min Response Time", "Max Response Time",
    "Average Content Size", "Requests/s", "Failures/s",
    "50%", "66%", "75%", "80%", "90%", "95%", "98%", "99%", "99.9%", "99.99%", "100%",
]


def _write_csv(tmp_path, rows: list[dict], filename: str = "stats.csv") -> str:
    """Write a Locust-style stats CSV and return its path."""
    path = tmp_path / filename
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=LOCUST_CSV_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return str(path)


def _agg_row(
    requests_per_sec: float = 1500.0,
    total_requests: int = 450000,
    failure_count: int = 100,
) -> dict:
    """Build an Aggregated row dict for Locust CSV with throughput fields."""
    return {
        "Type": "",
        "Name": "Aggregated",
        "Request Count": str(total_requests),
        "Failure Count": str(failure_count),
        "Median Response Time": "200",
        "Average Response Time": "250",
        "Min Response Time": "10",
        "Max Response Time": "5000",
        "Average Content Size": "1024",
        "Requests/s": str(requests_per_sec),
        "Failures/s": "0.5",
        "50%": "200",
        "66%": "300",
        "75%": "350",
        "80%": "400",
        "90%": "450",
        "95%": "487",
        "98%": "550",
        "99%": "650",
        "99.9%": "900",
        "99.99%": "980",
        "100%": "1000",
    }


def _endpoint_row(name: str = "POST /api/v1/query") -> dict:
    """Build a non-aggregated endpoint row."""
    return {
        "Type": "POST",
        "Name": name,
        "Request Count": "5000",
        "Failure Count": "10",
        "Median Response Time": "200",
        "Average Response Time": "250",
        "Min Response Time": "10",
        "Max Response Time": "5000",
        "Average Content Size": "1024",
        "Requests/s": "750",
        "Failures/s": "0.3",
        "50%": "200",
        "66%": "300",
        "75%": "350",
        "80%": "400",
        "90%": "450",
        "95%": "487",
        "98%": "550",
        "99%": "650",
        "99.9%": "900",
        "99.99%": "980",
        "100%": "1000",
    }


# ---------------------------------------------------------------------------
# Test A: Happy path — CSV with high QPS, low error rate → PASS
# [unit] — uses tmp_path CSV
# ---------------------------------------------------------------------------

def test_analyze_csv_high_qps_passes(tmp_path):
    """QPS=1500, error_rate~0.000222 → passed=True."""
    csv_path = _write_csv(tmp_path, [_endpoint_row(), _agg_row(
        requests_per_sec=1500.0, total_requests=450000, failure_count=100,
    )])
    analyzer = ThroughputReportAnalyzer()
    result = analyzer.analyze(csv_path)

    assert result.passed is True
    assert result.qps == 1500.0
    assert result.total_requests == 450000
    assert abs(result.error_rate - 100 / 450000) < 1e-6


# ---------------------------------------------------------------------------
# Test B: Happy path — CSV with low QPS → FAIL
# [unit]
# ---------------------------------------------------------------------------

def test_analyze_csv_low_qps_fails(tmp_path):
    """QPS=800, below 1000 threshold → passed=False."""
    csv_path = _write_csv(tmp_path, [_agg_row(requests_per_sec=800.0)])
    analyzer = ThroughputReportAnalyzer()
    result = analyzer.analyze(csv_path)

    assert result.passed is False
    assert result.qps == 800.0


# ---------------------------------------------------------------------------
# Test C: Happy path — High QPS but high error rate → FAIL
# [unit]
# ---------------------------------------------------------------------------

def test_analyze_csv_high_qps_high_error_rate_fails(tmp_path):
    """QPS=1200 passes QPS check, but error_rate=2% fails error check."""
    csv_path = _write_csv(tmp_path, [_agg_row(
        requests_per_sec=1200.0, total_requests=10000, failure_count=200,
    )])
    analyzer = ThroughputReportAnalyzer()
    result = analyzer.analyze(csv_path)

    assert result.passed is False
    assert result.qps == 1200.0
    assert abs(result.error_rate - 0.02) < 1e-6


# ---------------------------------------------------------------------------
# Test D: Boundary — QPS exactly at threshold → PASS (>=)
# [unit]
# ---------------------------------------------------------------------------

def test_analyze_csv_qps_exactly_at_threshold(tmp_path):
    """QPS=1000.0 exactly, failure_count=0 → passed=True (>= threshold)."""
    csv_path = _write_csv(tmp_path, [_agg_row(
        requests_per_sec=1000.0, total_requests=300000, failure_count=0,
    )])
    analyzer = ThroughputReportAnalyzer()
    result = analyzer.analyze(csv_path)

    assert result.passed is True
    assert result.qps == 1000.0
    assert result.error_rate == 0.0


# ---------------------------------------------------------------------------
# Test E: Boundary — error_rate exactly at threshold → FAIL (strict <)
# [unit]
# ---------------------------------------------------------------------------

def test_analyze_csv_error_rate_exactly_at_threshold(tmp_path):
    """error_rate=0.01 exactly (100/10000), strict < means FAIL."""
    csv_path = _write_csv(tmp_path, [_agg_row(
        requests_per_sec=1500.0, total_requests=10000, failure_count=100,
    )])
    analyzer = ThroughputReportAnalyzer()
    result = analyzer.analyze(csv_path)

    assert result.passed is False
    assert abs(result.error_rate - 0.01) < 1e-9


# ---------------------------------------------------------------------------
# Test F: Boundary — zero total_requests → no ZeroDivisionError
# [unit]
# ---------------------------------------------------------------------------

def test_analyze_csv_zero_requests_no_division_error(tmp_path):
    """total_requests=0 should not raise ZeroDivisionError, error_rate=0.0."""
    csv_path = _write_csv(tmp_path, [_agg_row(
        requests_per_sec=0.0, total_requests=0, failure_count=0,
    )])
    analyzer = ThroughputReportAnalyzer()
    result = analyzer.analyze(csv_path)

    assert result.error_rate == 0.0
    assert result.total_requests == 0


# ---------------------------------------------------------------------------
# Test G: Error — non-existent CSV path → FileNotFoundError
# [unit]
# ---------------------------------------------------------------------------

def test_analyze_csv_nonexistent_raises_file_not_found():
    """Non-existent path raises FileNotFoundError."""
    analyzer = ThroughputReportAnalyzer()
    with pytest.raises(FileNotFoundError):
        analyzer.analyze("/nonexistent/path.csv")


# ---------------------------------------------------------------------------
# Test H: Error — CSV with no Aggregated row → ValueError
# [unit]
# ---------------------------------------------------------------------------

def test_analyze_csv_no_aggregated_row_raises_value_error(tmp_path):
    """CSV with only endpoint rows, no Aggregated → ValueError."""
    csv_path = _write_csv(tmp_path, [_endpoint_row("POST /api/v1/query")])
    analyzer = ThroughputReportAnalyzer()

    with pytest.raises(ValueError, match="no aggregated stats row"):
        analyzer.analyze(csv_path)


# ---------------------------------------------------------------------------
# Test I: Error — CSV with missing Requests/s column → ValueError
# [unit]
# ---------------------------------------------------------------------------

def test_analyze_csv_missing_requests_per_sec_column_raises(tmp_path):
    """Aggregated row present but missing 'Requests/s' → ValueError."""
    # Write CSV without the Requests/s column
    headers_without_rps = [h for h in LOCUST_CSV_HEADERS if h != "Requests/s"]
    path = tmp_path / "bad.csv"
    row = _agg_row()
    del row["Requests/s"]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers_without_rps)
        writer.writeheader()
        writer.writerow(row)

    analyzer = ThroughputReportAnalyzer()
    with pytest.raises(ValueError, match="missing column"):
        analyzer.analyze(str(path))


# ---------------------------------------------------------------------------
# Test J: Happy path — analyze_from_stats with 2 entries → PASS
# [unit]
# ---------------------------------------------------------------------------

def test_analyze_from_stats_aggregates_qps(tmp_path):
    """Two entries summing to 1100 QPS with low error rate → passed=True."""
    stats = [
        {"qps": 600.0, "total_requests": 180000, "failure_count": 50},
        {"qps": 500.0, "total_requests": 150000, "failure_count": 30},
    ]
    analyzer = ThroughputReportAnalyzer()
    result = analyzer.analyze_from_stats(stats)

    assert result.passed is True
    assert result.qps == 1100.0
    assert result.total_requests == 330000
    assert abs(result.error_rate - 80 / 330000) < 1e-6


# ---------------------------------------------------------------------------
# Test K: Error — analyze_from_stats with empty list → ValueError
# [unit]
# ---------------------------------------------------------------------------

def test_analyze_from_stats_empty_raises_value_error():
    """Empty stats list raises ValueError."""
    analyzer = ThroughputReportAnalyzer()
    with pytest.raises(ValueError, match="stats list must not be empty"):
        analyzer.analyze_from_stats([])


# ---------------------------------------------------------------------------
# Test L: Happy path — summary() on passing result
# [unit]
# ---------------------------------------------------------------------------

def test_summary_pass_format():
    """summary() on passing result contains NFR-002, PASS, QPS value."""
    result = ThroughputVerificationResult(
        passed=True,
        qps=1500.0,
        total_requests=450000,
        error_rate=0.000222,
        qps_threshold=1000.0,
        error_rate_threshold=0.01,
    )
    s = result.summary()

    assert "NFR-002" in s
    assert "PASS" in s
    assert "1500" in s
    assert "1000" in s


# ---------------------------------------------------------------------------
# Test M: Happy path — summary() on failing result
# [unit]
# ---------------------------------------------------------------------------

def test_summary_fail_format():
    """summary() on failing result contains FAIL, QPS value, threshold."""
    result = ThroughputVerificationResult(
        passed=False,
        qps=800.0,
        total_requests=240000,
        error_rate=0.005,
        qps_threshold=1000.0,
        error_rate_threshold=0.01,
    )
    s = result.summary()

    assert "NFR-002" in s
    assert "FAIL" in s
    assert "800" in s


# ---------------------------------------------------------------------------
# Test N: Boundary — qps_threshold=0.0
# [unit]
# ---------------------------------------------------------------------------

def test_analyze_csv_zero_qps_threshold(tmp_path):
    """qps_threshold=0.0 means any QPS >= 0 passes the QPS check."""
    csv_path = _write_csv(tmp_path, [_agg_row(
        requests_per_sec=0.1, total_requests=100, failure_count=0,
    )])
    analyzer = ThroughputReportAnalyzer()
    result = analyzer.analyze(csv_path, qps_threshold=0.0)

    assert result.passed is True
    assert result.qps == 0.1


# ---------------------------------------------------------------------------
# Test O: Boundary — error_rate_threshold=0.0 with zero failures
# [unit]
# ---------------------------------------------------------------------------

def test_analyze_csv_zero_error_rate_threshold_with_zero_failures(tmp_path):
    """error_rate_threshold=0.0, failure_count=0 → error_rate=0.0.
    0.0 < 0.0 is False, so passed=False despite QPS passing."""
    csv_path = _write_csv(tmp_path, [_agg_row(
        requests_per_sec=1500.0, total_requests=100000, failure_count=0,
    )])
    analyzer = ThroughputReportAnalyzer()
    result = analyzer.analyze(csv_path, error_rate_threshold=0.0)

    assert result.passed is False
    assert result.error_rate == 0.0


# ---------------------------------------------------------------------------
# Real test — feature 27 CSV file I/O round-trip
# ---------------------------------------------------------------------------

@pytest.mark.real
class TestRealThroughputReportFeature27:
    """Real test: exercises actual CSV file I/O for feature #27."""

    def test_real_csv_roundtrip_analyze_feature_27(self, tmp_path):
        """Real test: write a Locust CSV, parse it, verify throughput metrics extracted."""
        csv_path = _write_csv(tmp_path, [
            _endpoint_row(),
            _agg_row(requests_per_sec=1250.0, total_requests=375000,
                     failure_count=150),
        ])
        analyzer = ThroughputReportAnalyzer()
        result = analyzer.analyze(csv_path, qps_threshold=1000.0)

        assert result.passed is True
        assert result.qps == 1250.0
        assert result.total_requests == 375000
        assert result.error_rate == pytest.approx(150 / 375000)
        assert result.qps_threshold == 1000.0
        assert result.error_rate_threshold == 0.01
