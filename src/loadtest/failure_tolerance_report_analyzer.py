"""Failure tolerance report analyzer — parses JSON failure-tolerance reports and checks NFR-008."""

import json
import os

from src.loadtest.failure_tolerance_verification_result import FailureToleranceVerificationResult

_REQUIRED_KEYS = ("total_requests", "failed_requests", "nodes_killed", "nodes_initial")


class FailureToleranceReportAnalyzer:
    """Analyzes node-failure test reports to verify NFR-008 single-node failure tolerance."""

    def analyze(
        self,
        json_path: str,
        max_allowed_failures: int = 0,
    ) -> FailureToleranceVerificationResult:
        """Analyze a JSON failure-tolerance report.

        Args:
            json_path: Path to the JSON report file.
            max_allowed_failures: Maximum requests that may fail (default 0).

        Returns:
            FailureToleranceVerificationResult with pass/fail verdict and metrics.

        Raises:
            FileNotFoundError: If json_path does not exist.
            ValueError: If JSON is malformed, required keys are absent, or values are negative.
        """
        if not os.path.exists(json_path):
            raise FileNotFoundError(json_path)

        with open(json_path) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                raise ValueError("malformed JSON in report file") from e

        for key in _REQUIRED_KEYS:
            if key not in data:
                raise ValueError(f"missing key: {key}")

        total_requests = data["total_requests"]
        failed_requests = data["failed_requests"]
        nodes_killed = data["nodes_killed"]
        nodes_initial = data["nodes_initial"]

        if total_requests < 0 or failed_requests < 0 or nodes_killed < 0 or nodes_initial < 0:
            raise ValueError("field values must be non-negative")

        return self._compute(
            total_requests, failed_requests, nodes_killed, nodes_initial, max_allowed_failures
        )

    def analyze_from_stats(
        self,
        stats: dict,
        max_allowed_failures: int = 0,
    ) -> FailureToleranceVerificationResult:
        """Analyze from a stats dictionary.

        Args:
            stats: Dict with keys: total_requests, failed_requests, nodes_killed, nodes_initial.
            max_allowed_failures: Maximum requests that may fail (default 0).

        Returns:
            FailureToleranceVerificationResult with pass/fail verdict and metrics.

        Raises:
            ValueError: If stats is missing required keys or has negative values.
        """
        for key in _REQUIRED_KEYS:
            if key not in stats:
                raise ValueError(
                    "stats must contain 'total_requests', 'failed_requests', "
                    "'nodes_killed', 'nodes_initial'"
                )

        total_requests = stats["total_requests"]
        failed_requests = stats["failed_requests"]
        nodes_killed = stats["nodes_killed"]
        nodes_initial = stats["nodes_initial"]

        if total_requests < 0 or failed_requests < 0 or nodes_killed < 0 or nodes_initial < 0:
            raise ValueError("field values must be non-negative")

        return self._compute(
            total_requests, failed_requests, nodes_killed, nodes_initial, max_allowed_failures
        )

    def _compute(
        self,
        total_requests: int,
        failed_requests: int,
        nodes_killed: int,
        nodes_initial: int,
        max_allowed_failures: int,
    ) -> FailureToleranceVerificationResult:
        """Evaluate the four pass conditions and return a result.

        Pass conditions:
            1. nodes_killed >= 1 (at least one node was killed)
            2. nodes_initial > nodes_killed (cluster remains operational)
            3. failed_requests <= max_allowed_failures (within failure tolerance)
            4. total_requests > 0 (load test actually ran)
        """
        cond1 = nodes_killed >= 1
        cond2 = nodes_initial > nodes_killed
        cond3 = failed_requests <= max_allowed_failures
        cond4 = total_requests > 0

        passed = cond1 and cond2 and cond3 and cond4

        return FailureToleranceVerificationResult(
            passed=passed,
            total_requests=total_requests,
            failed_requests=failed_requests,
            nodes_killed=nodes_killed,
            nodes_initial=nodes_initial,
            max_allowed_failures=max_allowed_failures,
        )
