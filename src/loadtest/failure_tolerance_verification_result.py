"""Verification result dataclass for NFR-008 single-node failure tolerance checks."""

from dataclasses import dataclass


@dataclass
class FailureToleranceVerificationResult:
    """Result of a single-node failure tolerance verification check."""

    passed: bool
    total_requests: int
    failed_requests: int
    nodes_killed: int
    nodes_initial: int
    max_allowed_failures: int

    def summary(self) -> str:
        """Return a human-readable summary of the verification result."""
        verdict = "PASS" if self.passed else "FAIL"
        return (
            f"NFR-008: {verdict} — "
            f"nodes_killed={self.nodes_killed}/{self.nodes_initial} initial, "
            f"failed={self.failed_requests} "
            f"(max_allowed={self.max_allowed_failures}), "
            f"total_requests={self.total_requests}"
        )
