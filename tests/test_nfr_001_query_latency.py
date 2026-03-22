"""Tests for NFR-001: Query Latency p95 < 1s verification components.

Components: LatencyReportAnalyzer, QueryGenerator, VerificationResult.

# [no integration test] — pure function, no external I/O
# All components operate on in-memory data or local CSV files via tmp_path.
# Security: N/A — internal utility with no user-facing input
"""

import csv
import textwrap

import pytest

from src.loadtest.verification_result import VerificationResult
from src.loadtest.latency_report_analyzer import LatencyReportAnalyzer
from src.loadtest.query_generator import QueryGenerator


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
    p95: float = 487.0,
    p99: float = 650.0,
    median: float = 200.0,
    avg: float = 250.0,
    total_requests: int = 10000,
    failure_count: int = 0,
) -> dict:
    """Build a Locust 'Aggregated' stats row with specified metrics."""
    return {
        "Type": "",
        "Name": "Aggregated",
        "Request Count": str(total_requests),
        "Failure Count": str(failure_count),
        "Median Response Time": str(median),
        "Average Response Time": str(avg),
        "Min Response Time": "10",
        "Max Response Time": "2000",
        "Average Content Size": "512",
        "Requests/s": "100.0",
        "Failures/s": "0.0",
        "50%": str(median),
        "66%": "350",
        "75%": "400",
        "80%": "420",
        "90%": "460",
        "95%": str(p95),
        "98%": "600",
        "99%": str(p99),
        "99.9%": "900",
        "99.99%": "1500",
        "100%": "2000",
    }


def _endpoint_row(name: str = "POST /api/v1/query") -> dict:
    """Build a per-endpoint stats row."""
    return {
        "Type": "POST",
        "Name": name,
        "Request Count": "5000",
        "Failure Count": "0",
        "Median Response Time": "200",
        "Average Response Time": "250",
        "Min Response Time": "10",
        "Max Response Time": "2000",
        "Average Content Size": "512",
        "Requests/s": "50.0",
        "Failures/s": "0.0",
        "50%": "200",
        "66%": "350",
        "75%": "400",
        "80%": "420",
        "90%": "460",
        "95%": "487",
        "98%": "600",
        "99%": "650",
        "99.9%": "900",
        "99.99%": "1500",
        "100%": "2000",
    }


# ===========================================================================
# Test A — happy path: p95 well under threshold → PASS
# ===========================================================================
# [unit] — in-memory CSV via tmp_path
class TestLatencyReportAnalyzerHappyPath:
    def test_a_p95_under_threshold_passes(self, tmp_path):
        """Kills: analyzer always returns False regardless of data."""
        csv_path = _write_csv(tmp_path, [_endpoint_row(), _agg_row(p95=487.0)])
        analyzer = LatencyReportAnalyzer()
        result = analyzer.analyze(csv_path, p95_threshold_ms=1000.0)

        assert result.passed is True
        assert result.p95_ms == 487.0
        assert result.p99_ms == 650.0
        assert result.median_ms == 200.0
        assert result.avg_ms == 250.0
        assert result.total_requests == 10000
        assert result.failure_rate == 0.0
        assert result.threshold_ms == 1000.0

    # -----------------------------------------------------------------------
    # Test B — happy path: p95 over threshold → FAIL
    # -----------------------------------------------------------------------
    def test_b_p95_over_threshold_fails(self, tmp_path):
        """Kills: analyzer always returns True regardless of data."""
        csv_path = _write_csv(tmp_path, [_endpoint_row(), _agg_row(p95=1200.0)])
        analyzer = LatencyReportAnalyzer()
        result = analyzer.analyze(csv_path, p95_threshold_ms=1000.0)

        assert result.passed is False
        assert result.p95_ms == 1200.0

    # -----------------------------------------------------------------------
    # Test C — boundary: p95 exactly equals threshold → PASS (uses <=)
    # -----------------------------------------------------------------------
    def test_c_p95_equals_threshold_passes(self, tmp_path):
        """Kills: off-by-one using < instead of <=."""
        csv_path = _write_csv(tmp_path, [_agg_row(p95=1000.0)])
        analyzer = LatencyReportAnalyzer()
        result = analyzer.analyze(csv_path, p95_threshold_ms=1000.0)

        assert result.passed is True
        assert result.p95_ms == 1000.0


