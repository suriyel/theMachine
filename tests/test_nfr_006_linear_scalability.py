"""Tests for NFR-006: Linear Scalability >= 70% verification components.

Components: ScalabilityReportAnalyzer, ScalabilityVerificationResult.

# [no integration test] — pure function, no external service dependencies
# All components operate on in-memory data or local CSV files via tmp_path.
# Security: N/A — internal utility with no user-facing input
"""

import csv

import pytest

from src.loadtest.scalability_verification_result import ScalabilityVerificationResult
from src.loadtest.scalability_report_analyzer import ScalabilityReportAnalyzer


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
    requests_per_sec: float = 1000.0,
    total_requests: int = 300000,
    failure_count: int = 0,
) -> dict:
    """Build an Aggregated row dict for Locust CSV."""
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
        "Failures/s": "0.0",
        "50%": "200",
        "66%": "300",
        "75%": "350",
        "80%": "400",
        "90%": "500",
        "95%": "600",
        "98%": "800",
        "99%": "900",
        "99.9%": "1500",
        "99.99%": "2000",
        "100%": "5000",
    }


# ---------------------------------------------------------------------------
# Test A: Happy path — CSV analyze, passing (efficiency=0.80)
# [unit]
# ---------------------------------------------------------------------------
class TestAnalyzeCSVPassing:
    def test_passing_scalability(self, tmp_path):
        """Baseline: 1000 QPS / 2 nodes, Scaled: 1400 QPS / 3 nodes.
        efficiency = (1400-1000) / (1000/2) = 400/500 = 0.80 >= 0.70 → PASS"""
        baseline_csv = _write_csv(tmp_path, [_agg_row(1000.0)], "baseline.csv")
        scaled_csv = _write_csv(tmp_path, [_agg_row(1400.0)], "scaled.csv")

        analyzer = ScalabilityReportAnalyzer()
        result = analyzer.analyze(baseline_csv, scaled_csv, baseline_nodes=2, scaled_nodes=3)

        assert result.passed is True
        assert result.efficiency == pytest.approx(0.80, abs=0.001)
        assert result.baseline_qps == pytest.approx(1000.0)
        assert result.scaled_qps == pytest.approx(1400.0)
        assert result.baseline_nodes == 2
        assert result.scaled_nodes == 3
        assert result.efficiency_threshold == pytest.approx(0.70)


# ---------------------------------------------------------------------------
# Test B: Happy path — CSV analyze, failing (efficiency=0.40)
# [unit]
# ---------------------------------------------------------------------------
class TestAnalyzeCSVFailing:
    def test_failing_scalability(self, tmp_path):
        """Baseline: 1000 QPS / 2 nodes, Scaled: 1200 QPS / 3 nodes.
        efficiency = (1200-1000) / (1000/2) = 200/500 = 0.40 < 0.70 → FAIL"""
        baseline_csv = _write_csv(tmp_path, [_agg_row(1000.0)], "baseline.csv")
        scaled_csv = _write_csv(tmp_path, [_agg_row(1200.0)], "scaled.csv")

        analyzer = ScalabilityReportAnalyzer()
        result = analyzer.analyze(baseline_csv, scaled_csv, baseline_nodes=2, scaled_nodes=3)

        assert result.passed is False
        assert result.efficiency == pytest.approx(0.40, abs=0.001)
        assert result.baseline_qps == pytest.approx(1000.0)
        assert result.scaled_qps == pytest.approx(1200.0)


# ---------------------------------------------------------------------------
# Test C: Happy path — analyze_from_stats, super-linear (efficiency=1.05)
# [unit]
# ---------------------------------------------------------------------------
class TestFromStatsSuperLinear:
    def test_superlinear_scalability(self):
        """baseline_qps=900, scaled_qps=1530, 3→5 nodes.
        efficiency = (1530-900) / (900/3*2) = 630/600 = 1.05 → PASS"""
        analyzer = ScalabilityReportAnalyzer()
        result = analyzer.analyze_from_stats(
            baseline_qps=900.0, scaled_qps=1530.0,
            baseline_nodes=3, scaled_nodes=5,
        )

        assert result.passed is True
        assert result.efficiency == pytest.approx(1.05, abs=0.001)
        assert result.baseline_qps == pytest.approx(900.0)
        assert result.scaled_qps == pytest.approx(1530.0)
        assert result.baseline_nodes == 3
        assert result.scaled_nodes == 5


