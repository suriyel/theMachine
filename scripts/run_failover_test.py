#!/usr/bin/env python3
"""
NFR-007: Single-Node Failure Tolerance Test Runner

Validates that the system tolerates single-node failure with zero query failures
and failover <= 30 seconds.

Usage:
    # Validate pre-collected metrics
    python scripts/run_failover_test.py --validate --queries 1000 --failures 0 --failover-time 5
    python scripts/run_failover_test.py --validate --queries 1000 --failures 0 --failover-time 30

    # Show help
    python scripts/run_failover_test.py --help

Thresholds (NFR-007):
    - Zero query failures during single-node outage
    - Failover <= 30 seconds
"""

import argparse
import sys

# Default thresholds from NFR-007
MAX_FAILOVER_TIME = 30  # seconds
MAX_QUERY_FAILURES = 0  # zero tolerance


def validate_failover(
    queries: int,
    failures: int,
    failover_time: float,
    max_failures: int = MAX_FAILOVER_TIME,
    max_time: float = MAX_FAILOVER_TIME
) -> int:
    """
    Validate failover metrics.

    Args:
        queries: Total number of queries during test
        failures: Number of failed queries
        failover_time: Failover time in seconds
        max_failures: Maximum acceptable failures
        max_time: Maximum acceptable failover time

    Returns:
        exit code 0 if pass, 1 if fail
    """
    print(f"Validating single-node failure tolerance...")
    print(f"  Total queries: {queries}")
    print(f"  Failed queries: {failures}")
    print(f"  Failover time: {failover_time}s")
    print(f"  Thresholds: max failures={max_failures}, max time={max_time}s")

    # Validate inputs
    if queries <= 0:
        print("ERROR: Number of queries must be greater than zero")
        return 1

    if failures < 0:
        print("ERROR: Number of failures cannot be negative")
        return 1

    if failures > queries:
        print("ERROR: Failures cannot exceed total queries")
        return 1

    if failover_time < 0:
        print("ERROR: Failover time cannot be negative")
        return 1

    # Check failure tolerance
    if failures > max_failures:
        print(f"✗ NFR-007 FAIL: {failures} failures > {max_failures} max failures")
        return 1

    # Check failover time
    if failover_time > max_time:
        print(f"✗ NFR-007 FAIL: {failover_time}s > {max_time}s max failover time")
        return 1

    print(f"✓ NFR-007 PASS: {failures} failures <= {max_failures}, {failover_time}s <= {max_time}s")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="NFR-007: Single-Node Failure Tolerance Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate zero failures, 5s failover
  python scripts/run_failover_test.py --validate --queries 1000 --failures 0 --failover-time 5

  # Validate zero failures, 30s failover (boundary)
  python scripts/run_failover_test.py --validate --queries 1000 --failures 0 --failover-time 30

  # Validate some failures (should fail)
  python scripts/run_failover_test.py --validate --queries 1000 --failures 1 --failover-time 5

Thresholds (NFR-007):
  - Zero query failures during single-node outage
  - Failover <= 30 seconds
        """
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate pre-collected metrics"
    )

    parser.add_argument(
        "--queries",
        type=int,
        help="Total number of queries during test"
    )
    parser.add_argument(
        "--failures",
        type=int,
        help="Number of failed queries"
    )
    parser.add_argument(
        "--failover-time",
        type=float,
        help="Failover time in seconds"
    )
    parser.add_argument(
        "--max-failures",
        type=int,
        default=MAX_QUERY_FAILURES,
        help=f"Maximum acceptable failures (default: {MAX_QUERY_FAILURES})"
    )
    parser.add_argument(
        "--max-time",
        type=float,
        default=MAX_FAILOVER_TIME,
        help=f"Maximum failover time in seconds (default: {MAX_FAILOVER_TIME})"
    )

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    if args.validate:
        if None in (args.queries, args.failures, args.failover_time):
            print("ERROR: --validate requires --queries, --failures, and --failover-time")
            return 1

        return validate_failover(
            queries=args.queries,
            failures=args.failures,
            failover_time=args.failover_time,
            max_failures=args.max_failures,
            max_time=args.max_time
        )

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
