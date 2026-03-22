#!/bin/bash
# Example: Web UI Search Page (Feature #19)
#
# The Web UI is a Jinja2 SSR interface with Developer Dark theme.
# It serves the following routes:
#   GET  /          — Main search page with form, filters, registration
#   GET  /search    — Search results (htmx partial or full page)
#   POST /register  — Register a repository
#   GET  /branches  — List branches for a repo URL (htmx partial)
#
# To run the query-api service:
#   source .venv/bin/activate
#   set -a && source .env && set +a
#   uvicorn src.query.main:app --host 0.0.0.0 --port 8000
#
# Then open http://localhost:8000/ in your browser.
#
# Or test via curl:

echo "=== GET / — Search page ==="
curl -s http://localhost:8000/ | head -20

echo ""
echo "=== GET /search?q=timeout — Search results ==="
curl -s "http://localhost:8000/search?q=timeout" | head -20

echo ""
echo "=== GET /search?q= — Empty query validation ==="
curl -s "http://localhost:8000/search?q=" | head -10

echo ""
echo "=== GET /branches?repo_id=https://github.com/test/repo — Branch listing ==="
curl -s "http://localhost:8000/branches?repo_id=https://github.com/test/repo" | head -10
