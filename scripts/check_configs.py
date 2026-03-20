#!/usr/bin/env python3
"""Project-specific config checker for Code Context Retrieval.

Usage:
    python scripts/check_configs.py feature-list.json [--feature <id>]

Reads required_configs from feature-list.json, loads .env file if present,
checks each env-type config via os.environ and file-type via os.path.exists.
Exit 0 = all required configs present; Exit 1 = one or more missing.
"""

import json
import os
import sys
from pathlib import Path


def load_dotenv_file(env_path: str = ".env") -> None:
    """Load KEY=VALUE pairs from .env file into os.environ."""
    path = Path(env_path)
    if not path.exists():
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and value:
                os.environ.setdefault(key, value)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_configs.py feature-list.json [--feature <id>]")
        sys.exit(1)

    feature_list_path = sys.argv[1]
    feature_id = None

    if "--feature" in sys.argv:
        idx = sys.argv.index("--feature")
        if idx + 1 < len(sys.argv):
            feature_id = int(sys.argv[idx + 1])

    with open(feature_list_path) as f:
        data = json.load(f)

    required_configs = data.get("required_configs", [])

    # Filter to configs required by the specified feature
    if feature_id is not None:
        required_configs = [
            c for c in required_configs
            if feature_id in c.get("required_by", [])
        ]

    if not required_configs:
        if feature_id is not None:
            print(f"No configs required for feature #{feature_id}")
        else:
            print("No required configs defined")
        sys.exit(0)

    # Load .env file (project uses dotenv pattern)
    project_root = Path(feature_list_path).parent
    env_file = project_root / ".env"
    load_dotenv_file(str(env_file))

    missing = []
    present = []

    for config in required_configs:
        config_type = config.get("type", "env")
        name = config.get("name", "unknown")

        if config_type == "env":
            key = config.get("key", "")
            value = os.environ.get(key, "")
            if value:
                present.append(f"  ✓ {key} = {value[:20]}{'...' if len(value) > 20 else ''}")
            else:
                hint = config.get("check_hint", "No hint available")
                missing.append(f"  ✗ {key} — {name}\n    Hint: {hint}")
        elif config_type == "file":
            path = config.get("path", "")
            if path and os.path.exists(path):
                present.append(f"  ✓ {path} exists")
            else:
                hint = config.get("check_hint", "No hint available")
                missing.append(f"  ✗ {path} — {name}\n    Hint: {hint}")

    # Print results
    if present:
        print("Present configs:")
        for line in present:
            print(line)

    if missing:
        print("\nMissing configs:")
        for line in missing:
            print(line)
        print(f"\n{len(missing)} config(s) missing")
        sys.exit(1)
    else:
        print(f"\nAll {len(present)} required config(s) present")
        sys.exit(0)


if __name__ == "__main__":
    main()
