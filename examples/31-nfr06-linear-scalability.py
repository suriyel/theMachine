#!/usr/bin/env python3
"""
NFR-006: Linear Scalability Test Example

Demonstrates the scalability test runner script functionality.
This script validates that the system achieves linear horizontal scaling
(80-120% per-node capacity increase).

Usage:
    python examples/31-nfr06-linear-scalability.py

This validates the threshold logic used by the scalability test runner.
"""

import subprocess
import sys


def main():
    print("=" * 60)
    print("NFR-006: Linear Scalability Test Example")
    print("=" * 60)
    print()

    # Test 1: Show help
    print("1. Running scalability test script --help...")
    result = subprocess.run(
        ["python3", "scripts/run_scalability_test.py", "--help"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   ✓ Help command works")
    else:
        print("   ✗ Help command failed")
        return 1

    # Test 2: 100% scaling - should pass
    print()
    print("2. Testing 100% linear scaling (1 to 2 nodes)...")
    result = subprocess.run(
        ["python3", "scripts/run_scalability_test.py", "--validate",
         "--nodes", "1", "--throughput", "1000",
         "--nodes1", "2", "--throughput1", "2000"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   ✓ 1→2 nodes: 1000→2000 QPS PASSES (100%)")
    else:
        print("   ✗ Should have passed")
        return 1

    # Test 3: 80% scaling (boundary) - should pass
    print()
    print("3. Testing 80% scaling (boundary)...")
    result = subprocess.run(
        ["python3", "scripts/run_scalability_test.py", "--validate",
         "--nodes", "1", "--throughput", "1000",
         "--nodes1", "2", "--throughput1", "1800"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   ✓ 1→2 nodes: 1000→1800 QPS PASSES (80%)")
    else:
        print("   ✗ Should have passed at 80% boundary")
        return 1

    # Test 4: 120% scaling (boundary) - should pass
    print()
    print("4. Testing 120% scaling (boundary)...")
    result = subprocess.run(
        ["python3", "scripts/run_scalability_test.py", "--validate",
         "--nodes", "1", "--throughput", "1000",
         "--nodes1", "2", "--throughput1", "2200"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   ✓ 1→2 nodes: 1000→2200 QPS PASSES (120%)")
    else:
        print("   ✗ Should have passed at 120% boundary")
        return 1

    # Test 5: 79% scaling - should fail
    print()
    print("5. Testing 79% scaling (below threshold)...")
    result = subprocess.run(
        ["python3", "scripts/run_scalability_test.py", "--validate",
         "--nodes", "1", "--throughput", "1000",
         "--nodes1", "2", "--throughput1", "1790"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   ✓ 1→2 nodes: 1000→1790 QPS FAILS (79% < 80%)")
    else:
        print("   ✗ Should have failed")
        return 1

    # Test 6: 121% scaling - should fail
    print()
    print("6. Testing 121% scaling (above threshold)...")
    result = subprocess.run(
        ["python3", "scripts/run_scalability_test.py", "--validate",
         "--nodes", "1", "--throughput", "1000",
         "--nodes1", "2", "--throughput1", "2210"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   ✓ 1→2 nodes: 1000→2210 QPS FAILS (121% > 120%)")
    else:
        print("   ✗ Should have failed")
        return 1

    # Test 7: 3 to 4 nodes - should pass
    print()
    print("7. Testing 3 to 4 nodes scaling...")
    result = subprocess.run(
        ["python3", "scripts/run_scalability_test.py", "--validate",
         "--nodes", "3", "--throughput", "3000",
         "--nodes1", "4", "--throughput1", "4000"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   ✓ 3→4 nodes: 3000→4000 QPS PASSES (100%)")
    else:
        print("   ✗ Should have passed")
        return 1

    # Test 8: Custom thresholds - should pass
    print()
    print("8. Testing custom thresholds...")
    result = subprocess.run(
        ["python3", "scripts/run_scalability_test.py", "--validate",
         "--nodes", "1", "--throughput", "1000",
         "--nodes1", "2", "--throughput1", "1500",
         "--threshold-min", "40", "--threshold-max", "160"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   ✓ Custom threshold 40-160% with 50% gain PASSES")
    else:
        print("   ✗ Should have passed")
        return 1

    # Test 9: Input validation - nodes1 <= nodes
    print()
    print("9. Testing input validation (nodes1 <= nodes)...")
    result = subprocess.run(
        ["python3", "scripts/run_scalability_test.py", "--validate",
         "--nodes", "2", "--throughput", "2000",
         "--nodes1", "2", "--throughput1", "2500"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   ✓ nodes1 <= nodes rejected")
    else:
        print("   ✗ Should have failed")
        return 1

    print()
    print("=" * 60)
    print("All scalability validation tests PASSED!")
    print("=" * 60)
    print()
    print("Summary:")
    print("  - Scaling threshold: 80-120%")
    print("  - Formula: (throughput_N1 - throughput_N) / per_node_capacity")
    print("  - 1→2 nodes: 1000→2000 QPS = 100% (pass)")
    print("  - 1→2 nodes: 1000→1800 QPS = 80% (pass)")
    print("  - 1→2 nodes: 1000→2200 QPS = 120% (pass)")
    print()
    print("Note: Full scalability test requires running services with")
    print("multiple query nodes and load testing infrastructure.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