# ---------------------------------------------------------------------------
# Test D: Boundary — exactly at threshold (efficiency=0.70)
# [unit]
# ---------------------------------------------------------------------------
class TestExactlyAtThreshold:
    def test_at_threshold_passes(self):
        """baseline_qps=1000, scaled_qps=1350, 2→3 nodes.
        efficiency = 350/500 = 0.70 >= 0.70 → PASS"""
        analyzer = ScalabilityReportAnalyzer()
        result = analyzer.analyze_from_stats(
            baseline_qps=1000.0, scaled_qps=1350.0,
            baseline_nodes=2, scaled_nodes=3,
        )

        assert result.passed is True
        assert result.efficiency == pytest.approx(0.70, abs=0.001)


# ---------------------------------------------------------------------------
# Test E: Boundary — just below threshold (efficiency=0.698)
# [unit]
# ---------------------------------------------------------------------------
class TestJustBelowThreshold:
    def test_below_threshold_fails(self):
        """baseline_qps=1000, scaled_qps=1349, 2→3 nodes.
        efficiency = 349/500 = 0.698 < 0.70 → FAIL"""
        analyzer = ScalabilityReportAnalyzer()
        result = analyzer.analyze_from_stats(
            baseline_qps=1000.0, scaled_qps=1349.0,
            baseline_nodes=2, scaled_nodes=3,
        )

        assert result.passed is False
        assert result.efficiency == pytest.approx(0.698, abs=0.001)


# ---------------------------------------------------------------------------
# Test F: Boundary — negative increase (scaled < baseline)
# [unit]
# ---------------------------------------------------------------------------
class TestNegativeIncrease:
    def test_negative_increase_clamps_to_zero(self):
        """baseline_qps=1000, scaled_qps=900, 2→3 nodes.
        actual_increase = -100 → efficiency = 0.0 → FAIL"""
        analyzer = ScalabilityReportAnalyzer()
        result = analyzer.analyze_from_stats(
            baseline_qps=1000.0, scaled_qps=900.0,
            baseline_nodes=2, scaled_nodes=3,
        )

        assert result.passed is False
        assert result.efficiency == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test G: Boundary — zero increase (scaled == baseline)
# [unit]
# ---------------------------------------------------------------------------
class TestZeroIncrease:
    def test_zero_increase_efficiency_zero(self):
        """baseline_qps=1000, scaled_qps=1000, 2→3 nodes.
        actual_increase = 0 → efficiency = 0.0 → FAIL"""
        analyzer = ScalabilityReportAnalyzer()
        result = analyzer.analyze_from_stats(
            baseline_qps=1000.0, scaled_qps=1000.0,
            baseline_nodes=2, scaled_nodes=3,
        )

        assert result.passed is False
        assert result.efficiency == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test H: Boundary — zero threshold with zero increase passes
# [unit]
# ---------------------------------------------------------------------------
class TestZeroThreshold:
    def test_zero_threshold_zero_increase_passes(self):
        """efficiency_threshold=0.0, efficiency=0.0. 0.0 >= 0.0 → PASS"""
        analyzer = ScalabilityReportAnalyzer()
        result = analyzer.analyze_from_stats(
            baseline_qps=1000.0, scaled_qps=1000.0,
            baseline_nodes=2, scaled_nodes=3,
            efficiency_threshold=0.0,
        )

        assert result.passed is True
        assert result.efficiency == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Test I: Boundary — minimum node count (1→2)
# [unit]
# ---------------------------------------------------------------------------
class TestMinimumNodeCount:
    def test_one_to_two_nodes(self):
        """baseline_nodes=1, scaled_nodes=2, baseline_qps=500, scaled_qps=850.
        efficiency = (850-500) / (500/1) = 350/500 = 0.70 → PASS"""
        analyzer = ScalabilityReportAnalyzer()
        result = analyzer.analyze_from_stats(
            baseline_qps=500.0, scaled_qps=850.0,
            baseline_nodes=1, scaled_nodes=2,
        )

        assert result.passed is True
        assert result.efficiency == pytest.approx(0.70, abs=0.001)


# ---------------------------------------------------------------------------
# Test J: Error — baseline CSV path does not exist
# [unit]
# ---------------------------------------------------------------------------
class TestBaselineCSVNotFound:
    def test_missing_baseline_csv(self, tmp_path):
        scaled_csv = _write_csv(tmp_path, [_agg_row(1400.0)], "scaled.csv")
        analyzer = ScalabilityReportAnalyzer()

        with pytest.raises(FileNotFoundError):
            analyzer.analyze("/nonexistent/baseline.csv", scaled_csv, 2, 3)


