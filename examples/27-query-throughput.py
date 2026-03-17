#!/usr/bin/env python3
"""
Example: NFR-002 Query Throughput Test Runner

This example demonstrates how to use the throughput test runner script
to verify NFR-002 compliance (>= 1000 QPS sustained, >= 2000 QPS peak).

Prerequisites:
    - PostgreSQL, Redis, Qdrant, Elasticsearch running
    - Query Service running on port 8000
    - Test data indexed for query testing
    - locust installed: pip install locust

Usage:
    # Show help
    python examples/27-query-throughput.py

    # Validate pre-collected metrics (fastest way to verify threshold logic)
    python examples/27-query-throughput.py --validate-sustained 1200
    python examples/27-query-throughput.py --validate-burst 2500

    # Run full load tests (requires services running)
    python examples/27-query-throughput.py --sustained
    python examples/27-query-throughput.py --burst

Notes:
    - Full load tests require 10 min (sustained) or 30s (burst)
    - Use --validate-* for quick threshold verification
"""

import subprocess
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_command(cmd, description):
    """Run a command and print results."""
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    print(f"Exit code: {result.returncode}")
    return result.returncode


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="NFR-002 Query Throughput Example",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--validate-sustained",
        type=float,
        metavar="RPS",
        help="Validate sustained throughput (e.g., 1200 QPS)"
    )
    parser.add_argument(
        "--validate-burst",
        type=float,
        metavar="RPS",
        help="Validate burst throughput (e.g., 2500 QPS)"
    )
    parser.add_argument(
        "--sustained",
        action="store_true",
        help="Run full sustained load test (1000 QPS for 10 min)"
    )
    parser.add_argument(
        "--burst",
        action="store_true",
        help="Run full burst load test (2000 QPS peak)"
    )

    args = parser.parse_args()

    if not any([args.validate_sustained, args.validate_burst,
                args.sustained, args.burst]):
        parser.print_help()
        print("\n" + "="*60)
        print("EXAMPLES:")
        print("="*60)
        print("""
# Quick validation (no services needed):
python examples/27-query-throughput.py --validate-sustained 1200
python examples/27-query-throughput.py --validate-burst 2500

# Full load tests (requires services running):
python examples/27-query-throughput.py --sustained
python examples/27-query-throughput.py --burst

# Using the underlying script directly:
python scripts/run_throughput_test.py --validate --rps 1200 --duration 600
python scripts/run_throughput_test.py --validate --peak-rps 2500
        """)
        return 0

    # Run the requested test
    if args.validate_sustained:
        return run_command(
            ["python3", "scripts/run_throughput_test.py",
             "--validate", "--rps", str(args.validate_sustained), "--duration", "600"],
            f"Validating sustained throughput: {args.validate_sustained} QPS"
        )

    if args.validate_burst:
        return run_command(
            ["python3", "scripts/run_throughput_test.py",
             "--validate", "--peak-rps", str(args.validate_burst)],
            f"Validating burst throughput: {args.validate_burst} QPS"
        )

    if args.sustained:
        print("\n⚠️  Sustained test runs for 10 minutes!")
        print("   Use --validate-sustained for quick validation.")
        return run_command(
            ["python3", "scripts/run_throughput_test.py",
             "--host", "http://localhost:8000", "--sustained"],
            "Running sustained throughput test (1000 QPS for 10 min)"
        )

    if args.burst:
        print("\n⚠️  Burst test runs for 30 seconds!")
        print("   Use --validate-burst for quick validation.")
        return run_command(
            ["python3", "scripts/run_throughput_test.py",
             "--host", "http://localhost:8000", "--burst"],
            "Running burst throughput test (2000 QPS peak)"
        )


if __name__ == "__main__":
    sys.exit(main())
