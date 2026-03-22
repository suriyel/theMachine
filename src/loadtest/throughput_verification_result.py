"""Verification result dataclass for NFR-002 throughput checks."""

from dataclasses import dataclass


@dataclass
class ThroughputVerificationResult:
    """Result of a throughput threshold verification check."""

    passed: bool
    qps: float
    total_requests: int
    error_rate: float
    qps_threshold: float
    error_rate_threshold: float

    def summary(self) -> str:
        """Return a human-readable summary of the verification result."""
        verdict = "PASS" if self.passed else "FAIL"
        return (
            f"NFR-002: {verdict} — "
            f"qps={self.qps:.1f} (threshold={self.qps_threshold:.1f}), "
            f"error_rate={self.error_rate:.4f} (max={self.error_rate_threshold:.4f}), "
            f"requests={self.total_requests}"
        )
