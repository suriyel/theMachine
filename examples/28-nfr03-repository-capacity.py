#!/usr/bin/env python3
"""
NFR-003: Repository Capacity Test Example

Demonstrates the capacity test runner script functionality.
This script validates that the system can handle 100-1000 repositories
while maintaining query latency within NFR-001 bounds (P95 <= 1000ms).

Usage:
    python examples/28-nfr03-repository-capacity.py

This validates the threshold logic used by the capacity test runner.
"""

import subprocess
import sys


def main():
    print("=" * 60)
    print("NFR-003: Repository Capacity Test Example")
    print("=" * 60)
    print()

    # Test 1: Show help
    print("1. Running capacity test script --help...")
    result = subprocess.run(
        ["python3", "scripts/run_capacity_test.py", "--help"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   ✓ Help command works")
    else:
        print("   ✗ Help command failed")
        return 1

    # Test 2: Validate under threshold
    print()
    print("2. Testing validation under threshold...")
    result = subprocess.run(
        ["python3", "scripts/run_capacity_test.py", "--validate",
         "--repos", "500", "--latency", "800"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   ✓ 500 repos with 800ms latency PASSES")
    else:
        print("   ✗ Should have passed")
        return 1

    # Test 3: Validate at threshold
    print()
    print("3. Testing validation at threshold...")
    result = subprocess.run(
        ["python3", "scripts/run_capacity_test.py", "--validate",
         "--repos", "1000", "--latency", "1000"],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("   ✓ 1000 repos with 1000ms latency PASSES (at boundary)")
    else:
        print("   ✗ Should have passed at boundary")
        return 1

    # Test 4: Validate over threshold
    print()
    print("4. Testing validation over threshold...")
    result = subprocess.run(
        ["python3", "scripts/run_capacity_test.py", "--validate",
         "--repos", "500", "--latency", "1500"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   ✓ 500 repos with 1500ms latency FAILS (exceeds NFR-001)")
    else:
        print("   ✗ Should have failed")
        return 1

    # Test 5: Validate below min repos
    print()
    print("5. Testing below minimum repository count...")
    result = subprocess.run(
        ["python3", "scripts/run_capacity_test.py", "--validate",
         "--repos", "50", "--latency", "500"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   ✓ 50 repos FAILS (below minimum 100)")
    else:
        print("   ✗ Should have failed")
        return 1

    # Test 6: Validate above max repos
    print()
    print("6. Testing above maximum repository count...")
    result = subprocess.run(
        ["python3", "scripts/run_capacity_test.py", "--validate",
         "--repos", "1500", "--latency", "500"],
        capture_output=True,
        text=True
    )
    if result.returncode == 1:
        print("   ✓ 1500 repos FAILS (above maximum 1000)")
    else:
        print("   ✗ Should have failed")
        return 1

    print()
    print("=" * 60)
    print("All capacity validation tests PASSED!")
    print("=" * 60)
    print()
    print("Summary:")
    print("  - Valid repo counts: 100-1000")
    print("  - Max latency: 1000ms (NFR-001 bound)")
    print("  - Scale points: [100, 250, 500, 750, 1000]")
    print()
    print("Note: Full capacity test requires running services with")
    print("100-1000 indexed repositories for load testing.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
