"""Example: Repository Registration

This example demonstrates how to register a Git repository for indexing
using the Query Service API.

Usage:
    python examples/03-repository-registration.py

The script creates a test repository registration and lists all repositories.
"""

import asyncio
import sys

from httpx import AsyncClient, ASGITransport


async def main():
    """Register a repository and list all repositories."""
    transport = ASGITransport(app="src.query.main:app")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Register a new repository
        print("Registering repository...")
        response = await client.post(
            "/api/v1/repos?skip_validation=true",
            json={
                "url": "https://github.com/example/demo-repo.git",
                "name": "Demo Repository",
                "languages": ["Python", "JavaScript"],
            },
        )

        if response.status_code == 201:
            repo = response.json()
            print(f"✓ Repository registered: {repo['name']}")
            print(f"  URL: {repo['url']}")
            print(f"  Status: {repo['status']}")
            print(f"  Languages: {repo['languages']}")
        elif response.status_code == 409:
            print("✓ Repository already registered")
        else:
            print(f"✗ Failed to register: {response.status_code}")
            print(f"  {response.json()}")
            return 1

        # List all repositories
        print("\nListing all repositories...")
        response = await client.get("/api/v1/repos")

        if response.status_code == 200:
            repos = response.json()
            print(f"✓ Found {len(repos)} repository(ies):")
            for repo in repos:
                print(f"  - {repo['name']} ({repo['status']})")
        else:
            print(f"✗ Failed to list: {response.status_code}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
