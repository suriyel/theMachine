"""
NFR-007: Single-Node Failure Tolerance Tests

Tests for failover test runner script - validates system tolerates single-node failure
with zero query failures and failover <= 30 seconds.

[unit] — script subprocess tests
"""

import subprocess
import os


class TestFailoverTestRunner:
    """Unit tests for the failover test runner script"""

    def test_runner_script_exists(self):
        """Runner script should exist in scripts directory"""
        script_path = "scripts/run_failover_test.py"
        assert os.path.exists(script_path), f"Runner script {script_path} should exist"

    def test_runner_accepts_help(self):
        """Runner should respond to --help"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Script should respond to --help"

    def test_runner_documents_nfr007(self):
        """Runner should document NFR-007 thresholds"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "NFR-007" in result.stdout, "Script should reference NFR-007"
        assert "30" in result.stdout, "Script should reference 30 second threshold"

    def test_runner_accepts_validate_parameter(self):
        """Runner should accept --validate parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--validate" in result.stdout, "Script should accept --validate"

    def test_runner_accepts_queries_parameter(self):
        """Runner should accept --queries parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--queries" in result.stdout, "Script should accept --queries"

    def test_runner_accepts_failures_parameter(self):
        """Runner should accept --failures parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--failures" in result.stdout, "Script should accept --failures"

    def test_runner_accepts_failover_time_parameter(self):
        """Runner should accept --failover-time parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--failover-time" in result.stdout, "Script should accept --failover-time"

    def test_runner_accepts_max_parameters(self):
        """Runner should accept max thresholds"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--max-failures" in result.stdout, "Script should accept --max-failures"
        assert "--max-time" in result.stdout, "Script should accept --max-time"


class TestFailoverThresholdValidation:
    """Tests for failover threshold validation logic"""

    def test_validate_zero_failures_fast_failover_pass(self):
        """Zero failures with fast failover should pass"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--validate",
             "--queries", "1000", "--failures", "0", "--failover-time", "5"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass: {result.stderr}"
        assert "PASS" in result.stdout

    def test_validate_zero_failures_30s_failover_pass(self):
        """Zero failures with 30s failover (boundary) should pass"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--validate",
             "--queries", "1000", "--failures", "0", "--failover-time", "30"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass at 30s boundary: {result.stderr}"

    def test_validate_one_failure_fail(self):
        """One failure should fail (zero tolerance)"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--validate",
             "--queries", "1000", "--failures", "1", "--failover-time", "5"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, f"Should fail with 1 failure: {result.stdout}"
        assert "FAIL" in result.stdout

    def test_validate_multiple_failures_fail(self):
        """Multiple failures should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--validate",
             "--queries", "1000", "--failures", "100", "--failover-time", "5"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, f"Should fail with multiple failures: {result.stdout}"

    def test_validate_31s_failover_fail(self):
        """31s failover should fail (exceeds 30s threshold)"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--validate",
             "--queries", "1000", "--failures", "0", "--failover-time", "31"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, f"Should fail at 31s: {result.stdout}"

    def test_validate_60s_failover_fail(self):
        """60s failover should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--validate",
             "--queries", "1000", "--failures", "0", "--failover-time", "60"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, f"Should fail at 60s: {result.stdout}"

    def test_validate_zero_queries_fail(self):
        """Zero queries should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--validate",
             "--queries", "0", "--failures", "0", "--failover-time", "5"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail with zero queries"

    def test_validate_negative_failures_fail(self):
        """Negative failures should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--validate",
             "--queries", "1000", "--failures", "-1", "--failover-time", "5"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail with negative failures"

    def test_validate_negative_failover_time_fail(self):
        """Negative failover time should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--validate",
             "--queries", "1000", "--failures", "0", "--failover-time", "-5"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail with negative failover time"

    def test_validate_failures_greater_than_queries_fail(self):
        """Failures > queries should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--validate",
             "--queries", "100", "--failures", "200", "--failover-time", "5"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail when failures > queries"

    def test_validate_missing_params_fail(self):
        """Missing parameters should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--validate",
             "--queries", "1000"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail with missing params"

    def test_validate_custom_max_failures_pass(self):
        """Custom max failures should work"""
        result = subprocess.run(
            ["python3", "scripts/run_failover_test.py", "--validate",
             "--queries", "100", "--failures", "5", "--failover-time", "5",
             "--max-failures", "10"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass with custom max failures: {result.stderr}"


# [no integration test] - NFR failover testing requires external services
