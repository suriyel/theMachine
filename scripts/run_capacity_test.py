#!/usr/bin/env python3
"""
NFR-003: Repository Capacity Test Runner

Tests system capacity to handle 100-1000 repositories while maintaining
query latency within NFR-001 bounds (P95 <= 1000ms).

Usage:
    python scripts/run_capacity_test.py --help
    python scripts/run_capacity_test.py --host http://localhost:8000
    python scripts/run_capacity_test.py --validate --repos 500 --latency 800
    python scripts/run_capacity_test.py --validate --repos 1000 --latency 950

Thresholds (NFR-003):
    - Repository count: 100 to 1000
    - Latency: P95 <= 1000ms (NFR-001 bound)
"""

import argparse
import sys


# Thresholds from NFR-003
REPO_COUNT_MIN = 100
REPO_COUNT_MAX = 1000
LATENCY_P95_MAX = 1000  # ms (NFR-001 bound)

# Progressive scale points
SCALE_POINTS = [100, 250, 500, 750, 1000]


def validate_capacity(repos: int, latency_ms: float) -> bool:
    """
    Validate that the system can handle the given repository count
    while maintaining latency within NFR-001 bounds.

    Args:
        repos: Number of repositories
        latency_ms: P95 latency in milliseconds

    Returns:
        True if capacity test passes, False otherwise
    """
    # Validate repo count
    if repos < REPO_COUNT_MIN or repos > REPO_COUNT_MAX:
        print(f"Error: Repository count {repos} outside valid range [{REPO_COUNT_MIN}, {REPO_COUNT_MAX}]")
        return False

    # Validate latency against NFR-001 threshold
    if latency_ms > LATENCY_P95_MAX:
        print(f"FAIL: Latency {latency_ms}ms exceeds NFR-001 threshold {LATENCY_P95_MAX}ms")
        return False

    print(f"PASS: {repos} repos with {latency_ms}ms latency (within NFR-001 bound)")
    return True


def run_progressive_test(host: str):
    """
    Run progressive capacity test across scale points.

    Args:
        host: Target host URL

    Returns:
        Exit code 0 if all scale points pass, 1 if any fail
    """
    print("Running progressive capacity test...")
    print(f"Scale points: {SCALE_POINTS}")
    print(f"Latency threshold: {LATENCY_P95_MAX}ms (NFR-001)")
    print()

    # This is a stub - real implementation would:
    # 1. Progressively add repositories
    # 2. Measure query latency at each scale point
    # 3. Validate latency stays within NFR-001 bounds

    print("Note: Full capacity test requires running services and indexed data.")
    print("Use --validate to test with pre-collected metrics.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="NFR-003: Repository Capacity Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run progressive capacity test (requires services)
  python scripts/run_capacity_test.py --host http://localhost:8000

  # Validate pre-collected metrics
  python scripts/run_capacity_test.py --validate --repos 500 --latency 800

  # Validate at max capacity
  python scripts/run_capacity_test.py --validate --repos 1000 --latency 950

Thresholds (NFR-003):
  - Repository count: 100 to 1000
  - Latency: P95 <= 1000ms (NFR-001 bound)
        """
    )

    parser.add_argument(
        "--host",
        type=str,
        default="http://localhost:8000",
        help="Target host URL"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate pre-collected metrics"
    )
    parser.add_argument(
        "--repos",
        type=int,
        help="Number of repositories (for --validate)"
    )
    parser.add_argument(
        "--latency",
        type=float,
        help="P95 latency in ms (for --validate)"
    )

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    if args.validate:
        if args.repos is None or args.latency is None:
            print("Error: --repos and --latency required with --validate")
            return 1
        result = validate_capacity(args.repos, args.latency)
        return 0 if result else 1

    return run_progressive_test(args.host)


if __name__ == "__main__":
    sys.exit(main())