# ===========================================================================
# Test D — error: file not found → FileNotFoundError
# ===========================================================================
# [unit] — no I/O dependencies
class TestLatencyReportAnalyzerErrors:
    def test_d_file_not_found(self):
        """Kills: missing file existence check → crash on open."""
        analyzer = LatencyReportAnalyzer()
        with pytest.raises(FileNotFoundError):
            analyzer.analyze("/nonexistent/path/stats.csv")

    # -----------------------------------------------------------------------
    # Test E — error: no Aggregated row → ValueError
    # -----------------------------------------------------------------------
    def test_e_no_aggregated_row(self, tmp_path):
        """Kills: analyzer reads wrong row or returns garbage."""
        csv_path = _write_csv(tmp_path, [_endpoint_row()])
        analyzer = LatencyReportAnalyzer()
        with pytest.raises(ValueError, match="no aggregated stats row"):
            analyzer.analyze(csv_path)

    # -----------------------------------------------------------------------
    # Test F — error: malformed CSV missing 95% column → ValueError
    # -----------------------------------------------------------------------
    def test_f_malformed_csv_missing_column(self, tmp_path):
        """Kills: uncaught KeyError propagates as unhandled exception."""
        path = tmp_path / "bad.csv"
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Type", "Name", "Request Count"])
            writer.writerow(["", "Aggregated", "1000"])
        analyzer = LatencyReportAnalyzer()
        with pytest.raises(ValueError, match="malformed CSV"):
            analyzer.analyze(str(path))


# ===========================================================================
# Test G — boundary: zero total_requests → failure_rate=0.0 (no div-by-zero)
# ===========================================================================
# [unit]
class TestLatencyReportAnalyzerBoundary:
    def test_g_zero_requests_no_division_error(self, tmp_path):
        """Kills: division by zero when total_requests=0."""
        csv_path = _write_csv(
            tmp_path, [_agg_row(total_requests=0, failure_count=0)]
        )
        analyzer = LatencyReportAnalyzer()
        result = analyzer.analyze(csv_path)

        assert result.failure_rate == 0.0
        assert result.total_requests == 0


# ===========================================================================
# Tests H–L, P — QueryGenerator.generate_payloads
# ===========================================================================
# [unit] — pure computation
class TestQueryGenerator:
    def test_h_default_mix_ratio(self):
        """Kills: wrong split calculation."""
        gen = QueryGenerator()
        payloads = gen.generate_payloads(count=10, mix_ratio=0.7)

        assert len(payloads) == 10
        nl_count = sum(1 for p in payloads if p.get("query_type") == "nl")
        sym_count = sum(1 for p in payloads if p.get("query_type") == "symbol")
        assert nl_count == 7
        assert sym_count == 3
        # Each payload has required keys
        for p in payloads:
            assert "query" in p
            assert isinstance(p["query"], str)
            assert len(p["query"]) > 0

    def test_i_mix_ratio_zero_all_symbol(self):
        """Kills: edge case all-symbol not handled."""
        gen = QueryGenerator()
        payloads = gen.generate_payloads(count=5, mix_ratio=0.0)

        assert len(payloads) == 5
        assert all(p["query_type"] == "symbol" for p in payloads)

    def test_j_mix_ratio_one_all_nl(self):
        """Kills: edge case all-NL not handled."""
        gen = QueryGenerator()
        payloads = gen.generate_payloads(count=5, mix_ratio=1.0)

        assert len(payloads) == 5
        assert all(p["query_type"] == "nl" for p in payloads)

    def test_k_count_zero_raises(self):
        """Kills: missing input validation allows empty list."""
        gen = QueryGenerator()
        with pytest.raises(ValueError, match="count must be > 0"):
            gen.generate_payloads(count=0)

    def test_l_mix_ratio_out_of_range_raises(self):
        """Kills: invalid ratio silently produces wrong split."""
        gen = QueryGenerator()
        with pytest.raises(ValueError, match="mix_ratio must be in"):
            gen.generate_payloads(count=5, mix_ratio=1.5)

        with pytest.raises(ValueError, match="mix_ratio must be in"):
            gen.generate_payloads(count=5, mix_ratio=-0.1)

    def test_p_count_one_minimal(self):
        """Kills: off-by-one when count is minimal."""
        gen = QueryGenerator()
        payloads = gen.generate_payloads(count=1, mix_ratio=0.7)

        assert len(payloads) == 1
        # round(1 * 0.7) = 1 → should be NL
        assert payloads[0]["query_type"] == "nl"


