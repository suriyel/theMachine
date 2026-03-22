"""Throughput report analyzer — parses Locust stats CSV and checks QPS thresholds."""

import csv
import os

from src.loadtest.throughput_verification_result import ThroughputVerificationResult

COL_NAME = "Name"
COL_REQUEST_COUNT = "Request Count"
COL_FAILURE_COUNT = "Failure Count"
COL_REQUESTS_PER_SEC = "Requests/s"
AGGREGATED_ROW_NAME = "Aggregated"

REQUIRED_COLUMNS = [COL_NAME, COL_REQUEST_COUNT, COL_FAILURE_COUNT,
                    COL_REQUESTS_PER_SEC]


class ThroughputReportAnalyzer:
    """Analyzes Locust load test output to verify throughput NFRs."""

    def analyze(
        self,
        csv_path: str,
        qps_threshold: float = 1000.0,
        error_rate_threshold: float = 0.01,
    ) -> ThroughputVerificationResult:
        """Analyze a Locust stats CSV file against throughput thresholds.

        Args:
            csv_path: Path to the Locust stats CSV file.
            qps_threshold: Minimum acceptable QPS (default 1000.0).
            error_rate_threshold: Maximum acceptable error rate (strict <, default 0.01).

        Returns:
            ThroughputVerificationResult with pass/fail verdict and extracted metrics.

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
            qps = float(agg_row[COL_REQUESTS_PER_SEC])
            total_requests = int(agg_row[COL_REQUEST_COUNT])
            failure_count = int(agg_row[COL_FAILURE_COUNT])
        except KeyError as e:
            raise ValueError(f"malformed CSV: missing column {e}") from e

        error_rate = failure_count / total_requests if total_requests > 0 else 0.0
        passed = (qps >= qps_threshold) and (error_rate < error_rate_threshold)

        return ThroughputVerificationResult(
            passed=passed,
            qps=qps,
            total_requests=total_requests,
            error_rate=error_rate,
            qps_threshold=qps_threshold,
            error_rate_threshold=error_rate_threshold,
        )

    def analyze_from_stats(
        self,
        stats: list[dict],
        qps_threshold: float = 1000.0,
        error_rate_threshold: float = 0.01,
    ) -> ThroughputVerificationResult:
        """Analyze from a list of stats dictionaries.

        Args:
            stats: List of dicts with keys: qps, total_requests, failure_count.
            qps_threshold: Minimum acceptable QPS.
            error_rate_threshold: Maximum acceptable error rate (strict <).

        Returns:
            ThroughputVerificationResult with pass/fail verdict and aggregated metrics.

        Raises:
            ValueError: If stats list is empty.
        """
        if not stats:
            raise ValueError("stats list must not be empty")

        total_qps = 0.0
        total_requests = 0
        total_failures = 0

        for entry in stats:
            total_qps += entry["qps"]
            total_requests += entry["total_requests"]
            total_failures += entry["failure_count"]

        error_rate = total_failures / total_requests if total_requests > 0 else 0.0
        passed = (total_qps >= qps_threshold) and (error_rate < error_rate_threshold)

        return ThroughputVerificationResult(
            passed=passed,
            qps=total_qps,
            total_requests=total_requests,
            error_rate=error_rate,
            qps_threshold=qps_threshold,
            error_rate_threshold=error_rate_threshold,
        )