# ---------------------------------------------------------------------------
# Test K: Error — scaled CSV path does not exist
# [unit]
# ---------------------------------------------------------------------------
class TestScaledCSVNotFound:
    def test_missing_scaled_csv(self, tmp_path):
        baseline_csv = _write_csv(tmp_path, [_agg_row(1000.0)], "baseline.csv")
        analyzer = ScalabilityReportAnalyzer()

        with pytest.raises(FileNotFoundError):
            analyzer.analyze(baseline_csv, "/nonexistent/scaled.csv", 2, 3)


# ---------------------------------------------------------------------------
# Test L: Error — baseline_nodes < 1
# [unit]
# ---------------------------------------------------------------------------
class TestBaselineNodesTooLow:
    def test_baseline_nodes_zero(self, tmp_path):
        baseline_csv = _write_csv(tmp_path, [_agg_row(1000.0)], "baseline.csv")
        scaled_csv = _write_csv(tmp_path, [_agg_row(1400.0)], "scaled.csv")
        analyzer = ScalabilityReportAnalyzer()

        with pytest.raises(ValueError, match="baseline_nodes must be >= 1"):
            analyzer.analyze(baseline_csv, scaled_csv, baseline_nodes=0, scaled_nodes=3)


# ---------------------------------------------------------------------------
# Test M: Error — scaled_nodes == baseline_nodes
# [unit]
# ---------------------------------------------------------------------------
class TestScaledNodesEqual:
    def test_equal_node_counts(self, tmp_path):
        baseline_csv = _write_csv(tmp_path, [_agg_row(1000.0)], "baseline.csv")
        scaled_csv = _write_csv(tmp_path, [_agg_row(1400.0)], "scaled.csv")
        analyzer = ScalabilityReportAnalyzer()

        with pytest.raises(ValueError, match="scaled_nodes must be > baseline_nodes"):
            analyzer.analyze(baseline_csv, scaled_csv, baseline_nodes=2, scaled_nodes=2)


# ---------------------------------------------------------------------------
# Test N: Error — scaled_nodes < baseline_nodes
# [unit]
# ---------------------------------------------------------------------------
class TestScaledNodesLess:
    def test_reversed_node_counts(self, tmp_path):
        baseline_csv = _write_csv(tmp_path, [_agg_row(1000.0)], "baseline.csv")
        scaled_csv = _write_csv(tmp_path, [_agg_row(1400.0)], "scaled.csv")
        analyzer = ScalabilityReportAnalyzer()

        with pytest.raises(ValueError, match="scaled_nodes must be > baseline_nodes"):
            analyzer.analyze(baseline_csv, scaled_csv, baseline_nodes=3, scaled_nodes=1)


# ---------------------------------------------------------------------------
# Test O: Error — analyze_from_stats with baseline_qps=0.0
# [unit]
# ---------------------------------------------------------------------------
class TestFromStatsZeroQPS:
    def test_zero_baseline_qps(self):
        analyzer = ScalabilityReportAnalyzer()

        with pytest.raises(ValueError, match="baseline_qps must be > 0"):
            analyzer.analyze_from_stats(
                baseline_qps=0.0, scaled_qps=1000.0,
                baseline_nodes=2, scaled_nodes=3,
            )


# ---------------------------------------------------------------------------
# Test P: Error — analyze_from_stats with negative baseline_qps
# [unit]
# ---------------------------------------------------------------------------
class TestFromStatsNegativeQPS:
    def test_negative_baseline_qps(self):
        analyzer = ScalabilityReportAnalyzer()

        with pytest.raises(ValueError, match="baseline_qps must be > 0"):
            analyzer.analyze_from_stats(
                baseline_qps=-10.0, scaled_qps=1000.0,
                baseline_nodes=2, scaled_nodes=3,
            )


# ---------------------------------------------------------------------------
# Test Q: Error — CSV analyze with 0.0 QPS in baseline
# [unit]
# ---------------------------------------------------------------------------
class TestCSVZeroQPS:
    def test_zero_qps_in_csv(self, tmp_path):
        baseline_csv = _write_csv(tmp_path, [_agg_row(0.0)], "baseline.csv")
        scaled_csv = _write_csv(tmp_path, [_agg_row(1000.0)], "scaled.csv")
        analyzer = ScalabilityReportAnalyzer()

        with pytest.raises(ValueError, match="baseline QPS must be > 0"):
            analyzer.analyze(baseline_csv, scaled_csv, baseline_nodes=2, scaled_nodes=3)


