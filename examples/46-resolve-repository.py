#!/usr/bin/env python3
"""Example: Repository Resolution MCP Tool (Feature #46).

Demonstrates the resolve_repository MCP tool with match quality sorting
and available_branches population.

Usage:
    python examples/46-resolve-repository.py
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

from src.query.mcp_server import (
    _populate_branches,
    _score_match,
    create_mcp_server,
)


def _make_repo(name, url, status="indexed", clone_path=None):
    """Create a mock Repository for demonstration."""
    repo = MagicMock()
    repo.name = name
    repo.url = url
    repo.status = status
    repo.clone_path = clone_path
    repo.indexed_branch = "main"
    repo.default_branch = "main"
    repo.last_indexed_at = datetime(2026, 3, 25, 12, 0, 0)
    return repo


def demo_score_match():
    """Show the 5-tier match quality scoring."""
    print("=" * 60)
    print("  _score_match — 5-Tier Match Quality")
    print("=" * 60)

    cases = [
        ("gson", "https://github.com/google/gson", "gson", "Exact name"),
        ("springfw", "https://github.com/org/spring", "spring", "Exact URL segment"),
        ("gson-fire", "https://github.com/x/gson-fire", "gson", "Prefix name"),
        ("mylib", "https://github.com/org/gson-ext", "gson", "Prefix URL segment"),
        ("my-gson-lib", "https://github.com/acme/my-gson-lib", "gson", "Substring"),
        ("react", "https://github.com/facebook/react", "gson", "No match"),
    ]

    for name, url, search, label in cases:
        tier = _score_match(name, url, search)
        print(f"  Tier {tier:>2} | {label:<20} | name={name}, search={search}")


def demo_populate_branches():
    """Show graceful degradation of branch population."""
    print("\n" + "=" * 60)
    print("  _populate_branches — Graceful Degradation")
    print("=" * 60)

    repo_with_clone = _make_repo("gson", "https://x", clone_path="/tmp/gson")
    repo_no_clone = _make_repo("react", "https://x", clone_path=None)

    cloner = MagicMock()
    cloner.list_remote_branches = MagicMock(return_value=["dev", "main", "release/v2"])

    print(f"  With clone_path + cloner: {_populate_branches(repo_with_clone, cloner)}")
    print(f"  With clone_path, no cloner: {_populate_branches(repo_with_clone, None)}")
    print(f"  No clone_path: {_populate_branches(repo_no_clone, cloner)}")

    # Simulate git error
    error_cloner = MagicMock()
    error_cloner.list_remote_branches = MagicMock(side_effect=Exception("git error"))
    print(f"  Git error (graceful): {_populate_branches(repo_with_clone, error_cloner)}")


async def demo_resolve_repository():
    """Show full resolve_repository with sorted results."""
    print("\n" + "=" * 60)
    print("  resolve_repository — Sorted Results with Branches")
    print("=" * 60)

    repos = [
        _make_repo("my-gson-lib", "https://github.com/acme/my-gson-lib", clone_path="/tmp/my-gson-lib"),
        _make_repo("gson-fire", "https://github.com/julman99/gson-fire"),
        _make_repo("gson", "https://github.com/google/gson", clone_path="/tmp/gson"),
        _make_repo("react", "https://github.com/facebook/react"),
        _make_repo("spring", "https://github.com/spring/spring", status="pending"),
    ]
    indexed = [r for r in repos if r.status == "indexed"]

    session = AsyncMock()
    result_mock = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = indexed
    result_mock.scalars.return_value = scalars_mock
    session.execute = AsyncMock(return_value=result_mock)
    session.close = AsyncMock()
    sf = MagicMock(return_value=session)

    cloner = MagicMock()
    cloner.list_remote_branches = MagicMock(return_value=["dev", "main"])

    mcp = create_mcp_server(AsyncMock(), sf, AsyncMock(), git_cloner=cloner)
    tool = mcp._tool_manager._tools["resolve_repository"]

    result = json.loads(await tool.fn(query="JSON parsing", libraryName="gson"))

    print(f"\n  Query: resolve_repository(query='JSON parsing', libraryName='gson')")
    print(f"  Results: {len(result)} repos (sorted by match quality)\n")

    for i, r in enumerate(result):
        branches = r["available_branches"]
        branch_str = ", ".join(branches) if branches else "(none)"
        print(f"  [{i+1}] {r['name']}")
        print(f"      URL: {r['url']}")
        print(f"      Branches: {branch_str}")
        print(f"      Indexed: {r['indexed_branch']}")


if __name__ == "__main__":
    demo_score_match()
    demo_populate_branches()
    asyncio.run(demo_resolve_repository())
    print("\n  Done.")
