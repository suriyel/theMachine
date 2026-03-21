# Feature Detailed Design: Manual Reindex Trigger (Feature #22)

**Date**: 2026-03-22
**Feature**: #22 — Manual Reindex Trigger
**Priority**: high
**Dependencies**: #17 (REST API Endpoints)
**Design Reference**: docs/plans/2026-03-21-code-context-retrieval-design.md § 4.5 (Authentication & API)
**SRS Reference**: FR-020

## Context

REST endpoint `POST /api/v1/repos/{repo_id}/reindex` that allows administrators to trigger immediate re-indexing of a specific repository. Already implemented as part of Feature #17 — this design formalizes the existing implementation.

## Design Alignment

- **Key classes**: `repos_router` (existing FastAPI router), `ReindexResponse` schema, `IndexJob` model
- **Interaction flow**: Admin → POST reindex → auth check → DB lookup → create IndexJob → return job_id
- **Third-party deps**: FastAPI, SQLAlchemy (async)
- **Deviations**: None — implementation matches design §4.5 `RepoManager.trigger_reindex`

## SRS Requirement

### FR-020: Manual Reindex Trigger
**Priority**: Must
**EARS**: When an administrator sends a reindex request for a specific repository, the system shall queue an immediate re-indexing job for that repository.
**Acceptance Criteria**:
- Given a POST request to `/api/v1/repos/{repo_id}/reindex` with valid admin credentials, when processed, then the system shall queue an indexing job and return the job ID with status "queued".
- Given a reindex request for a non-existent repository, then the system shall return 404.

**Verification Steps** (from feature-list.json):
- VS-1: Given a POST to /api/v1/repos/{repo_id}/reindex with valid admin API key, when processed, then an indexing job is queued and the response contains job_id with status='queued'
- VS-2: Given a reindex request for a non-existent repository, when processed, then it returns 404
- VS-3: Given a reindex request with a read-only API key, when processed, then it returns 403 Forbidden

## Component Data-Flow Diagram

N/A — single-endpoint feature. The reindex endpoint is a thin REST handler in `repos_router` that creates an IndexJob. See Interface Contract below.

## Interface Contract

| Method | Signature | Preconditions | Postconditions | Raises |
|--------|-----------|---------------|----------------|--------|
| `reindex_repo` | `async reindex_repo(repo_id: UUID, request: Request, api_key: ApiKey, auth_middleware: AuthMiddleware) -> ReindexResponse` | Valid admin API key, repo_id is valid UUID | IndexJob created with status='pending', response contains job_id + repo_id + status | HTTPException(404) if repo not found, HTTPException(403) via require_permission if not admin |

## Internal Sequence Diagram

N/A — single-function endpoint, error paths documented in Algorithm error handling table.

## Algorithm / Core Logic

### reindex_repo

#### Pseudocode

```
FUNCTION reindex_repo(repo_id, request, api_key, auth_middleware) -> ReindexResponse
  // Step 1: Permission check (delegated to require_permission)
  require_permission(api_key, "reindex", auth_middleware)

  // Step 2: Look up repository
  repo = SELECT * FROM repository WHERE id = repo_id
  IF repo is None THEN RAISE HTTPException(404, "Repository not found")

  // Step 3: Determine branch and create job
  branch = repo.indexed_branch OR repo.default_branch OR "main"
  job = IndexJob(repo_id=repo.id, branch=branch, status="pending")
  session.add(job)
  session.commit()

  RETURN ReindexResponse(job_id=job.id, repo_id=repo.id, status=job.status)
END
```

#### Boundary Decisions

| Parameter | Min | Max | Empty/Null | At boundary |
|-----------|-----|-----|------------|-------------|
| repo_id | valid UUID | valid UUID | FastAPI returns 422 | Non-existent UUID: returns 404 |

#### Error Handling

| Condition | Detection | Response | Recovery |
|-----------|-----------|----------|----------|
| Repo not found | query returns None | HTTPException(404) | Client retries with valid ID |
| Not admin | require_permission raises | HTTPException(403) | Client uses admin key |
| Invalid UUID format | FastAPI path validation | 422 Unprocessable Entity | Client fixes UUID |

## State Diagram

N/A — stateless endpoint. IndexJob state managed by Feature #2.

## Test Inventory

| ID | Category | Traces To | Input / Setup | Expected | Kills Which Bug? |
|----|----------|-----------|---------------|----------|-----------------|
| A1 | happy path | VS-1, FR-020 AC-1 | POST with admin key, existing repo | 200, job_id + status="pending" | Missing job creation |
| B1 | error | VS-2, FR-020 AC-2 | POST with non-existent repo_id | 404 | Missing existence check |
| B2 | error | VS-3 | POST with read-only API key | 403 | Missing permission check |
| C1 | boundary | §Algorithm | POST with invalid UUID format | 422 | Missing input validation |

**Negative ratio**: 3/4 = 75% ✓ >= 40%

## Tasks

### Task 1: Verify existing tests
**Files**: `tests/test_rest_api.py`
**Steps**:
1. Confirm tests T08, T21, T24 cover all 4 test inventory rows
2. Run: `pytest tests/test_rest_api.py -k "reindex" -v`
3. **Expected**: All pass

### Task 2: Coverage Gate
1. Run: `pytest --cov=src/query/api/v1/endpoints/repos --cov-branch --cov-report=term-missing tests/test_rest_api.py`
2. Check thresholds.

### Task 3: Mutation Gate
1. Run: `mutmut run src.query.api.v1.endpoints.repos`
2. Check threshold.

## Verification Checklist
- [x] All verification_steps traced to Interface Contract postconditions
- [x] All verification_steps traced to Test Inventory rows
- [x] Algorithm pseudocode covers the endpoint logic
- [x] Boundary table covers all parameters
- [x] Error handling table covers all Raises entries
- [x] Test Inventory negative ratio >= 40% (75%)
- [x] Every skipped section has explicit "N/A — [reason]"