# ---------------------------------------------------------------------------
# Test R: Happy path — summary format (passing)
# [unit]
# ---------------------------------------------------------------------------
class TestSummaryPassing:
    def test_summary_format_pass(self):
        result = ScalabilityVerificationResult(
            passed=True,
            efficiency=0.80,
            baseline_qps=1000.0,
            scaled_qps=1400.0,
            baseline_nodes=2,
            scaled_nodes=3,
            efficiency_threshold=0.70,
        )
        s = result.summary()
        expected = (
            "NFR-006: PASS — "
            "efficiency=80.00% "
            "(threshold=70.00%), "
            "baseline_qps=1000.0 (2 nodes), "
            "scaled_qps=1400.0 (3 nodes)"
        )
        assert s == expected


# ---------------------------------------------------------------------------
# Test S: Happy path — summary format (failing)
# [unit]
# ---------------------------------------------------------------------------
class TestSummaryFailing:
    def test_summary_format_fail(self):
        result = ScalabilityVerificationResult(
            passed=False,
            efficiency=0.40,
            baseline_qps=1000.0,
            scaled_qps=1200.0,
            baseline_nodes=2,
            scaled_nodes=3,
            efficiency_threshold=0.70,
        )
        s = result.summary()
        expected = (
            "NFR-006: FAIL — "
            "efficiency=40.00% "
            "(threshold=70.00%), "
            "baseline_qps=1000.0 (2 nodes), "
            "scaled_qps=1200.0 (3 nodes)"
        )
        assert s == expected


# ---------------------------------------------------------------------------
# Test T: Mutation killer — analyze_from_stats with baseline_nodes=1 (kill #3, #4)
# Validates that baseline_nodes=1 is accepted (not rejected by `< 1` guard)
# [unit]
# ---------------------------------------------------------------------------
class TestFromStatsBaselineNodesOne:
    def test_baseline_nodes_one_accepted(self):
        """analyze_from_stats with baseline_nodes=1 should not raise."""
        analyzer = ScalabilityReportAnalyzer()
        result = analyzer.analyze_from_stats(
            baseline_qps=500.0, scaled_qps=850.0,
            baseline_nodes=1, scaled_nodes=2,
        )
        assert result.passed is True


# ---------------------------------------------------------------------------
# Test U: Mutation killer — analyze_from_stats with equal node counts (kill #24)
# [unit]
# ---------------------------------------------------------------------------
class TestFromStatsEqualNodes:
    def test_equal_node_counts_raises(self):
        analyzer = ScalabilityReportAnalyzer()
        with pytest.raises(ValueError, match=r"^scaled_nodes must be > baseline_nodes$"):
            analyzer.analyze_from_stats(
                baseline_qps=1000.0, scaled_qps=1400.0,
                baseline_nodes=2, scaled_nodes=2,
            )


# ---------------------------------------------------------------------------
# Test V: Mutation killer — analyze_from_stats with baseline_qps=0.5 (kill #19)
# [unit]
# ---------------------------------------------------------------------------
class TestFromStatsSmallQPS:
    def test_small_positive_qps_accepted(self):
        """baseline_qps=0.5 should NOT raise (> 0), killing <= 1 mutant."""
        analyzer = ScalabilityReportAnalyzer()
        result = analyzer.analyze_from_stats(
            baseline_qps=0.5, scaled_qps=1.0,
            baseline_nodes=1, scaled_nodes=2,
        )
        assert result.efficiency == pytest.approx(1.0, abs=0.001)


# ---------------------------------------------------------------------------
# Test W: Mutation killer — CSV analyze with small positive QPS (kill #15)
# [unit]
# ---------------------------------------------------------------------------
class TestCSVSmallQPS:
    def test_small_positive_qps_csv(self, tmp_path):
        """baseline QPS 0.5 in CSV should not raise (> 0), killing <= 1 mutant."""
        baseline_csv = _write_csv(tmp_path, [_agg_row(0.5)], "baseline.csv")
        scaled_csv = _write_csv(tmp_path, [_agg_row(1.0)], "scaled.csv")
        analyzer = ScalabilityReportAnalyzer()
        result = analyzer.analyze(baseline_csv, scaled_csv, baseline_nodes=1, scaled_nodes=2)
        assert result.passed is True


# ---------------------------------------------------------------------------
# Test X: Mutation killer — actual_increase near boundary (kill #35)
# [unit]
# ---------------------------------------------------------------------------
class TestSmallActualIncrease:
    def test_tiny_actual_increase_counted(self):
        """actual_increase=0.5 (between 0 and 1) should yield non-zero efficiency."""
        analyzer = ScalabilityReportAnalyzer()
        # baseline_qps=100, scaled_qps=100.5, nodes 1→2
        # actual_increase = 0.5, theoretical = 100, efficiency = 0.005
        result = analyzer.analyze_from_stats(
            baseline_qps=100.0, scaled_qps=100.5,
            baseline_nodes=1, scaled_nodes=2,
        )
        assert result.efficiency == pytest.approx(0.005, abs=0.001)
        assert result.passed is False


