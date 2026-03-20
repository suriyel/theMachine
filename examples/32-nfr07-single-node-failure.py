#!/usr/bin/env python3
"""
NFR-007: Single-Node Failure Tolerance Test Example

Demonstrates the failover test runner script functionality.
This script validates that the system tolerates single-node failure
with zero query failures and failover <= 30 seconds.

Usage:
    python examples/32-nfr07-single-node-failure.py

This validates the threshold logic used by the failover test runner.
"""

import subprocess
import sys


def main():
    print("=" * 60)
    print("NFR-007: Single-Node Failure Tolerance Test Example")
    print("=" * 60)
    print()

    # Test 1: Show help
    print("1. Running failover test script --help...")
    result = subprocess.run(
        ["python3", "scripts/run_failover_test.py", "--help"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   - Help command works")
    else:
        print("   - Help command failed")
        return 1

    # Test 2: Zero failures with fast failover - should pass
    print()
    print("2. Testing zero failures with 5s failover (should PASS)...")
    result = subprocess.run(
        ["python3", "scripts/run_failover_test.py", "--validate",
         "--queries", "1000", "--failures", "0", "--failover-time", "5"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   - Zero failures + 5s failover: PASS")
    else:
        print("   - Should have passed")
        return 1

    # Test 3: Zero failures with 30s failover (boundary) - should pass
    print()
    print("3. Testing zero failures with 30s failover (boundary)...")
    result = subprocess.run(
        ["python3", "scripts/run_failover_test.py", "--validate",
         "--queries", "1000", "--failures", "0", "--failover-time", "30"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   - Zero failures + 30s failover: PASS")
    else:
        print("   - Should have passed at 30s boundary")
        return 1

    # Test 4: One failure - should fail
    print()
    print("4. Testing one failure (should FAIL - zero tolerance)...")
    result = subprocess.run(
        ["python3", "scripts/run_failover_test.py", "--validate",
         "--queries", "1000", "--failures", "1", "--failover-time", "5"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   - 1 failure: FAIL (correct - zero tolerance)")
    else:
        print("   - Should have failed")
        return 1

    # Test 5: Multiple failures - should fail
    print()
    print("5. Testing multiple failures (should FAIL)...")
    result = subprocess.run(
        ["python3", "scripts/run_failover_test.py", "--validate",
         "--queries", "1000", "--failures", "100", "--failover-time", "5"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   - 100 failures: FAIL (correct)")
    else:
        print("   - Should have failed")
        return 1

    # Test 6: 31s failover - should fail
    print()
    print("6. Testing 31s failover (should FAIL - exceeds 30s threshold)...")
    result = subprocess.run(
        ["python3", "scripts/run_failover_test.py", "--validate",
         "--queries", "1000", "--failures", "0", "--failover-time", "31"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   - 31s failover: FAIL (correct - exceeds 30s)")
    else:
        print("   - Should have failed")
        return 1

    # Test 7: 60s failover - should fail
    print()
    print("7. Testing 60s failover (should FAIL)...")
    result = subprocess.run(
        ["python3", "scripts/run_failover_test.py", "--validate",
         "--queries", "1000", "--failures", "0", "--failover-time", "60"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   - 60s failover: FAIL (correct)")
    else:
        print("   - Should have failed")
        return 1

    # Test 8: Zero queries - should fail
    print()
    print("8. Testing zero queries (should FAIL)...")
    result = subprocess.run(
        ["python3", "scripts/run_failover_test.py", "--validate",
         "--queries", "0", "--failures", "0", "--failover-time", "5"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   - Zero queries: FAIL (correct)")
    else:
        print("   - Should have failed")
        return 1

    # Test 9: Negative failures - should fail
    print()
    print("9. Testing negative failures (should FAIL)...")
    result = subprocess.run(
        ["python3", "scripts/run_failover_test.py", "--validate",
         "--queries", "1000", "--failures", "-1", "--failover-time", "5"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   - Negative failures: FAIL (correct)")
    else:
        print("   - Should have failed")
        return 1

    # Test 10: Failures > queries - should fail
    print()
    print("10. Testing failures > queries (should FAIL)...")
    result = subprocess.run(
        ["python3", "scripts/run_failover_test.py", "--validate",
         "--queries", "100", "--failures", "200", "--failover-time", "5"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   - Failures > queries: FAIL (correct)")
    else:
        print("   - Should have failed")
        return 1

    # Test 11: Missing params - should fail
    print()
    print("11. Testing missing parameters (should FAIL)...")
    result = subprocess.run(
        ["python3", "scripts/run_failover_test.py", "--validate",
         "--queries", "1000"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   - Missing params: FAIL (correct)")
    else:
        print("   - Should have failed")
        return 1

    # Test 12: Custom max failures - should pass
    print()
    print("12. Testing custom max failures (should PASS)...")
    result = subprocess.run(
        ["python3", "scripts/run_failover_test.py", "--validate",
         "--queries", "100", "--failures", "5", "--failover-time", "5",
         "--max-failures", "10"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   - 5 failures with max-failures=10: PASS")
    else:
        print("   - Should have passed")
        return 1

    print()
    print("=" * 60)
    print("All failover validation tests PASSED!")
    print("=" * 60)
    print()
    print("Summary:")
    print("  - Failure threshold: 0 (zero tolerance)")
    print("  - Failover time threshold: 30 seconds")
    print("  - Zero failures + 5s failover: PASS")
    print("  - Zero failures + 30s failover: PASS (boundary)")
    print("  - 1+ failures: FAIL (zero tolerance)")
    print("  - 31s+ failover: FAIL (> 30s)")
    print()
    print("Note: Full failover test requires running services with")
    print("multiple query nodes, a load balancer, and chaos testing.")
    print("The test runner validates threshold logic using pre-collected metrics.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
