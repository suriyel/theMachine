# Feature #17 Implementation Plan: REST API Endpoints

**Date**: 2026-03-16
**Feature**: REST API Endpoints (Feature #17)
**Status**: In Progress

## Overview

Feature #17 implements FastAPI REST endpoints for the Query Service. The endpoints are mostly implemented but there's a critical import bug preventing tests from running.

## Verification Steps

From `feature-list.json`:

1. Given valid API key, when POST /api/v1/query with query body, then 200 with QueryResponse
2. Given valid API key, when GET /api/v1/query?text=foo, then 200 with QueryResponse
3. Given no auth, when GET /api/v1/health, then 200 with health status
4. Given no auth, when GET /api/v1/metrics, then Prometheus-format metrics returned

## Design Reference

From `docs/plans/2026-03-14-code-context-retrieval-design.md`:

- **Section 6**: REST API (Query Service :8000)
- Endpoints defined:
  - POST `/api/v1/query` - FR-005/006/007/012, API Key auth
  - GET `/api/v1/query` - FR-005/012, API Key auth
  - GET `/api/v1/health` - No auth
  - GET `/api/v1/metrics` - No auth
- Tech: FastAPI, uvicorn, pydantic

## Implementation Tasks

### Task 1: Fix Import Bug in dependencies.py
- **File**: `src/query/dependencies.py`
- **Issue**: Imports `get_es_client`, `get_qdrant_client` but functions are `get_elasticsearch`, `get_qdrant`
- **Fix**: Update imports to use correct function names

### Task 2: Run Tests to Verify Implementation
- **Command**: `pytest tests/test_query_api.py -v`
- **Expected**: All tests pass
- **Coverage**: Verify coverage >= 90%

### Task 3: Verify No Regressions
- **Command**: `pytest --cov=src --cov-branch --cov-report=term-missing`
- **Expected**: No regressions, coverage maintained

## Files Modified

1. `src/query/dependencies.py` - Fix import names
2. `tests/test_query_api.py` - Test already exists, verify passes

## Dependencies

All satisfied (Features 13, 14, 15, 16 all passing)

## Notes

- The query endpoints (`POST /api/v1/query`, `GET /api/v1/query`) are already implemented
- Health and metrics endpoints already implemented
- Repo management endpoints partially implemented (reindex not - that's Feature #23)
- Tests exist and cover all verification steps
- The only blocker is the import bug
