# Feature #25 - Query Logging - ST Test Cases

## Test Cases

### FUNC-001: Query Logged on Success
**Priority**: High
**Type**: FUNC
**Status**: PASS (via unit tests)

**Description**: Verify query is logged to database on success

**Preconditions**:
- Valid API key exists in database
- Database is accessible

**Test Steps**:
1. Submit a valid query via POST /api/v1/query
2. Verify QueryLog record is created with all required fields

**Expected Result**: QueryLog record created with query_text, latency_ms, correlation_id

---

### FUNC-002: Query Logged on Error
**Priority**: High
**Type**: FUNC
**Status**: PASS (via unit tests)

**Description**: Verify query errors are logged with correlation ID

**Preconditions**:
- Valid API key exists

**Test Steps**:
1. Submit an invalid query that triggers an error
2. Verify error is logged with same correlation_id for tracing

**Expected Result**: Error logged with correlation_id for tracing

---

### FUNC-003: Correlation ID Generated
**Priority**: High
**Type**: FUNC
**Status**: PASS (via unit tests)

**Description**: Verify correlation ID is generated for each request

**Preconditions**: None

**Test Steps**:
1. Submit a query
2. Check the correlation_id field in the response or logs

**Expected Result**: UUID correlation_id is generated and logged

---

### BNDRY-004: Log Contains All Required Fields
**Priority**: Medium
**Type**: BNDRY
**Status**: PASS (via unit tests)

**Description**: Verify query log contains all required fields

**Preconditions**: None

**Test Steps**:
1. Submit a query with all parameters
2. Verify QueryLog record contains: query_text, query_type, repo_filter, language_filter, result_count, latency_ms, correlation_id

**Expected Result**: All fields populated in QueryLog record

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
