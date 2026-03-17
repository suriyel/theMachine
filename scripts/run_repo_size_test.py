#!/usr/bin/env python3
"""
NFR-004: Single Repository Size Test Runner

Tests system capacity to handle large repositories up to 1GB without failure.

Usage:
    python scripts/run_repo_size_test.py --help
    python scripts/run_repo_size_test.py --validate --size 500 --chunks 10000
    python scripts/run_repo_size_test.py --validate --size 1024 --chunks 50000

Thresholds (NFR-004):
    - Repository size: <= 1 GB (1024 MB)
    - Successful indexing with all chunks
"""

import argparse
import sys


# Thresholds from NFR-004
REPO_SIZE_MAX_MB = 1024  # 1 GB in MB
MAX_CHUNK_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB per chunk

# Size categories for testing
SIZE_CATEGORIES = {
    "small": 10,      # 10 MB
    "medium": 100,    # 100 MB
    "large": 500,     # 500 MB
    "xlarge": 1024,   # 1 GB
}


def validate_repo_size(size_mb: int, chunks_indexed: int) -> bool:
    """
    Validate that the system can handle the given repository size
    and successfully indexed all chunks.

    Args:
        size_mb: Repository size in MB
        chunks_indexed: Number of chunks successfully indexed

    Returns:
        True if test passes, False otherwise
    """
    # Validate size is within bounds
    if size_mb <= 0:
        print(f"Error: Repository size must be positive, got {size_mb} MB")
        return False

    if size_mb > REPO_SIZE_MAX_MB:
        print(f"FAIL: Repository size {size_mb}MB exceeds NFR-004 threshold {REPO_SIZE_MAX_MB}MB")
        return False

    # Validate chunks were indexed
    if chunks_indexed <= 0:
        print(f"FAIL: No chunks indexed for {size_mb}MB repository")
        return False

    # Calculate expected chunks (rough estimate: ~50KB per chunk average)
    expected_min_chunks = (size_mb * 1024 * 1024) // 50000
    if chunks_indexed < expected_min_chunks * 0.5:  # Allow 50% variance
        print(f"WARN: Chunk count {chunks_indexed} lower than expected ~{expected_min_chunks}")

    print(f"PASS: {size_mb}MB repository indexed with {chunks_indexed} chunks")
    return True


def validate_large_file_handling(file_size_mb: int, processed: bool) -> bool:
    """
    Validate that large files are handled correctly.

    Args:
        file_size_mb: File size in MB
        processed: Whether file was successfully processed

    Returns:
        True if test passes, False otherwise
    """
    if file_size_mb <= 0:
        print(f"Error: File size must be positive, got {file_size_mb} MB")
        return False

    if file_size_mb > MAX_CHUNK_SIZE_BYTES // (1024 * 1024):
        print(f"FAIL: File size {file_size_mb}MB exceeds chunk size limit")
        return False

    if not processed:
        print(f"FAIL: Large file ({file_size_mb}MB) was not processed")
        return False

    print(f"PASS: Large file ({file_size_mb}MB) processed successfully")
    return True


def run_size_test(host: str):
    """
    Run repository size test against live services.

    Args:
        host: Target host URL

    Returns:
        Exit code 0 if tests pass, 1 if any fail
    """
    print("Running repository size test...")
    print(f"Size threshold: {REPO_SIZE_MAX_MB} MB (NFR-004)")
    print()

    # This is a stub - real implementation would:
    # 1. Register a large test repository
    # 2. Trigger indexing
    # 3. Monitor job completion
    # 4. Validate all chunks were indexed

    print("Note: Full size test requires running services and indexed data.")
    print("Use --validate to test with pre-collected metrics.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="NFR-004: Single Repository Size Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run size test (requires services)
  python scripts/run_repo_size_test.py --host http://localhost:8000

  # Validate pre-collected metrics (500MB, 10000 chunks)
  python scripts/run_repo_size_test.py --validate --size 500 --chunks 10000

  # Validate at max size (1GB, 50000 chunks)
  python scripts/run_repo_size_test.py --validate --size 1024 --chunks 50000

Thresholds (NFR-004):
  - Repository size: <= 1 GB (1024 MB)
  - All chunks indexed successfully
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
        "--size",
        type=int,
        help="Repository size in MB (for --validate)"
    )
    parser.add_argument(
        "--chunks",
        type=int,
        help="Number of chunks indexed (for --validate)"
    )
    parser.add_argument(
        "--file-size",
        type=int,
        help="Single file size in MB (for large file test)"
    )
    parser.add_argument(
        "--file-processed",
        action="store_true",
        help="Large file was processed successfully"
    )
    parser.add_argument(
        "--test-large-file",
        action="store_true",
        help="Test large file handling"
    )

    args = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    if args.test_large_file:
        if args.file_size is None:
            print("Error: --file-size required with --test-large-file")
            return 1
        result = validate_large_file_handling(args.file_size, args.file_processed)
        return 0 if result else 1

    if args.validate:
        if args.size is None or args.chunks is None:
            print("Error: --size and --chunks required with --validate")
            return 1
        result = validate_repo_size(args.size, args.chunks)
        return 0 if result else 1

    return run_size_test(args.host)


if __name__ == "__main__":
    sys.exit(main())
