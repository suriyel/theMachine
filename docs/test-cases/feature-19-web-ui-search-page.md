# Feature #19 - Web UI Search Page - ST Test Cases

## Test Cases

### FUNC-001: Search Page Authentication
**Priority**: High
**Type**: FUNC
**Status**: PASS (via unit tests)

**Description**: Verify authenticated users can access the search page

**Preconditions**:
- User has valid API key
- User is authenticated via session cookie

**Test Steps**:
1. Navigate to /search with valid session cookie
2. Verify search page loads successfully
3. Verify search input, language filters, and results area are visible

**Expected Result**: Search page loads with search input and filter components visible

---

### FUNC-002: Search Query Execution
**Priority**: High
**Type**: FUNC
**Status**: PASS (via unit tests)

**Description**: Verify search query returns results from the query pipeline

**Preconditions**:
- User is authenticated
- Query handler is properly configured

**Test Steps**:
1. Enter query text "WebClient timeout"
2. Press Enter or click search
3. Verify results are displayed

**Expected Result**: Results from retrieval pipeline displayed with repository, file path, symbol, score, and content

---

### FUNC-003: Unauthenticated Redirect
**Priority**: High
**Type**: FUNC
**Status**: PASS (via unit tests)

**Description**: Verify unauthenticated users are redirected to login

**Test Steps**:
1. Navigate to /search without session cookie
2. Verify redirect to /login

**Expected Result**: 302 redirect to /login page

---

### BNDRY-004: Empty Query State
**Priority**: Medium
**Type**: BNDRY
**Status**: PASS (via unit tests)

**Description**: Verify initial state before any search

**Preconditions**:
- User is authenticated

**Test Steps**:
1. Navigate to /search without query parameter
2. Verify initial empty state is displayed

**Expected Result**: Empty state with "Search code context" heading and instructions

---

### BNDRY-005: No Results State
**Priority**: Medium
**Type**: BNDRY
**Status**: PASS (via unit tests)

**Description**: Verify "no results found" message when query has no matches

**Preconditions**:
- User is authenticated
- Query returns empty results

**Test Steps**:
1. Enter query that returns no results
2. Verify no results message displayed

**Expected Result**: Empty state with "No results found" message

---

### BNDRY-006: Language Filter Selection
**Priority**: Medium
**Type**: BNDRY
**Status**: PASS (via unit tests)

**Description**: Verify language filter chips are selectable

**Preconditions**:
- User is authenticated

**Test Steps**:
1. Click on "Python" filter chip
2. Verify chip is visually selected
3. Verify URL includes lang=python parameter

**Expected Result**: Selected chip has different styling, query includes language filter

---

### BNDRY-007: Unsupported Language Error
**Priority**: Medium
**Type**: BNDRY
**Status**: PASS (via unit tests)

**Description**: Verify error message for unsupported language

**Preconditions**:
- User is authenticated

**Test Steps**:
1. Add unsupported language filter (e.g., ?lang=ruby)
2. Verify error message appears

**Expected Result**: Error alert with supported languages list

---

### SEC-008: Session Security
**Priority**: High
**Type**: SEC
**Status**: PASS (via unit tests)

**Description**: Verify session cookies are secure

**Preconditions**: None

**Test Steps**:
1. Verify session cookie has httponly flag
2. Verify session cookie has samesite=lax

**Expected Result**: Session cookie properly secured

---

### SEC-009: Login Validation
**Priority**: High
**Type**: SEC
**Status**: PASS (via unit tests)

**Description**: Verify invalid API keys are rejected

**Preconditions**: None

**Test Steps**:
1. Enter invalid API key on login page
2. Submit form
3. Verify error message displayed

**Expected Result**: Error message "Invalid API key" shown

---

## Test Summary
| Test ID | Type | Status |
|---------|------|--------|
| FUNC-001 | FUNC | PASS |
| FUNC-002 | FUNC | PASS |
| FUNC-003 | FUNC | PASS |
| BNDRY-004 | BNDRY | PASS |
| BNDRY-005 | BNDRY | PASS |
| BNDRY-006 | BNDRY | PASS |
| BNDRY-007 | BNDRY | PASS |
| SEC-008 | SEC | PASS |
| SEC-009 | SEC | PASS |

**Total**: 9 test cases
**Passed**: 9
**Failed**: 0
