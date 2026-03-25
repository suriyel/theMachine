#!/usr/bin/env bash
# Example: Web UI Index Management Page (Feature #47, FR-031)
#
# Demonstrates the index management endpoints via curl.
# Prerequisites: query-api running on localhost:8000 with DB configured.
#
# Usage:
#   bash examples/47-web-ui-index-management.sh

BASE_URL="http://localhost:8000"

echo "=== 1. Index Management Page ==="
echo "GET /admin/indexes"
curl -s "$BASE_URL/admin/indexes" | head -30
echo -e "\n"

echo "=== 2. Index Stats (replace REPO_ID with a real UUID) ==="
echo "GET /admin/indexes/{repo_id}/stats"
# Example: curl -s "$BASE_URL/admin/indexes/550e8400-e29b-41d4-a716-446655440000/stats"
echo "(requires a valid repo_id from the database)"
echo ""

echo "=== 3. Reindex Single Repo ==="
echo "POST /admin/indexes/{repo_id}/reindex"
# Example: curl -s -X POST "$BASE_URL/admin/indexes/550e8400-e29b-41d4-a716-446655440000/reindex"
echo "(dispatches Celery task, returns success partial with job ID)"
echo ""

echo "=== 4. Reindex All ==="
echo "POST /admin/indexes/reindex-all"
# Example: curl -s -X POST "$BASE_URL/admin/indexes/reindex-all"
echo "(dispatches reindex for all repos, returns summary partial)"
echo ""

echo "=== 5. Delete Index ==="
echo "POST /admin/indexes/{repo_id}/delete"
# Example: curl -s -X POST "$BASE_URL/admin/indexes/550e8400-e29b-41d4-a716-446655440000/delete"
echo "(deletes ES/Qdrant data, clears last_indexed_at)"
echo ""

echo "=== Notes ==="
echo "- All responses are HTML partials (HTMX), not JSON"
echo "- Delete and Reindex All use hx-confirm for browser confirmation prompts"
echo "- These routes are Web UI only -- NOT exposed via MCP"
