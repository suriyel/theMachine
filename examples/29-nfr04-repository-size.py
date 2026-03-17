#!/usr/bin/env python3
"""
Example: NFR-004 Single Repository Size Test Runner

This example demonstrates how to use the repository size test runner script
to verify NFR-004 compliance (repositories up to 1GB indexed successfully).

Prerequisites:
    - PostgreSQL, Redis, Qdrant, Elasticsearch running
    - Celery worker running for indexing
    - 1GB test repository available

Usage:
    # Show help
    python examples/29-nfr04-repository-size.py

    # Validate pre-collected metrics (fastest way to verify threshold logic)
    python examples/29-nfr04-repository-size.py --validate 500 10000
    python examples/29-nfr04-repository-size.py --validate 1024 20000

    # Test large file handling
    python examples/29-nfr04-repository-size.py --large-file 50 --processed
    python examples/29-nfr04-repository-size.py --large-file 50

    # Run full size test (requires services running)
    python examples/29-nfr04-repository-size.py

Notes:
    - Full size tests require a large test repository
    - Use --validate for quick threshold verification
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
        description="NFR-004 Single Repository Size Example",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "size_chunks",
        nargs="*",
        metavar=("SIZE", "CHUNKS"),
        help="Validate: repository size in MB and chunks indexed"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate pre-collected metrics"
    )
    parser.add_argument(
        "--large-file",
        type=int,
        metavar="MB",
        help="Test large file handling (size in MB)"
    )
    parser.add_argument(
        "--processed",
        action="store_true",
        help="Large file was processed successfully"
    )
    parser.add_argument(
        "--full-test",
        action="store_true",
        help="Run full repository size test (requires services)"
    )

    args = parser.parse_args()

    # Show help if no args
    if not any([args.size_chunks, args.validate, args.large_file, args.full_test]):
        parser.print_help()
        print("\n" + "="*60)
        print("EXAMPLES:")
        print("="*60)
        print("""
# Quick validation (no services needed):
python examples/29-nfr04-repository-size.py 500 10000
python examples/29-nfr04-repository-size.py 1024 20000

# Large file handling tests:
python examples/29-nfr04-repository-size.py --large-file 50 --processed
python examples/29-nfr04-repository-size.py --large-file 50

# Full size test (requires services running):
python examples/29-nfr04-repository-size.py --full-test

# Using the underlying script directly:
python scripts/run_repo_size_test.py --validate --size 500 --chunks 10000
python scripts/run_repo_size_test.py --test-large-file --file-size 50 --file-processed
        """)
        return 0

    # Run the requested test
    if args.size_chunks and len(args.size_chunks) == 2:
        size = args.size_chunks[0]
        chunks = args.size_chunks[1]
        return run_command(
            ["python3", "scripts/run_repo_size_test.py",
             "--validate", "--size", str(size), "--chunks", str(chunks)],
            f"Validating repository size: {size}MB with {chunks} chunks"
        )

    if args.large_file:
        cmd = ["python3", "scripts/run_repo_size_test.py",
               "--test-large-file", "--file-size", str(args.large_file)]
        if args.processed:
            cmd.append("--file-processed")
        return run_command(
            cmd,
            f"Testing large file handling: {args.large_file}MB"
        )

    if args.full_test:
        return run_command(
            ["python3", "scripts/run_repo_size_test.py",
             "--host", "http://localhost:8000"],
            "Running full repository size test"
        )


if __name__ == "__main__":
    sys.exit(main())
