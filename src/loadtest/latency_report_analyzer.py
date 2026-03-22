"""Latency report analyzer — parses Locust stats CSV and checks thresholds."""

import csv
import os

from src.loadtest.verification_result import VerificationResult

# Locust CSV column names
COL_NAME = "Name"
COL_REQUEST_COUNT = "Request Count"
COL_FAILURE_COUNT = "Failure Count"
COL_MEDIAN = "50%"
COL_AVERAGE = "Average Response Time"
COL_P95 = "95%"
COL_P99 = "99%"
AGGREGATED_ROW_NAME = "Aggregated"

REQUIRED_COLUMNS = [COL_NAME, COL_REQUEST_COUNT, COL_FAILURE_COUNT,
                    COL_MEDIAN, COL_AVERAGE, COL_P95, COL_P99]


class LatencyReportAnalyzer:
    """Analyzes Locust load test output to verify latency NFRs."""

    def analyze(
        self, csv_path: str, p95_threshold_ms: float = 1000.0
    ) -> VerificationResult:
        """Analyze a Locust stats CSV file against a p95 latency threshold.

        Args:
            csv_path: Path to the Locust stats CSV file.
            p95_threshold_ms: Maximum acceptable p95 latency in milliseconds.

        Returns:
            VerificationResult with pass/fail verdict and extracted metrics.

        Raises:
            FileNotFoundError: If csv_path does not exist.
            ValueError: If CSV is malformed or has no aggregated row.
        """
        if not os.path.exists(csv_path):
            raise FileNotFoundError(csv_path)

        with open(csv_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        agg_row = None
        for row in rows:
            if row.get(COL_NAME) == AGGREGATED_ROW_NAME:
                agg_row = row
                break

        if agg_row is None:
            raise ValueError("no aggregated stats row in CSV")

        try:
            p95_ms = float(agg_row[COL_P95])
            p99_ms = float(agg_row[COL_P99])
            median_ms = float(agg_row[COL_MEDIAN])
            avg_ms = float(agg_row[COL_AVERAGE])
            total_requests = int(agg_row[COL_REQUEST_COUNT])
            failure_count = int(agg_row[COL_FAILURE_COUNT])
        except KeyError as e:
            raise ValueError(f"malformed CSV: missing column {e}") from e

        failure_rate = failure_count / total_requests if total_requests > 0 else 0.0
        passed = p95_ms <= p95_threshold_ms

        return VerificationResult(
            passed=passed,
            p95_ms=p95_ms,
            p99_ms=p99_ms,
            median_ms=median_ms,
            avg_ms=avg_ms,
            total_requests=total_requests,
            failure_rate=failure_rate,
            threshold_ms=p95_threshold_ms,
        )

    def analyze_from_stats(
        self, stats: list[dict], p95_threshold_ms: float = 1000.0
    ) -> VerificationResult:
        """Analyze from a list of stats dictionaries (programmatic alternative to CSV).

        Args:
            stats: List of dicts with keys: p95_ms, p99_ms, median_ms, avg_ms,
                   total_requests, failure_count.
            p95_threshold_ms: Maximum acceptable p95 latency in milliseconds.

        Returns:
            VerificationResult with pass/fail verdict and aggregated metrics.

        Raises:
            ValueError: If stats list is empty or missing required keys.
        """
        if not stats:
            raise ValueError("stats list must not be empty")

        total_requests = 0
        total_failures = 0
        weighted_p95 = 0.0
        weighted_p99 = 0.0
        weighted_median = 0.0
        weighted_avg = 0.0

        for entry in stats:
            reqs = entry["total_requests"]
            total_requests += reqs
            total_failures += entry["failure_count"]
            weighted_p95 += entry["p95_ms"] * reqs
            weighted_p99 += entry.get("p99_ms", 0.0) * reqs
            weighted_median += entry.get("median_ms", 0.0) * reqs
            weighted_avg += entry.get("avg_ms", 0.0) * reqs

        if total_requests > 0:
            p95_ms = weighted_p95 / total_requests
            p99_ms = weighted_p99 / total_requests
            median_ms = weighted_median / total_requests
            avg_ms = weighted_avg / total_requests
            failure_rate = total_failures / total_requests
        else:
            p95_ms = 0.0
            p99_ms = 0.0
            median_ms = 0.0
            avg_ms = 0.0
            failure_rate = 0.0

        passed = p95_ms <= p95_threshold_ms

        return VerificationResult(
            passed=passed,
            p95_ms=p95_ms,
            p99_ms=p99_ms,
            median_ms=median_ms,
            avg_ms=avg_ms,
            total_requests=total_requests,
            failure_rate=failure_rate,
            threshold_ms=p95_threshold_ms,
        )
