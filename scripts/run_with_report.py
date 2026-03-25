#!/usr/bin/env python3
"""
Run a command, save full output to a report file, return only a concise summary.

Usage:
    python run_with_report.py <report-path> [--tail N] [--label LABEL] -- <command...>

Examples:
    python scripts/run_with_report.py .long-task-reports/coverage.txt -- pytest --cov=src
    python scripts/run_with_report.py .long-task-reports/mutation.txt --tail 30 -- mutmut run
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime


def main():
    # Split args on '--' separator
    try:
        sep_idx = sys.argv.index('--')
    except ValueError:
        print("Error: missing '--' separator between options and command", file=sys.stderr)
        print("Usage: run_with_report.py <report-path> [--tail N] -- <command...>", file=sys.stderr)
        sys.exit(2)

    our_args = sys.argv[1:sep_idx]
    cmd_args = sys.argv[sep_idx + 1:]

    if not cmd_args:
        print("Error: no command provided after '--'", file=sys.stderr)
        sys.exit(2)

    parser = argparse.ArgumentParser()
    parser.add_argument('report_path', help='Path to save full output')
    parser.add_argument('--tail', type=int, default=20, help='Number of tail lines to show (default: 20)')
    parser.add_argument('--label', default=None, help='Label for the summary header')
    args = parser.parse_args(our_args)

    label = args.label or os.path.splitext(os.path.basename(args.report_path))[0]
    command_str = ' '.join(cmd_args)

    # Ensure report directory exists
    report_dir = os.path.dirname(args.report_path)
    if report_dir:
        os.makedirs(report_dir, exist_ok=True)

    # Run command, capture merged stdout+stderr
    try:
        result = subprocess.run(
            command_str,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        full_output = result.stdout or ''
        exit_code = result.returncode
    except Exception as e:
        full_output = f"Error executing command: {e}\n"
        exit_code = 127

    # Write full output to report file
    with open(args.report_path, 'w', encoding='utf-8') as f:
        f.write(f"# Command: {command_str}\n")
        f.write(f"# Timestamp: {datetime.now().isoformat()}\n")
        f.write(f"# Exit code: {exit_code}\n\n")
        f.write(full_output)

    # Build summary
    lines = full_output.rstrip('\n').split('\n') if full_output.strip() else []
    total_lines = len(lines)
    tail_n = min(args.tail, total_lines)
    tail_lines = lines[-tail_n:] if tail_n > 0 else []

    verdict = "PASS" if exit_code == 0 else "FAIL"
    print(f"[{label}] {verdict} (exit code {exit_code})")
    print(f"Report: {args.report_path} ({total_lines} lines)")

    if tail_lines:
        print(f"--- last {tail_n} lines ---")
        for line in tail_lines:
            print(line)
        print("---")

    if exit_code != 0:
        print(f"\nFAIL: Read {args.report_path} for full details.")

    sys.exit(exit_code)


if __name__ == '__main__':
    main()
