#!/usr/bin/env python3
"""
NFR-005: Service Availability Test Example

Demonstrates the availability test runner script functionality.
This script validates that the system can achieve 99.9% uptime target
(<= 8.76 hours downtime per year).

Usage:
    python examples/30-nfr05-service-availability.py

This validates the threshold logic used by the availability test runner.
"""

import subprocess
import sys


def main():
    print("=" * 60)
    print("NFR-005: Service Availability Test Example")
    print("=" * 60)
    print()

    # Test 1: Show help
    print("1. Running availability test script --help...")
    result = subprocess.run(
        ["python3", "scripts/run_availability_test.py", "--help"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   ✓ Help command works")
    else:
        print("   ✗ Help command failed")
        return 1

    # Test 2: 100% uptime - should pass
    print()
    print("2. Testing 100% uptime...")
    result = subprocess.run(
        ["python3", "scripts/run_availability_test.py", "--validate",
         "--checks", "1000", "--successful", "1000"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   ✓ 1000/1000 checks PASSES (100%)")
    else:
        print("   ✗ Should have passed")
        print(result.stdout)
        return 1

    # Test 3: 99.9% uptime (boundary) - should pass
    print()
    print("3. Testing 99.9% uptime (boundary)...")
    result = subprocess.run(
        ["python3", "scripts/run_availability_test.py", "--validate",
         "--checks", "1000", "--successful", "999"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   ✓ 999/1000 checks PASSES (99.9% - at boundary)")
    else:
        print("   ✗ Should have passed at boundary")
        print(result.stdout)
        return 1

    # Test 4: 99.89% uptime - should fail
    print()
    print("4. Testing 99.89% uptime (just below threshold)...")
    result = subprocess.run(
        ["python3", "scripts/run_availability_test.py", "--validate",
         "--checks", "1000", "--successful", "998"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   ✓ 998/1000 checks FAILS (99.8% < 99.9%)")
    else:
        print("   ✗ Should have failed")
        return 1

    # Test 5: 95% uptime - should fail
    print()
    print("5. Testing 95% uptime...")
    result = subprocess.run(
        ["python3", "scripts/run_availability_test.py", "--validate",
         "--checks", "1000", "--successful", "950"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   ✓ 950/1000 checks FAILS (95% < 99.9%)")
    else:
        print("   ✗ Should have failed")
        return 1

    # Test 6: Custom threshold - 95% with 90% threshold
    print()
    print("6. Testing custom threshold...")
    result = subprocess.run(
        ["python3", "scripts/run_availability_test.py", "--validate",
         "--checks", "100", "--successful", "96", "--threshold", "95"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   ✓ 96% uptime with 95% threshold PASSES")
    else:
        print("   ✗ Should have passed")
        return 1

    # Test 7: Small sample size
    print()
    print("7. Testing small sample size...")
    result = subprocess.run(
        ["python3", "scripts/run_availability_test.py", "--validate",
         "--checks", "10", "--successful", "10"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   ✓ 10/10 checks PASSES (small sample)")
    else:
        print("   ✗ Should have passed")
        return 1

    # Test 8: Input validation - negative checks
    print()
    print("8. Testing input validation (negative checks)...")
    result = subprocess.run(
        ["python3", "scripts/run_availability_test.py", "--validate",
         "--checks", "-100", "--successful", "100"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   ✓ Negative checks rejected")
    else:
        print("   ✗ Should have failed")
        return 1

    # Test 9: Input validation - successful > total
    print()
    print("9. Testing input validation (successful > total)...")
    result = subprocess.run(
        ["python3", "scripts/run_availability_test.py", "--validate",
         "--checks", "100", "--successful", "150"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   ✓ Successful > total rejected")
    else:
        print("   ✗ Should have failed")
        return 1

    print()
    print("=" * 60)
    print("All availability validation tests PASSED!")
    print("=" * 60)
    print()
    print("Summary:")
    print("  - Availability threshold: 99.9%")
    print("  - Max downtime: 8.76 hours/year")
    print("  - Boundary: 999/1000 checks (99.9%) passes")
    print("  - Boundary: 998/1000 checks (99.8%) fails")
    print()
    print("Note: Full availability test requires running services and")
    print("monitoring over an extended period (days/weeks/months).")
    print("Use --monitor mode for live monitoring.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