# ===========================================================================
# Tests M–N — analyze_from_stats
# ===========================================================================
# [unit]
class TestAnalyzeFromStats:
    def test_m_from_stats_happy_path(self):
        """Kills: analyze_from_stats not wired correctly."""
        analyzer = LatencyReportAnalyzer()
        stats = [
            {
                "p95_ms": 400.0,
                "p99_ms": 550.0,
                "median_ms": 180.0,
                "avg_ms": 200.0,
                "total_requests": 5000,
                "failure_count": 5,
            }
        ]
        result = analyzer.analyze_from_stats(stats, p95_threshold_ms=1000.0)

        assert result.passed is True
        assert result.p95_ms == 400.0
        assert result.p99_ms == 550.0
        assert result.median_ms == 180.0
        assert result.avg_ms == 200.0
        assert result.failure_rate == pytest.approx(0.001)
        assert result.total_requests == 5000
        assert result.threshold_ms == 1000.0

    def test_m2_from_stats_multi_entry_weighted_aggregation(self):
        """Kills: += vs = bug in weighted aggregation (single entry hides it)."""
        analyzer = LatencyReportAnalyzer()
        stats = [
            {
                "p95_ms": 300.0,
                "p99_ms": 400.0,
                "median_ms": 100.0,
                "avg_ms": 150.0,
                "total_requests": 2000,
                "failure_count": 2,
            },
            {
                "p95_ms": 600.0,
                "p99_ms": 800.0,
                "median_ms": 300.0,
                "avg_ms": 350.0,
                "total_requests": 3000,
                "failure_count": 9,
            },
        ]
        result = analyzer.analyze_from_stats(stats, p95_threshold_ms=1000.0)

        # Weighted averages: (300*2000 + 600*3000) / 5000 = 2400000/5000 = 480
        assert result.passed is True
        assert result.p95_ms == pytest.approx(480.0)
        assert result.p99_ms == pytest.approx(640.0)  # (400*2000 + 800*3000)/5000
        assert result.median_ms == pytest.approx(220.0)  # (100*2000 + 300*3000)/5000
        assert result.avg_ms == pytest.approx(270.0)  # (150*2000 + 350*3000)/5000
        assert result.total_requests == 5000
        assert result.failure_rate == pytest.approx(11 / 5000)

    def test_n_from_stats_empty_raises(self):
        """Kills: missing empty-list guard."""
        analyzer = LatencyReportAnalyzer()
        with pytest.raises(ValueError, match="stats list must not be empty"):
            analyzer.analyze_from_stats([], p95_threshold_ms=1000.0)


