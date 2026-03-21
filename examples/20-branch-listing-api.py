#!/usr/bin/env python3
"""Example: Branch Listing API (Feature #33)

Demonstrates the GET /api/v1/repos/{id}/branches endpoint that lists
remote branches for a registered repository.

Prerequisites:
  - API server running (see env-guide.md)
  - A registered and cloned repository
  - Valid API key with 'read' or 'admin' role
"""

import requests

API_BASE = "http://localhost:8000/api/v1"
API_KEY = "your-api-key-here"
HEADERS = {"X-API-Key": API_KEY}


def list_branches(repo_id: str) -> dict:
    """List remote branches for a registered repository."""
    resp = requests.get(f"{API_BASE}/repos/{repo_id}/branches", headers=HEADERS)
    resp.raise_for_status()
    return resp.json()


def main():
    # 1. List registered repos to find one
    repos_resp = requests.get(f"{API_BASE}/repos", headers=HEADERS)
    repos_resp.raise_for_status()
    repos = repos_resp.json()

    if not repos:
        print("No repositories registered. Register one first.")
        return

    repo = repos[0]
    print(f"Repository: {repo['name']} (ID: {repo['id']})")
    print(f"Status: {repo['status']}")

    # 2. List branches
    try:
        data = list_branches(repo["id"])
        print(f"\nBranches ({len(data['branches'])}):")
        for branch in data["branches"]:
            marker = " (default)" if branch == data["default_branch"] else ""
            print(f"  - {branch}{marker}")
        print(f"\nDefault branch: {data['default_branch']}")
    except requests.HTTPError as e:
        if e.response.status_code == 409:
            print("Repository has not been cloned yet. Trigger an index first.")
        elif e.response.status_code == 404:
            print("Repository not found.")
        else:
            print(f"Error: {e.response.status_code} - {e.response.text}")


if __name__ == "__main__":
    main()
