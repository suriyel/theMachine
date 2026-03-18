"""
NFR-006: Linear Scalability Tests

Tests for linear scalability test runner script - validates system achieves
linear horizontal scaling (±20%).

[unit] — script subprocess tests
"""

import subprocess
import pytest
import os


class TestScalabilityTestRunner:
    """Unit tests for the linear scalability test runner script"""

    def test_runner_script_exists(self):
        """Runner script should exist in scripts directory"""
        script_path = "scripts/run_scalability_test.py"
        assert os.path.exists(script_path), f"Runner script {script_path} should exist"

    def test_runner_accepts_help(self):
        """Runner should respond to --help"""
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Script should respond to --help"

    def test_runner_documents_nfr006(self):
        """Runner should document NFR-006 thresholds"""
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "NFR-006" in result.stdout, "Script should reference NFR-006"
        assert "80" in result.stdout and "120" in result.stdout, "Script should reference 80-120% range"

    def test_runner_accepts_validate_parameter(self):
        """Runner should accept --validate parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--validate" in result.stdout, "Script should accept --validate"

    def test_runner_accepts_nodes_parameter(self):
        """Runner should accept --nodes parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--nodes" in result.stdout, "Script should accept --nodes"

    def test_runner_accepts_throughput_parameter(self):
        """Runner should accept --throughput parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--throughput" in result.stdout, "Script should accept --throughput"

    def test_runner_accepts_nodes1_parameter(self):
        """Runner should accept --nodes1 parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--nodes1" in result.stdout, "Script should accept --nodes1"

    def test_runner_accepts_throughput1_parameter(self):
        """Runner should accept --throughput1 parameter"""
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--throughput1" in result.stdout, "Script should accept --throughput1"

    def test_runner_accepts_threshold_parameters(self):
        """Runner should accept threshold parameters"""
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--help"],
            capture_output=True,
            text=True
        )
        assert "--threshold-min" in result.stdout, "Script should accept --threshold-min"
        assert "--threshold-max" in result.stdout, "Script should accept --threshold-max"


class TestScalabilityThresholdValidation:
    """Tests for scalability threshold validation logic"""

    def test_validate_100_percent_scaling_pass(self):
        """100% linear scaling should pass"""
        # 1 node: 1000 QPS, 2 nodes: 2000 QPS = 100% gain
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--validate",
             "--nodes", "1", "--throughput", "1000",
             "--nodes1", "2", "--throughput1", "2000"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass with 100% scaling: {result.stderr}"
        assert "PASS" in result.stdout or "pass" in result.stdout.lower()

    def test_validate_80_percent_scaling_pass(self):
        """80% scaling (at boundary) should pass"""
        # 1 node: 1000 QPS, 2 nodes: 1800 QPS = 80% gain
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--validate",
             "--nodes", "1", "--throughput", "1000",
             "--nodes1", "2", "--throughput1", "1800"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass at 80% boundary: {result.stderr}"

    def test_validate_120_percent_scaling_pass(self):
        """120% scaling (at boundary) should pass"""
        # 1 node: 1000 QPS, 2 nodes: 2200 QPS = 120% gain
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--validate",
             "--nodes", "1", "--throughput", "1000",
             "--nodes1", "2", "--throughput1", "2200"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass at 120% boundary: {result.stderr}"

    def test_validate_79_percent_scaling_fail(self):
        """79% scaling should fail"""
        # 1 node: 1000 QPS, 2 nodes: 1790 QPS = 79% gain
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--validate",
             "--nodes", "1", "--throughput", "1000",
             "--nodes1", "2", "--throughput1", "1790"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, f"Should fail at 79%: {result.stdout}"
        assert "FAIL" in result.stdout or "fail" in result.stdout.lower()

    def test_validate_121_percent_scaling_fail(self):
        """121% scaling should fail"""
        # 1 node: 1000 QPS, 2 nodes: 2210 QPS = 121% gain
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--validate",
             "--nodes", "1", "--throughput", "1000",
             "--nodes1", "2", "--throughput1", "2210"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, f"Should fail at 121%: {result.stdout}"

    def test_validate_50_percent_scaling_fail(self):
        """50% scaling should fail"""
        # 1 node: 1000 QPS, 2 nodes: 1500 QPS = 50% gain
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--validate",
             "--nodes", "1", "--throughput", "1000",
             "--nodes1", "2", "--throughput1", "1500"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, f"Should fail at 50%: {result.stdout}"

    def test_validate_3_nodes_scaling_pass(self):
        """Scaling from 2 to 3 nodes at 100% should pass"""
        # 2 nodes: 2000 QPS (1000 QPS/node), 3 nodes: 3000 QPS = 100% gain
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--validate",
             "--nodes", "2", "--throughput", "2000",
             "--nodes1", "3", "--throughput1", "3000"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass with 3 nodes: {result.stderr}"

    def test_validate_4_nodes_scaling_pass(self):
        """Scaling from 3 to 4 nodes at 100% should pass"""
        # 3 nodes: 3000 QPS (1000 QPS/node), 4 nodes: 4000 QPS = 100% gain
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--validate",
             "--nodes", "3", "--throughput", "3000",
             "--nodes1", "4", "--throughput1", "4000"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass with 4 nodes: {result.stderr}"

    def test_validate_negative_nodes_fail(self):
        """Negative node count should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--validate",
             "--nodes", "-1", "--throughput", "1000",
             "--nodes1", "1", "--throughput1", "1000"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail with negative nodes"

    def test_validate_zero_throughput_fail(self):
        """Zero throughput should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--validate",
             "--nodes", "1", "--throughput", "0",
             "--nodes1", "2", "--throughput1", "1000"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail with zero throughput"

    def test_validate_nodes1_not_greater_than_nodes_fail(self):
        """nodes1 must be greater than nodes"""
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--validate",
             "--nodes", "2", "--throughput", "2000",
             "--nodes1", "2", "--throughput1", "2500"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail when nodes1 <= nodes"

    def test_validate_custom_threshold_pass(self):
        """Custom threshold (60-140%) should work"""
        # 1 node: 1000 QPS, 2 nodes: 1500 QPS = 50% gain
        # With custom threshold 40-160%, this should pass
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--validate",
             "--nodes", "1", "--throughput", "1000",
             "--nodes1", "2", "--throughput1", "1500",
             "--threshold-min", "40", "--threshold-max", "160"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, f"Should pass with custom threshold: {result.stderr}"

    def test_validate_missing_params_fail(self):
        """Missing required parameters should fail"""
        result = subprocess.run(
            ["python3", "scripts/run_scalability_test.py", "--validate",
             "--nodes", "1"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 1, "Should fail with missing params"


# [no integration test] - NFR scalability testing requires external services
# and is tested via ST acceptance tests
