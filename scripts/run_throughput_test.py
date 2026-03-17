#!/usr/bin/env python3
"""
NFR-002: Query Throughput Test Runner

Runs load tests using Locust and validates throughput thresholds.

Usage:
    # Run full load test (requires services running)
    python scripts/run_throughput_test.py --host http://localhost:8000 --sustained
    python scripts/run_throughput_test.py --host http://localhost:8000 --burst

    # Validate pre-collected metrics
    python scripts/run_throughput_test.py --validate --rps 1200 --duration 600
    python scripts/run_throughput_test.py --validate --peak-rps 2500

    # Show help
    python scripts/run_throughput_test.py --help

Thresholds (NFR-002):
    - Sustained: >= 1000 QPS for 10 minutes
    - Peak/Burst: >= 2000 QPS
"""

import argparse
import subprocess
import sys
import os

# Thresholds from NFR-002
SUSTAINED_QPS_THRESHOLD = 1000
PEAK_QPS_THRESHOLD = 2000


def run_sustained_test(host: str, users: int = 1000, duration: int = 600):
    """
    Run sustained throughput test (1000 QPS for 10 minutes).

    Args:
        host: Target host URL
        users: Number of concurrent users
        duration: Test duration in seconds

    Returns:
        exit code 0 if pass, 1 if fail
    """
    print(f"Running sustained throughput test...")
    print(f"  Target: {host}")
    print(f"  Users: {users}")
    print(f"  Duration: {duration}s ({duration/60:.1f} min)")
    print(f"  Threshold: >= {SUSTAINED_QPS_THRESHOLD} QPS")

    # Run locust in headless mode
    cmd = [
        "locust",
        "-f", "locustfile.py",
        "--headless",
        "--host", host,
        "-u", str(users),
        "-r", "100",  # spawn rate
        "-t", f"{duration}s",
        "--csv", "/tmp/locust-sustained"
    ]

    print(f"\nExecuting: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # Parse results - look for throughput in output
    for line in result.stdout.split('\n'):
        if 'Throughput:' in line or 'requests/second' in line:
            # Extract RPS value
            import re
            match = re.search(r'(\d+\.?\d*)\s*requests/second', line)
            if match:
                rps = float(match.group(1))
                print(f"\n{'='*50}")
                print(f"Sustained Throughput: {rps:.2f} QPS")
                if rps >= SUSTAINED_QPS_THRESHOLD:
                    print(f"✓ NFR-002 PASS: {rps:.2f} QPS >= {SUSTAINED_QPS_THRESHOLD} QPS")
                    return 0
                else:
                    print(f"✗ NFR-002 FAIL: {rps:.2f} QPS < {SUSTAINED_QPS_THRESHOLD} QPS")
                    return 1

    print("ERROR: Could not parse throughput from locust output")
    return 1


def run_burst_test(host: str, users: int = 2000):
    """
    Run burst throughput test (2000 QPS peak).

    Args:
        host: Target host URL
        users: Number of concurrent users for burst

    Returns:
        exit code 0 if pass, 1 if fail
    """
    print(f"Running burst throughput test...")
    print(f"  Target: {host}")
    print(f"  Users: {users}")
    print(f"  Threshold: >= {PEAK_QPS_THRESHOLD} QPS")

    # Run locust with high user count for burst
    cmd = [
        "locust",
        "-f", "locustfile.py",
        "--headless",
        "--host", host,
        "-u", str(users),
        "-r", "500",  # high spawn rate for burst
        "-t", "30s",  # shorter duration
        "--csv", "/tmp/locust-burst"
    ]

    print(f"\nExecuting: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    # Parse results - look for peak throughput
    for line in result.stdout.split('\n'):
        if 'Throughput:' in line or 'requests/second' in line:
            import re
            match = re.search(r'(\d+\.?\d*)\s*requests/second', line)
            if match:
                rps = float(match.group(1))
                print(f"\n{'='*50}")
                print(f"Peak Throughput: {rps:.2f} QPS")
                if rps >= PEAK_QPS_THRESHOLD:
                    print(f"✓ NFR-002 PASS: {rps:.2f} QPS >= {PEAK_QPS_THRESHOLD} QPS")
                    return 0
                else:
                    print(f"✗ NFR-002 FAIL: {rps:.2f} QPS < {PEAK_QPS_THRESHOLD} QPS")
                    return 1

    print("ERROR: Could not parse throughput from locust output")
    return 1


def validate_throughput(rps: float = None, duration: int = None, peak_rps: float = None):
    """
    Validate pre-collected throughput metrics.

    Args:
        rps: Requests per second (sustained)
        duration: Test duration in seconds
        peak_rps: Peak requests per second

    Returns:
        exit code 0 if pass, 1 if fail
    """
    if rps is not None:
        print(f"Validating sustained throughput...")
        print(f"  RPS: {rps}")
        print(f"  Duration: {duration}s")
        print(f"  Threshold: >= {SUSTAINED_QPS_THRESHOLD} QPS")

        if rps >= SUSTAINED_QPS_THRESHOLD:
            print(f"✓ NFR-002 PASS: {rps:.2f} QPS >= {SUSTAINED_QPS_THRESHOLD} QPS")
            return 0
        else:
            print(f"✗ NFR-002 FAIL: {rps:.2f} QPS < {SUSTAINED_QPS_THRESHOLD} QPS")
            return 1

    if peak_rps is not None:
        print(f"Validating burst throughput...")
        print(f"  Peak RPS: {peak_rps}")
        print(f"  Threshold: >= {PEAK_QPS_THRESHOLD} QPS")

        if peak_rps >= PEAK_QPS_THRESHOLD:
            print(f"✓ NFR-002 PASS: {peak_rps:.2f} QPS >= {PEAK_QPS_THRESHOLD} QPS")
            return 0
        else:
            print(f"✗ NFR-002 FAIL: {peak_rps:.2f} QPS < {PEAK_QPS_THRESHOLD} QPS")
            return 1

    print("ERROR: No metrics provided for validation")
    return 1


def main():
    parser = argparse.ArgumentParser(
        description="NFR-002: Query Throughput Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run sustained load test (1000 QPS for 10 minutes)
  python scripts/run_throughput_test.py --host http://localhost:8000 --sustained

  # Run burst load test (2000 QPS peak)
  python scripts/run_throughput_test.py --host http://localhost:8000 --burst

  # Validate pre-collected sustained metrics
  python scripts/run_throughput_test.py --validate --rps 1200 --duration 600

  # Validate pre-collected burst metrics
  python scripts/run_throughput_test.py --validate --peak-rps 2500

Thresholds (NFR-002):
  - Sustained: >= 1000 QPS for 10 minutes (600 seconds)
  - Burst: >= 2000 QPS peak
        """
    )

    # Test type
    test_group = parser.add_mutually_exclusive_group(required=False)
    test_group.add_argument(
        "--sustained",
        action="store_true",
        help="Run sustained throughput test (1000 QPS for 10 min)"
    )
    test_group.add_argument(
        "--burst",
        action="store_true",
        help="Run burst throughput test (2000 QPS peak)"
    )
    test_group.add_argument(
        "--validate",
        action="store_true",
        help="Validate pre-collected metrics"
    )

    # Test parameters
    parser.add_argument(
        "--host",
        type=str,
        default="http://localhost:8000",
        help="Target host URL (default: http://localhost:8000)"
    )
    parser.add_argument(
        "-u", "--users",
        type=int,
        help="Number of concurrent users"
    )
    parser.add_argument(
        "-t", "--duration",
        type=int,
        help="Test duration in seconds"
    )

    # Validation parameters
    parser.add_argument(
        "--rps",
        type=float,
        help="Requests per second (for --validate)"
    )
    parser.add_argument(
        "--peak-rps",
        type=float,
        help="Peak requests per second (for --validate)"
    )

    args = parser.parse_args()

    # Handle --help or no arguments
    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    # Execute test mode
    if args.validate:
        return validate_throughput(
            rps=args.rps,
            duration=args.duration,
            peak_rps=args.peak_rps
        )

    if args.sustained:
        users = args.users or 1000
        duration = args.duration or 600  # 10 minutes
        return run_sustained_test(args.host, users, duration)

    if args.burst:
        users = args.users or 2000
        return run_burst_test(args.host, users)

    # Default: show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
