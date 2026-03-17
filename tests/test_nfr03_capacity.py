"""
NFR-003: Repository Capacity Tests

Tests for capacity test runner script - validates system can handle
100-1000 repositories while maintaining latency within NFR-001 bounds.

[unit] — script subprocess tests
"""

import subprocess
import pytest
import os


class TestCapacityTestRunner:
    """Unit tests for the capacity test runner script"""

    def test_runner_script_exists(self):
        """Runner script should exist in scripts directory"""
        script_path = "scripts/run_capacity_test.py"
        assert os.path.exists(script_path), f"Runner script {script_path} should exist"

    def test_runner_accepts_help(self):
        """Runner should respond to --help"""
        result = subprocess.run(
            ["python3", "scripts/run_capacity_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Script should respond to --help"

    def test_runner_documents_nfr003(self):
        """Runner should document NFR-003 thresholds"""
        result = subprocess.run(
            ["python3", "scripts/run_capacity_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "NFR-003" in result.stdout, "Script should reference NFR-003"
        assert "1000" in result.stdout, "Script should reference 1000 repos"

    def test_runner_accepts_host_parameter(self):
        """Runner should accept --host parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_capacity_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--host" in result.stdout, "Script should accept --host"

    def test_runner_accepts_validate_parameter(self):
        """Runner should accept --validate parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_capacity_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--validate" in result.stdout, "Script should accept --validate"


class TestCapacityThresholdValidation:
    """Tests for threshold validation logic"""

    def test_validate_repos_min_pass(self):
        """100 repositories should pass"""
        result = subprocess.run(
            ["python3", "scripts/run_capacity_test.py", "--validate",
             "--repos", "100", "--latency", "500"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass with 100 repos: {result.stderr}"

    def test_validate_repos_max_pass(self):
        """1000 repositories should pass"""
        result = subprocess.run(
            ["python3", "scripts/run_capacity_test.py", "--validate",
             "--repos", "1000", "--latency", "800"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass with 1000 repos: {result.stderr}"

    def test_validate_latency_at_threshold(self):
        """Latency at 1000ms should pass (meets NFR-001)"""
        result = subprocess.run(
            ["python3", "scripts/run_capacity_test.py", "--validate",
             "--repos", "500", "--latency", "1000"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass at threshold: {result.stderr}"
        assert "PASS" in result.stdout or "pass" in result.stdout.lower()

    def test_validate_latency_under_threshold(self):
        """Latency under 1000ms should pass"""
        result = subprocess.run(
            ["python3", "scripts/run_capacity_test.py", "--validate",
             "--repos", "500", "--latency", "500"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass under threshold: {result.stderr}"

    def test_validate_latency_over_threshold(self):
        """Latency over 1000ms should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_capacity_test.py", "--validate",
             "--repos", "500", "--latency", "1500"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, f"Should fail over threshold: {result.stdout}"
        assert "FAIL" in result.stdout or "fail" in result.stdout.lower()

    def test_validate_repos_below_min(self):
        """Under 100 repositories should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_capacity_test.py", "--validate",
             "--repos", "50", "--latency", "500"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, f"Should fail under 100 repos: {result.stdout}"

    def test_validate_repos_above_max(self):
        """Over 1000 repositories should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_capacity_test.py", "--validate",
             "--repos", "1500", "--latency", "500"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, f"Should fail over 1000 repos: {result.stdout}"

    def test_validate_missing_repos(self):
        """Missing --repos should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_capacity_test.py", "--validate",
             "--latency", "500"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail without --repos"

    def test_validate_missing_latency(self):
        """Missing --latency should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_capacity_test.py", "--validate",
             "--repos", "500"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail without --latency"


class TestScalePoints:
    """Tests for progressive scale points"""

    def test_runner_documents_scale_points(self):
        """Runner should document progressive scale points"""
        result = subprocess.run(
            ["python3", "scripts/run_capacity_test.py", "--help"],
            capture_output=True,
            text=True
        )
        # Should mention progressive testing or scale points
        assert "100" in result.stdout, "Should mention 100 repos"
        assert "250" in result.stdout or "progressive" in result.stdout.lower()


# [no integration test] - NFR capacity testing requires external services
# and is tested via ST acceptance tests