# ---------------------------------------------------------------------------
# Test Y: Mutation killer — error message exact match (kill #5, #7, #16, #20, #23, #25)
# [unit]
# ---------------------------------------------------------------------------
class TestErrorMessageExact:
    def test_baseline_nodes_error_message_exact_csv(self, tmp_path):
        baseline_csv = _write_csv(tmp_path, [_agg_row(1000.0)], "baseline.csv")
        scaled_csv = _write_csv(tmp_path, [_agg_row(1400.0)], "scaled.csv")
        analyzer = ScalabilityReportAnalyzer()
        with pytest.raises(ValueError, match=r"^baseline_nodes must be >= 1$"):
            analyzer.analyze(baseline_csv, scaled_csv, baseline_nodes=0, scaled_nodes=3)

    def test_scaled_nodes_error_message_exact_csv(self, tmp_path):
        baseline_csv = _write_csv(tmp_path, [_agg_row(1000.0)], "baseline.csv")
        scaled_csv = _write_csv(tmp_path, [_agg_row(1400.0)], "scaled.csv")
        analyzer = ScalabilityReportAnalyzer()
        with pytest.raises(ValueError, match=r"^scaled_nodes must be > baseline_nodes$"):
            analyzer.analyze(baseline_csv, scaled_csv, baseline_nodes=2, scaled_nodes=2)

    def test_baseline_qps_error_message_exact_csv(self, tmp_path):
        baseline_csv = _write_csv(tmp_path, [_agg_row(0.0)], "baseline.csv")
        scaled_csv = _write_csv(tmp_path, [_agg_row(1000.0)], "scaled.csv")
        analyzer = ScalabilityReportAnalyzer()
        with pytest.raises(ValueError, match=r"^baseline QPS must be > 0"):
            analyzer.analyze(baseline_csv, scaled_csv, baseline_nodes=2, scaled_nodes=3)

    def test_baseline_qps_error_message_exact_stats(self):
        analyzer = ScalabilityReportAnalyzer()
        with pytest.raises(ValueError, match=r"^baseline_qps must be > 0$"):
            analyzer.analyze_from_stats(
                baseline_qps=0.0, scaled_qps=1000.0,
                baseline_nodes=2, scaled_nodes=3,
            )

    def test_baseline_nodes_error_message_exact_stats(self):
        analyzer = ScalabilityReportAnalyzer()
        with pytest.raises(ValueError, match=r"^baseline_nodes must be >= 1$"):
            analyzer.analyze_from_stats(
                baseline_qps=1000.0, scaled_qps=1400.0,
                baseline_nodes=0, scaled_nodes=3,
            )

    def test_scaled_nodes_error_message_exact_stats(self):
        analyzer = ScalabilityReportAnalyzer()
        with pytest.raises(ValueError, match=r"^scaled_nodes must be > baseline_nodes$"):
            analyzer.analyze_from_stats(
                baseline_qps=1000.0, scaled_qps=1400.0,
                baseline_nodes=2, scaled_nodes=2,
            )


# ---------------------------------------------------------------------------
# Real test — feature 31 CSV file I/O round-trip
# ---------------------------------------------------------------------------

@pytest.mark.real
class TestRealScalabilityReportFeature31:
    """Real test: exercises actual CSV file I/O for feature #31."""

    def test_real_csv_roundtrip_analyze_feature_31(self, tmp_path):
        """Real test: write two Locust CSVs, parse them, verify scalability metrics."""
        baseline_csv = _write_csv(
            tmp_path, [_agg_row(requests_per_sec=1000.0)], "baseline.csv",
        )
        scaled_csv = _write_csv(
            tmp_path, [_agg_row(requests_per_sec=1400.0)], "scaled.csv",
        )

        analyzer = ScalabilityReportAnalyzer()
        result = analyzer.analyze(
            baseline_csv, scaled_csv, baseline_nodes=2, scaled_nodes=3,
        )

        assert result.passed is True
        assert result.efficiency == pytest.approx(0.80, abs=0.001)
        assert result.baseline_qps == pytest.approx(1000.0)
        assert result.scaled_qps == pytest.approx(1400.0)
        assert result.baseline_nodes == 2
        assert result.scaled_nodes == 3
        assert result.efficiency_threshold == pytest.approx(0.70)
