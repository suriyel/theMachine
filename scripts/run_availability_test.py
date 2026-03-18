#!/usr/bin/env python3
"""
NFR-005: Service Availability Test Runner

Validates service availability meets 99.9% uptime target (<= 8.76 hours downtime per year).

Usage:
    # Run live monitoring test (requires services running)
    python scripts/run_availability_test.py --host http://localhost:8000 --monitor --interval 60 --duration 3600

    # Validate pre-collected metrics
    python scripts/run_availability_test.py --validate --checks 1000 --successful 999
    python scripts/run_availability_test.py --validate --checks 100 --successful 100 --threshold 99.9

    # Show help
    python scripts/run_availability_test.py --help

Thresholds (NFR-005):
    - Availability: >= 99.9% uptime
    - Measurement: 1-minute health check intervals
    - Max downtime: 8.76 hours/year (0.1% of 8760 hours)
"""

import argparse
import subprocess
import sys
import time
import requests
from typing import Optional

# Thresholds from NFR-005
AVAILABILITY_THRESHOLD = 99.9  # percent


def calculate_uptime_percentage(successful: int, total: int) -> float:
    """Calculate uptime percentage."""
    if total == 0:
        return 0.0
    return (successful / total) * 100


def check_health_endpoint(host: str, timeout: int = 5) -> bool:
    """
    Check if the health endpoint is responding.

    Args:
        host: Target host URL
        timeout: Request timeout in seconds

    Returns:
        True if health check succeeds, False otherwise
    """
    try:
        response = requests.get(f"{host}/api/v1/health", timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


def run_monitor_test(
    host: str,
    interval: int = 60,
    duration: int = 3600,
    timeout: int = 5
) -> int:
    """
    Run live availability monitoring test.

    Args:
        host: Target host URL
        interval: Check interval in seconds
        duration: Total test duration in seconds
        timeout: Request timeout in seconds

    Returns:
        exit code 0 if pass, 1 if fail
    """
    print(f"Running availability monitoring test...")
    print(f"  Target: {host}")
    print(f"  Interval: {interval}s")
    print(f"  Duration: {duration}s ({duration/60:.1f} min)")
    print(f"  Threshold: >= {AVAILABILITY_THRESHOLD}%")
    print()

    total_checks = 0
    successful_checks = 0
    start_time = time.time()

    while time.time() - start_time < duration:
        total_checks += 1

        # Perform health check
        is_healthy = check_health_endpoint(host, timeout)

        if is_healthy:
            successful_checks += 1
            status = "✓"
        else:
            status = "✗"

        # Calculate current uptime
        current_uptime = calculate_uptime_percentage(successful_checks, total_checks)

        # Print progress every 10 checks
        if total_checks % 10 == 0 or not is_healthy:
            print(f"  [{total_checks}] {status} Uptime: {current_uptime:.2f}%")

        # Wait for next interval
        time.sleep(interval)

    # Final calculation
    uptime_percentage = calculate_uptime_percentage(successful_checks, total_checks)

    print()
    print(f"{'='*50}")
    print(f"Availability Test Results:")
    print(f"  Total checks: {total_checks}")
    print(f"  Successful: {successful_checks}")
    print(f"  Failed: {total_checks - successful_checks}")
    print(f"  Uptime: {uptime_percentage:.2f}%")
    print(f"  Threshold: {AVAILABILITY_THRESHOLD}%")
    print()

    if uptime_percentage >= AVAILABILITY_THRESHOLD:
        print(f"✓ NFR-005 PASS: {uptime_percentage:.2f}% >= {AVAILABILITY_THRESHOLD}%")
        return 0
    else:
        print(f"✗ NFR-005 FAIL: {uptime_percentage:.2f}% < {AVAILABILITY_THRESHOLD}%")
        return 1


def validate_availability(
    checks: int,
    successful: int,
    threshold: float = AVAILABILITY_THRESHOLD
) -> int:
    """
    Validate pre-collected availability metrics.

    Args:
        checks: Total number of health checks
        successful: Number of successful health checks
        threshold: Availability threshold percentage

    Returns:
        exit code 0 if pass, 1 if fail
    """
    print(f"Validating availability...")
    print(f"  Total checks: {checks}")
    print(f"  Successful: {successful}")
    print(f"  Failed: {checks - successful}")
    print(f"  Threshold: {threshold}%")

    # Validate inputs
    if checks < 0:
        print("ERROR: Total checks cannot be negative")
        return 1

    if successful < 0:
        print("ERROR: Successful checks cannot be negative")
        return 1

    if successful > checks:
        print("ERROR: Successful checks cannot exceed total checks")
        return 1

    if checks == 0:
        print("ERROR: Total checks must be greater than zero")
        return 1

    # Calculate uptime
    uptime_percentage = calculate_uptime_percentage(successful, checks)

    print(f"  Uptime: {uptime_percentage:.2f}%")
    print()

    if uptime_percentage >= threshold:
        print(f"✓ NFR-005 PASS: {uptime_percentage:.2f}% >= {threshold}%")
        return 0
    else:
        print(f"✗ NFR-005 FAIL: {uptime_percentage:.2f}% < {threshold}%")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="NFR-005: Service Availability Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run live monitoring test (1 hour)
  python scripts/run_availability_test.py --host http://localhost:8000 --monitor --interval 60 --duration 3600

  # Validate pre-collected metrics (1000 checks)
  python scripts/run_availability_test.py --validate --checks 1000 --successful 999

  # Validate with custom threshold
  python scripts/run_availability_test.py --validate --checks 100 --successful 95 --threshold 90

Thresholds (NFR-005):
  - Availability: >= 99.9% uptime
  - Max downtime: 8.76 hours/year
        """
    )

    # Test type
    test_group = parser.add_mutually_exclusive_group(required=False)
    test_group.add_argument(
        "--monitor",
        action="store_true",
        help="Run live availability monitoring test"
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
        "--interval",
        type=int,
        default=60,
        help="Health check interval in seconds (default: 60)"
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=3600,
        help="Test duration in seconds (default: 3600 = 1 hour)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=5,
        help="Request timeout in seconds (default: 5)"
    )

    # Validation parameters
    parser.add_argument(
        "--checks",
        type=int,
        help="Total number of health checks (for --validate)"
    )
    parser.add_argument(
        "--successful",
        type=int,
        help="Number of successful health checks (for --validate)"
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=AVAILABILITY_THRESHOLD,
        help=f"Availability threshold percentage (default: {AVAILABILITY_THRESHOLD})"
    )

    args = parser.parse_args()

    # Handle --help or no arguments
    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    # Execute test mode
    if args.validate:
        if args.checks is None or args.successful is None:
            print("ERROR: --validate requires --checks and --successful")
            return 1

        return validate_availability(
            checks=args.checks,
            successful=args.successful,
            threshold=args.threshold
        )

    if args.monitor:
        return run_monitor_test(
            host=args.host,
            interval=args.interval,
            duration=args.duration,
            timeout=args.timeout
        )

    # Default: show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
