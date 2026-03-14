#!/usr/bin/env python3
"""
Project-specific config checker for Code Context Retrieval.

Usage:
    python scripts/check_configs.py feature-list.json [--feature <id>]

Loads config values from:
    - System environment variables
    - .env file in project root (via python-dotenv)

Exit codes:
    0 = all required configs present
    1 = one or more configs missing
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Try to load dotenv
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / ".env")
except ImportError:
    pass  # dotenv not installed, rely on system env only


def load_feature_list(path: str) -> dict[str, Any]:
    """Load feature-list.json."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def check_env_config(config: dict[str, Any]) -> tuple[bool, str]:
    """Check if an env-type config is set."""
    key = config.get("key", "")
    value = os.environ.get(key, "")
    if value:
        return True, f"✓ {key} is set ({len(value)} chars)"
    else:
        return False, f"✗ {key} is NOT set"


def check_file_config(config: dict[str, Any]) -> tuple[bool, str]:
    """Check if a file-type config exists."""
    path = config.get("path", "")
    full_path = Path(__file__).parent.parent / path
    if full_path.exists() and full_path.stat().st_size > 0:
        return True, f"✓ {path} exists"
    else:
        return False, f"✗ {path} does NOT exist"


def check_configs_for_feature(
    feature_list: dict[str, Any], feature_id: int | None
) -> list[tuple[bool, str]]:
    """Check all configs required by a specific feature (or all if feature_id is None)."""
    required_configs = feature_list.get("required_configs", [])
    features = feature_list.get("features", [])

    # If feature_id specified, filter configs to those required by that feature
    if feature_id is not None:
        feature = next((f for f in features if f["id"] == feature_id), None)
        if not feature:
            print(f"ERROR: Feature #{feature_id} not found", file=sys.stderr)
            sys.exit(1)

        required_by = set(feature.get("dependencies", [])) | {feature_id}
        configs_to_check = [
            c for c in required_configs
            if any(fid in c.get("required_by", []) for fid in required_by)
        ]
    else:
        configs_to_check = required_configs

    results = []
    for config in configs_to_check:
        config_type = config.get("type", "env")
        if config_type == "env":
            ok, msg = check_env_config(config)
        elif config_type == "file":
            ok, msg = check_file_config(config)
        else:
            ok, msg = False, f"✗ Unknown config type: {config_type}"

        if not ok:
            msg += f"\n  Hint: {config.get('check_hint', 'No hint available')}"
        results.append((ok, msg))

    return results


def main():
    parser = argparse.ArgumentParser(description="Check required configs")
    parser.add_argument("feature_list", help="Path to feature-list.json")
    parser.add_argument("--feature", type=int, help="Feature ID to check configs for")
    args = parser.parse_args()

    feature_list = load_feature_list(args.feature_list)
    results = check_configs_for_feature(feature_list, args.feature)

    all_ok = all(ok for ok, _ in results)

    print("=== Config Check ===\n")
    for ok, msg in results:
        print(msg)

    print()
    if all_ok:
        print("All required configs present.")
        sys.exit(0)
    else:
        print("MISSING CONFIGS: Set the missing values and re-run.")
        sys.exit(1)


if __name__ == "__main__":
    main()
