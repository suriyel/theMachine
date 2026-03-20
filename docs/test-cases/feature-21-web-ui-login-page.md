# Feature #21 - Web UI Login Page - ST Test Cases

## Test Cases

### FUNC-001: Login Page Rendering
**Priority**: High
**Type**: FUNC
**Status**: PASS (via unit tests)

**Description**: Verify login page renders with required elements

**Preconditions**: None

**Test Steps**:
1. Navigate to /login
2. Verify API key input field is present
3. Verify Sign In button is present

**Expected Result**: Login page loads with password-masked API key input and Sign In button

---

### FUNC-002: Valid API Key Login
**Priority**: High
**Type**: FUNC
**Status**: PASS (via unit tests)

**Description**: Verify valid API key grants access and redirects to search

**Preconditions**:
- Valid API key exists in database

**Test Steps**:
1. Enter valid API key in input field
2. Click Sign In button
3. Verify redirect to /search
4. Verify session cookie is set

**Expected Result**: 302 redirect to /search, session cookie created

---

### FUNC-003: Invalid API Key Rejection
**Priority**: High
**Type**: FUNC
**Status**: PASS (via unit tests)

**Description**: Verify invalid API key shows error message

**Preconditions**: None

**Test Steps**:
1. Enter invalid API key in input field
2. Click Sign In button
3. Verify error message displayed

**Expected Result**: Error message "Invalid API key" appears below input

---

### FUNC-004: Empty Input Validation
**Priority**: High
**Type**: FUNC
**Status**: PASS (via unit tests)

**Description**: Verify empty input shows validation error

**Preconditions**: None

**Test Steps**:
1. Leave API key input empty
2. Click Sign In button
3. Verify validation error appears

**Expected Result**: Error message "API key is required" appears

---

### BNDRY-005: Already Authenticated Redirect
**Priority**: Medium
**Type**: BNDRY
**Status**: PASS (via unit tests)

**Description**: Verify authenticated users are redirected to search

**Preconditions**: User has valid session

**Test Steps**:
1. Navigate to /login with session cookie
2. Verify redirect to /search

**Expected Result**: 302 redirect to /search

---

### SEC-006: Password Masking
**Priority**: High
**Type**: SEC
**Status**: PASS (via unit tests)

**Description**: Verify API key is not visible in input

**Preconditions**: None

**Test Steps**:
1. Navigate to /login
2. Inspect API key input type
3. Verify type is "password"

**Expected Result**: Input type is password (masked)

---

### SEC-007: Session Cookie Security
**Priority**: High
**Type**: SEC
**Status**: PASS (via unit tests)

**Description**: Verify session cookie has secure flags

**Preconditions**: None

**Test Steps**:
1. Submit valid credentials
2. Inspect session cookie in response

**Expected Result**: Cookie has httponly=True, samesite=lax

---

## Test Summary
| Test ID | Type | Status |
|---------|------|--------|
| FUNC-001 | FUNC | PASS |
| FUNC-002 | FUNC | PASS |
| FUNC-003 | FUNC | PASS |
| FUNC-004 | FUNC | PASS |
| BNDRY-005 | BNDRY | PASS |
| SEC-006 | SEC | PASS |
| SEC-007 | SEC | PASS |

**Total**: 7 test cases
**Passed**: 7
**Failed**: 0
