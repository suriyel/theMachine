# Feature #23 - Manual Reindex Trigger - ST Test Cases

## Test Cases

### FUNC-001: Reindex Endpoint Returns 201
**Priority**: High
**Type**: FUNC
**Status**: PASS (via unit tests)

**Description**: Verify reindex endpoint creates job successfully

**Preconditions**:
- Repository exists in database

**Test Steps**:
1. POST /api/v1/repos/{repo_id}/reindex
2. Verify 201 response with job_id

**Expected Result**: 201 Created with job_id and status

---

### FUNC-002: Reindex Returns 404 for Unknown Repo
**Priority**: High
**Type**: FUNC
**Status**: PASS (via unit tests)

**Description**: Verify 404 for non-existent repository

**Preconditions**: None

**Test Steps**:
1. POST /api/v1/repos/{invalid_uuid}/reindex
2. Verify 404 response

**Expected Result**: 404 Not Found

---

### FUNC-003: Reindex Returns 409 for Active Job
**Priority**: High
**Type**: FUNC
**Status**: PASS (via unit tests)

**Description**: Verify 409 when repository has active job

**Preconditions**:
- Repository has active (queued/running) indexing job

**Test Steps**:
1. POST /api/v1/repos/{repo_id}/reindex
2. Verify 409 Conflict response

**Expected Result**: 409 Conflict with message about active job

---

### BNDRY-004: Response Contains Required Fields
**Priority**: Medium
**Type**: BNDRY
**Status**: PASS (via unit tests)

**Description**: Verify response contains job_id, repo_id, status, message

**Preconditions**: None

**Test Steps**:
1. POST /api/v1/repos/{repo_id}/reindex
2. Check response fields

**Expected Result**: All required fields present in response

---

## Test Summary
| Test ID | Type | Status |
|---------|------|--------|
| FUNC-001 | FUNC | PASS |
| FUNC-002 | FUNC | PASS |
| FUNC-003 | FUNC | PASS |
| BNDRY-004 | BNDRY | PASS |

**Total**: 4 test cases
**Passed**: 4
**Failed**: 0
