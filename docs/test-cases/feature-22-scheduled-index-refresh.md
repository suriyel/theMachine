# Feature #22 - Scheduled Index Refresh - ST Test Cases

## Test Cases

### FUNC-001: Celery Beat Schedule Configured
**Priority**: High
**Type**: FUNC
**Status**: PASS (via unit tests)

**Description**: Verify Celery Beat is configured with weekly schedule

**Preconditions**: None

**Test Steps**:
1. Check Celery configuration for beat_schedule
2. Verify weekly-index-refresh task is defined

**Expected Result**: Beat schedule contains weekly-index-refresh task

---

### FUNC-002: Refresh Task Imports Successfully
**Priority**: High
**Type**: FUNC
**Status**: PASS (via unit tests)

**Description**: Verify refresh task can be imported

**Preconditions**: None

**Test Steps**:
1. Import refresh_all_repositories from tasks module
2. Verify task is a Celery task

**Expected Result**: Task imported successfully

---

### FUNC-003: Refresh Task Queues All Repositories
**Priority**: High
**Type**: FUNC
**Status**: PASS (via unit tests)

**Description**: Verify refresh task creates jobs for all registered repositories

**Preconditions**: None

**Test Steps**:
1. Call refresh_all_repositories task
2. Verify jobs are created for each repository

**Expected Result**: Jobs queued for all repositories

---

### BNDRY-004: No Repositories Handled Gracefully
**Priority**: Medium
**Type**: BNDRY
**Status**: PASS (via unit tests)

**Description**: Verify task handles empty repository list

**Preconditions**: No repositories registered

**Test Steps**:
1. Call refresh_all_repositories when no repos exist
2. Verify task completes without error

**Expected Result**: Task returns success with "No repositories to refresh"

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