# ===========================================================================
# Test O — VerificationResult.summary()
# ===========================================================================
# [unit]
class TestVerificationResultSummary:
    def test_o_summary_contains_key_info(self):
        """Kills: summary method returns empty or wrong format."""
        result = VerificationResult(
            passed=True,
            p95_ms=487.0,
            p99_ms=650.0,
            median_ms=200.0,
            avg_ms=250.0,
            total_requests=10000,
            failure_rate=0.0,
            threshold_ms=1000.0,
        )
        summary = result.summary()

        assert "PASS" in summary
        assert "487" in summary
        assert "10000" in summary or "10,000" in summary

    def test_o_summary_fail_contains_threshold(self):
        """Kills: summary omits threshold information."""
        result = VerificationResult(
            passed=False,
            p95_ms=1200.0,
            p99_ms=1500.0,
            median_ms=500.0,
            avg_ms=600.0,
            total_requests=8000,
            failure_rate=0.05,
            threshold_ms=1000.0,
        )
        summary = result.summary()
        assert "1000" in summary

    def test_o_summary_fail_verdict(self):
        """Kills: summary always shows PASS regardless of actual result."""
        result = VerificationResult(
            passed=False,
            p95_ms=1200.0,
            p99_ms=1500.0,
            median_ms=500.0,
            avg_ms=600.0,
            total_requests=8000,
            failure_rate=0.05,
            threshold_ms=1000.0,
        )
        summary = result.summary()

        assert "FAIL" in summary
        assert "1200" in summary


# ===========================================================================
# Tests for QueryLatencyLoadTest (Locust HttpUser)
# ===========================================================================
# [unit] — verifies locustfile module structure without importing locust
# (locust's gevent monkey-patching conflicts with full test suite context)
class TestQueryLatencyLoadTest:
    def test_locustfile_module_exists(self):
        """Kills: missing locustfile module."""
        import importlib.util
        spec = importlib.util.find_spec("src.loadtest.locustfile")
        assert spec is not None, "src.loadtest.locustfile module not found"

    def test_locustfile_contains_load_test_class(self):
        """Kills: missing QueryLatencyLoadTest class definition."""
        import ast
        with open("src/loadtest/locustfile.py") as f:
            tree = ast.parse(f.read())
        class_names = [
            node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
        ]
        assert "QueryLatencyLoadTest" in class_names

    def test_locustfile_has_task_method(self):
        """Kills: missing query_api task method."""
        import ast
        with open("src/loadtest/locustfile.py") as f:
            tree = ast.parse(f.read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "QueryLatencyLoadTest":
                method_names = [
                    n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                assert "on_start" in method_names, "on_start method missing"
                assert "query_api" in method_names, "query_api task method missing"

    def test_locustfile_imports_query_generator(self):
        """Kills: locustfile not wired to QueryGenerator."""
        with open("src/loadtest/locustfile.py") as f:
            content = f.read()
        assert "QueryGenerator" in content
        assert "generate_payloads" in content


# ===========================================================================
# Test: payloads include repo_id key
# ===========================================================================
# [unit]
class TestQueryGeneratorRepoId:
    def test_payloads_include_repo_id_key(self):
        """Kills: repo_id key missing from Interface Contract."""
        gen = QueryGenerator()
        payloads = gen.generate_payloads(count=10, mix_ratio=0.5)
        for p in payloads:
            assert "repo_id" in p


# ===========================================================================
# Real test — feature 26 CSV file I/O round-trip
# ===========================================================================
@pytest.mark.real
class TestRealLatencyReportFeature26:
    """Real test: exercises actual CSV file I/O for feature #26."""

    def test_real_csv_roundtrip_analyze_feature_26(self, tmp_path):
        """Real test: write a Locust CSV, parse it, verify metrics extracted correctly."""
        csv_path = _write_csv(tmp_path, [
            _endpoint_row(),
            _agg_row(p95=520.0, p99=700.0, median=180.0, avg=220.0,
                     total_requests=15000, failure_count=30),
        ])
        analyzer = LatencyReportAnalyzer()
        result = analyzer.analyze(csv_path, p95_threshold_ms=1000.0)

        assert result.passed is True
        assert result.p95_ms == 520.0
        assert result.p99_ms == 700.0
        assert result.median_ms == 180.0
        assert result.avg_ms == 220.0
        assert result.total_requests == 15000
        assert result.failure_rate == pytest.approx(30 / 15000)
