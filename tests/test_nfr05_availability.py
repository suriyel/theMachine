"""
NFR-005: Service Availability Tests

Tests for service availability test runner script - validates system can
achieve 99.9% uptime target (<= 8.76 hours downtime per year).

[unit] — script subprocess tests
"""

import subprocess
import pytest
import os


class TestAvailabilityTestRunner:
    """Unit tests for the service availability test runner script"""

    def test_runner_script_exists(self):
        """Runner script should exist in scripts directory"""
        script_path = "scripts/run_availability_test.py"
        assert os.path.exists(script_path), f"Runner script {script_path} should exist"

    def test_runner_accepts_help(self):
        """Runner should respond to --help"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Script should respond to --help"

    def test_runner_documents_nfr005(self):
        """Runner should document NFR-005 thresholds"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "NFR-005" in result.stdout, "Script should reference NFR-005"
        assert "99.9" in result.stdout, "Script should reference 99.9% threshold"

    def test_runner_accepts_host_parameter(self):
        """Runner should accept --host parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--host" in result.stdout, "Script should accept --host"

    def test_runner_accepts_validate_parameter(self):
        """Runner should accept --validate parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--validate" in result.stdout, "Script should accept --validate"

    def test_runner_accepts_interval_parameter(self):
        """Runner should accept --interval parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--interval" in result.stdout, "Script should accept --interval"

    def test_runner_accepts_duration_parameter(self):
        """Runner should accept --duration parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--duration" in result.stdout, "Script should accept --duration"

    def test_runner_accepts_monitor_parameter(self):
        """Runner should accept --monitor parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--monitor" in result.stdout, "Script should accept --monitor"

    def test_runner_accepts_threshold_parameter(self):
        """Runner should accept --threshold parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--threshold" in result.stdout, "Script should accept --threshold"

    def test_runner_accepts_checks_parameter(self):
        """Runner should accept --checks parameter for validation"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--checks" in result.stdout, "Script should accept --checks parameter"


class TestAvailabilityThresholdValidation:
    """Tests for availability threshold validation logic"""

    def test_validate_100_percent_uptime_pass(self):
        """100% uptime should pass"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--validate",
             "--checks", "1000", "--successful", "1000"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass with 100% uptime: {result.stderr}"
        assert "PASS" in result.stdout or "pass" in result.stdout.lower()

    def test_validate_99_9_percent_uptime_pass(self):
        """99.9% uptime should pass (boundary)"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--validate",
             "--checks", "1000", "--successful", "999"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass at 99.9% boundary: {result.stderr}"
        assert "PASS" in result.stdout or "pass" in result.stdout.lower()

    def test_validate_99_89_percent_uptime_fail(self):
        """99.89% uptime should fail (just below threshold)"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--validate",
             "--checks", "1000", "--successful", "998"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, f"Should fail at 99.8%: {result.stdout}"
        assert "FAIL" in result.stdout or "fail" in result.stdout.lower()

    def test_validate_95_percent_uptime_fail(self):
        """95% uptime should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--validate",
             "--checks", "1000", "--successful", "950"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, f"Should fail at 95%: {result.stdout}"
        assert "FAIL" in result.stdout or "fail" in result.stdout.lower()

    def test_validate_zero_checks_fail(self):
        """Zero total checks should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--validate",
             "--checks", "0", "--successful", "0"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail with zero checks"

    def test_validate_negative_checks_fail(self):
        """Negative total checks should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--validate",
             "--checks", "-100", "--successful", "100"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail with negative checks"

    def test_validate_negative_successful_fail(self):
        """Negative successful checks should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--validate",
             "--checks", "100", "--successful", "-50"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail with negative successful"

    def test_validate_successful_greater_than_total_fail(self):
        """Successful checks > total checks should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--validate",
             "--checks", "100", "--successful", "150"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail when successful > total"

    def test_validate_missing_checks_fail(self):
        """Missing --checks should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--validate",
             "--successful", "1000"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail without --checks"

    def test_validate_missing_successful_fail(self):
        """Missing --successful should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--validate",
             "--checks", "1000"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail without --successful"

    def test_validate_custom_threshold_pass(self):
        """Custom threshold (95%) should work"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--validate",
             "--checks", "100", "--successful", "96", "--threshold", "95"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass at 96% with 95% threshold: {result.stderr}"

    def test_validate_custom_threshold_fail(self):
        """Custom threshold (99%) should fail at 95%"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--validate",
             "--checks", "100", "--successful", "95", "--threshold", "99"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, f"Should fail at 95% with 99% threshold: {result.stdout}"


class TestAvailabilityCalculation:
    """Tests for uptime percentage calculation"""

    def test_calculate_uptime_percentage(self):
        """Uptime percentage calculation should be correct"""
        # 999/1000 = 99.9%
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--validate",
             "--checks", "1000", "--successful", "999"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        # Should output the calculated percentage
        assert "99.9" in result.stdout or "99.89" in result.stdout

    def test_small_sample_size(self):
        """Should handle small sample sizes correctly"""
        # 10/10 = 100%
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--validate",
             "--checks", "10", "--successful", "10"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass with small sample: {result.stderr}"

    def test_one_failure_in_1000(self):
        """1 failure in 1000 checks should pass (99.9%)"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--validate",
             "--checks", "1000", "--successful", "999"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_two_failures_in_1000(self):
        """2 failures in 1000 checks should fail (99.8%)"""
        result = subprocess.run(
            ["python3", "scripts/run_availability_test.py", "--validate",
             "--checks", "1000", "--successful", "998"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1


# [no integration test] - NFR availability testing requires external services
# and is tested via ST acceptance tests
