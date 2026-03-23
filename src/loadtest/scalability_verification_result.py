"""Verification result dataclass for NFR-006 scalability checks."""

from dataclasses import dataclass


@dataclass
class ScalabilityVerificationResult:
    """Result of a scalability threshold verification check."""

    passed: bool
    efficiency: float
    baseline_qps: float
    scaled_qps: float
    baseline_nodes: int
    scaled_nodes: int
    efficiency_threshold: float

    def summary(self) -> str:
        """Return a human-readable summary of the verification result."""
        verdict = "PASS" if self.passed else "FAIL"
        return (
            f"NFR-006: {verdict} — "
            f"efficiency={self.efficiency:.2%} "
            f"(threshold={self.efficiency_threshold:.2%}), "
            f"baseline_qps={self.baseline_qps:.1f} ({self.baseline_nodes} nodes), "
            f"scaled_qps={self.scaled_qps:.1f} ({self.scaled_nodes} nodes)"
        )
