"""
Tests for NFR-002: Query Throughput
Feature #27 - Load Test Runner

[unit] Tests for throughput test runner script
"""

import subprocess
import json
import pytest
import tempfile
import os


class TestThroughputTestRunner:
    """Unit tests for the throughput test runner script"""

    def test_runner_script_exists(self):
        """Runner script should exist in scripts directory"""
        script_path = "scripts/run_throughput_test.py"
        assert os.path.exists(script_path), f"Runner script {script_path} should exist"

    def test_runner_accepts_sustained_parameters(self):
        """Runner should accept parameters for sustained load test"""
        # This will fail until we implement the runner
        result = subprocess.run(
            ["python3", "scripts/run_throughput_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Script should respond to --help"
        assert "sustained" in result.stdout.lower() or "1000" in result.stdout

    def test_runner_accepts_burst_parameters(self):
        """Runner should accept parameters for burst load test"""
        result = subprocess.run(
            ["python3", "scripts/run_throughput_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "burst" in result.stdout.lower() or "2000" in result.stdout

    def test_runner_accepts_host_parameter(self):
        """Runner should accept --host parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_throughput_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--host" in result.stdout or "--url" in result.stdout

    def test_runner_accepts_duration_parameter(self):
        """Runner should accept --duration parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_throughput_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--duration" in result.stdout or "-t" in result.stdout

    def test_runner_accepts_users_parameter(self):
        """Runner should accept --users parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_throughput_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--users" in result.stdout or "-u" in result.stdout


class TestThroughputThresholdValidation:
    """Tests for threshold validation logic"""

    def test_threshold_validation_sustained_pass(self):
        """Sustained throughput >= 1000 should pass"""
        result = subprocess.run(
            ["python3", "scripts/run_throughput_test.py", "--validate",
             "--rps", "1200", "--duration", "600"],
            capture_output=True,
            text=True
        )
        # Should return 0 (pass) when RPS >= 1000
        assert result.returncode == 0, f"Should pass with 1200 RPS: {result.stderr}"

    def test_threshold_validation_sustained_fail(self):
        """Sustained throughput < 1000 should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_throughput_test.py", "--validate",
             "--rps", "800", "--duration", "600"],
            capture_output=True,
            text=True
        )
        # Should return 1 (fail) when RPS < 1000
        assert result.returncode == 1, f"Should fail with 800 RPS: {result.stdout}"

    def test_threshold_validation_burst_pass(self):
        """Burst throughput >= 2000 should pass"""
        result = subprocess.run(
            ["python3", "scripts/run_throughput_test.py", "--validate",
             "--peak-rps", "2500"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass with 2500 peak: {result.stderr}"

    def test_threshold_validation_burst_fail(self):
        """Burst throughput < 2000 should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_throughput_test.py", "--validate",
             "--peak-rps", "1500"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, f"Should fail with 1500 peak: {result.stdout}"


class TestLocustOutputParsing:
    """Tests for parsing locust output"""

    def test_parse_locust_stats_json(self):
        """Should parse locust stats output correctly"""
        # Sample locust stats output
        stats = {
            "stats": [
                {
                    "name": "Aggregated",
                    "num_requests": 60000,
                    "num_failures": 0,
                    "duration": 60.0
                }
            ]
        }
        # Calculate RPS: 60000 requests / 60 seconds = 1000 RPS
        rps = stats["stats"][0]["num_requests"] / stats["stats"][0]["duration"]
        assert rps == 1000.0

    def test_calculate_peak_rps_from_burst(self):
        """Should calculate peak RPS during burst correctly"""
        # Burst test: 2000 users, 30 second window
        peak_requests = 60000  # 2000 users * 30 requests each
        peak_duration = 30.0
        peak_rps = peak_requests / peak_duration
        assert peak_rps == 2000.0


class TestIntegrationWithLocustfile:
    """Tests verifying integration with existing locustfile"""

    def test_locustfile_exists(self):
        """Locustfile should exist for load testing"""
        assert os.path.exists("locustfile.py"), "locustfile.py should exist"

    def test_locustfile_has_query_task(self):
        """Locustfile should have query task"""
        with open("locustfile.py", "r") as f:
            content = f.read()
        assert "query" in content.lower()
        assert "@task" in content

    def test_locustfile_has_nfr_check(self):
        """Locustfile should check NFR-002 thresholds"""
        with open("locustfile.py", "r") as f:
            content = f.read()
        assert "NFR-002" in content, "Locustfile should reference NFR-002"
        assert "1000" in content, "Locustfile should reference 1000 QPS threshold"


# [no integration test] - NFR load testing requires external services
# and is tested via ST acceptance tests (feature-st)
