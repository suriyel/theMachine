#!/usr/bin/env python3
"""
NFR-006: Linear Scalability Test Runner

Validates that adding a query node increases throughput linearly (±20%).

Usage:
    # Validate pre-collected metrics
    python scripts/run_scalability_test.py --validate --nodes 1 --throughput 1000 --nodes1 2 --throughput1 1900
    python scripts/run_scalability_test.py --validate --nodes 1 --throughput 1000 --nodes1 2 --throughput1 2200 --threshold-min 80 --threshold-max 120

    # Show help
    python scripts/run_scalability_test.py --help

Thresholds (NFR-006):
    - Linear scaling: 80-120% of per-node capacity increase
    - Formula: (throughput_N1 - throughput_N) / per_node_capacity between 0.8 and 1.2
"""

import argparse
import sys

# Default thresholds from NFR-006
THRESHOLD_MIN = 80  # percent
THRESHOLD_MAX = 120  # percent


def calculate_scaling_percentage(
    nodes: int,
    throughput: float,
    nodes1: int,
    throughput1: float
) -> float:
    """
    Calculate the scaling percentage.

    Per-node capacity at N nodes = throughput / nodes
    Throughput gain = throughput1 - throughput
    Expected gain = per_node_capacity
    Scaling percentage = (actual_gain / expected_gain) * 100
    """
    if nodes <= 0 or nodes1 <= nodes:
        return 0.0

    per_node_capacity = throughput / nodes
    if per_node_capacity <= 0:
        return 0.0

    throughput_gain = throughput1 - throughput
    if throughput_gain < 0:
        # Negative scaling - worse than nothing
        return 0.0

    # Scaling percentage = (actual gain / expected gain) * 100
    # Expected gain = per_node_capacity (adding 1 node should add 1x per-node capacity)
    scaling_percentage = (throughput_gain / per_node_capacity) * 100

    return scaling_percentage


def validate_scalability(
    nodes: int,
    throughput: float,
    nodes1: int,
    throughput1: float,
    threshold_min: float = THRESHOLD_MIN,
    threshold_max: float = THRESHOLD_MAX
) -> int:
    """
    Validate scalability metrics.

    Args:
        nodes: Number of nodes in baseline
        throughput: Throughput at baseline (QPS)
        nodes1: Number of nodes after scaling
        throughput1: Throughput after scaling (QPS)
        threshold_min: Minimum acceptable scaling percentage
        threshold_max: Maximum acceptable scaling percentage

    Returns:
        exit code 0 if pass, 1 if fail
    """
    print(f"Validating linear scalability...")
    print(f"  Baseline: {nodes} nodes, {throughput} QPS")
    print(f"  Scaled:   {nodes1} nodes, {throughput1} QPS")
    print(f"  Threshold: {threshold_min}% - {threshold_max}%")

    # Validate inputs
    if nodes <= 0:
        print("ERROR: Number of nodes must be greater than zero")
        return 1

    if nodes1 <= nodes:
        print("ERROR: nodes1 must be greater than nodes")
        return 1

    if throughput <= 0:
        print("ERROR: Throughput must be greater than zero")
        return 1

    if throughput1 <= 0:
        print("ERROR: Throughput1 must be greater than zero")
        return 1

    if throughput1 < throughput:
        print(f"ERROR: Throughput1 ({throughput1}) must be >= throughput ({throughput})")
        return 1

    if threshold_min < 0 or threshold_max < 0:
        print("ERROR: Threshold values must be non-negative")
        return 1

    if threshold_min > threshold_max:
        print("ERROR: threshold-min must be <= threshold-max")
        return 1

    # Calculate scaling percentage
    scaling_percentage = calculate_scaling_percentage(nodes, throughput, nodes1, throughput1)

    print(f"  Scaling: {scaling_percentage:.2f}%")
    print()

    if threshold_min <= scaling_percentage <= threshold_max:
        print(f"✓ NFR-006 PASS: {scaling_percentage:.2f}% is within {threshold_min}%-{threshold_max}%")
        return 0
    else:
        print(f"✗ NFR-006 FAIL: {scaling_percentage:.2f}% is outside {threshold_min}%-{threshold_max}%")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="NFR-006: Linear Scalability Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate scaling from 1 to 2 nodes (100% scaling = perfect)
  python scripts/run_scalability_test.py --validate --nodes 1 --throughput 1000 --nodes1 2 --throughput1 2000

  # Validate scaling at 80% boundary
  python scripts/run_scalability_test.py --validate --nodes 1 --throughput 1000 --nodes1 2 --throughput1 1800

  # Validate scaling at 120% boundary
  python scripts/run_scalability_test.py --validate --nodes 1 --throughput 1000 --nodes1 2 --throughput1 2200

  # Validate with custom thresholds
  python scripts/run_scalability_test.py --validate --nodes 1 --throughput 1000 --nodes1 2 --throughput1 1500 --threshold-min 40 --threshold-max 160

Thresholds (NFR-006):
  - Linear scaling: 80-120% of per-node capacity increase
  - Adding 1 node should add 80-120% of the per-node capacity
        """
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate pre-collected metrics"
    )

    # Validation parameters
    parser.add_argument(
        "--nodes",
        type=int,
        help="Number of nodes in baseline"
    )
    parser.add_argument(
        "--throughput",
        type=float,
        help="Throughput at baseline (QPS)"
    )
    parser.add_argument(
        "--nodes1",
        type=int,
        help="Number of nodes after scaling (must be > nodes)"
    )
    parser.add_argument(
        "--throughput1",
        type=float,
        help="Throughput after scaling (QPS)"
    )
    parser.add_argument(
        "--threshold-min",
        type=float,
        default=THRESHOLD_MIN,
        help=f"Minimum scaling percentage (default: {THRESHOLD_MIN})"
    )
    parser.add_argument(
        "--threshold-max",
        type=float,
        default=THRESHOLD_MAX,
        help=f"Maximum scaling percentage (default: {THRESHOLD_MAX})"
    )

    args = parser.parse_args()

    # Handle --help or no arguments
    if len(sys.argv) == 1:
        parser.print_help()
        return 0

    # Execute validation
    if args.validate:
        if None in (args.nodes, args.throughput, args.nodes1, args.throughput1):
            print("ERROR: --validate requires --nodes, --throughput, --nodes1, and --throughput1")
            return 1

        return validate_scalability(
            nodes=args.nodes,
            throughput=args.throughput,
            nodes1=args.nodes1,
            throughput1=args.throughput1,
            threshold_min=args.threshold_min,
            threshold_max=args.threshold_max
        )

    # Default: show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
