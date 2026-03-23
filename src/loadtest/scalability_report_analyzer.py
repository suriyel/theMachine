"""Scalability report analyzer — compares multi-node Locust runs for NFR-006."""

from src.loadtest.scalability_verification_result import ScalabilityVerificationResult
from src.loadtest.throughput_report_analyzer import ThroughputReportAnalyzer


class ScalabilityReportAnalyzer:
    """Analyzes scalability by comparing baseline and scaled Locust load test runs."""

    def __init__(self) -> None:
        self._throughput_analyzer = ThroughputReportAnalyzer()

    def analyze(
        self,
        baseline_csv_path: str,
        scaled_csv_path: str,
        baseline_nodes: int,
        scaled_nodes: int,
        efficiency_threshold: float = 0.70,
    ) -> ScalabilityVerificationResult:
        """Analyze scalability from two Locust stats CSV files.

        Args:
            baseline_csv_path: Path to the baseline (N-node) Locust stats CSV.
            scaled_csv_path: Path to the scaled (N+1-node) Locust stats CSV.
            baseline_nodes: Number of nodes in the baseline run.
            scaled_nodes: Number of nodes in the scaled run.
            efficiency_threshold: Minimum acceptable scalability efficiency (default 0.70).

        Returns:
            ScalabilityVerificationResult with pass/fail verdict and metrics.

        Raises:
            FileNotFoundError: If either CSV path does not exist.
            ValueError: If CSV is malformed, node counts are invalid, or baseline QPS is zero.
        """
        if baseline_nodes < 1:
            raise ValueError("baseline_nodes must be >= 1")
        if scaled_nodes <= baseline_nodes:
            raise ValueError("scaled_nodes must be > baseline_nodes")

        baseline_result = self._throughput_analyzer.analyze(
            baseline_csv_path, qps_threshold=0.0,
        )
        scaled_result = self._throughput_analyzer.analyze(
            scaled_csv_path, qps_threshold=0.0,
        )

        baseline_qps = baseline_result.qps
        scaled_qps = scaled_result.qps

        if baseline_qps <= 0:
            raise ValueError("baseline QPS must be > 0 for scalability calculation")

        return self._compute(
            baseline_qps, scaled_qps,
            baseline_nodes, scaled_nodes,
            efficiency_threshold,
        )

    def analyze_from_stats(
        self,
        baseline_qps: float,
        scaled_qps: float,
        baseline_nodes: int,
        scaled_nodes: int,
        efficiency_threshold: float = 0.70,
    ) -> ScalabilityVerificationResult:
        """Analyze scalability from raw QPS values.

        Args:
            baseline_qps: QPS measured with baseline node count.
            scaled_qps: QPS measured with scaled node count.
            baseline_nodes: Number of nodes in the baseline run.
            scaled_nodes: Number of nodes in the scaled run.
            efficiency_threshold: Minimum acceptable scalability efficiency (default 0.70).

        Returns:
            ScalabilityVerificationResult with pass/fail verdict and metrics.

        Raises:
            ValueError: If inputs are invalid.
        """
        if baseline_qps <= 0:
            raise ValueError("baseline_qps must be > 0")
        if baseline_nodes < 1:
            raise ValueError("baseline_nodes must be >= 1")
        if scaled_nodes <= baseline_nodes:
            raise ValueError("scaled_nodes must be > baseline_nodes")

        return self._compute(
            baseline_qps, scaled_qps,
            baseline_nodes, scaled_nodes,
            efficiency_threshold,
        )

    def _compute(
        self,
        baseline_qps: float,
        scaled_qps: float,
        baseline_nodes: int,
        scaled_nodes: int,
        efficiency_threshold: float,
    ) -> ScalabilityVerificationResult:
        """Compute scalability efficiency and return the result."""
        per_node_throughput = baseline_qps / baseline_nodes
        added_nodes = scaled_nodes - baseline_nodes
        theoretical_increase = per_node_throughput * added_nodes
        actual_increase = scaled_qps - baseline_qps

        if actual_increase <= 0:
            efficiency = 0.0
        else:
            efficiency = actual_increase / theoretical_increase

        passed = efficiency >= efficiency_threshold

        return ScalabilityVerificationResult(
            passed=passed,
            efficiency=efficiency,
            baseline_qps=baseline_qps,
            scaled_qps=scaled_qps,
            baseline_nodes=baseline_nodes,
            scaled_nodes=scaled_nodes,
            efficiency_threshold=efficiency_threshold,
        )
