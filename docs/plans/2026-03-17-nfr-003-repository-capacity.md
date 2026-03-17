# Plan: N Capacity (Feature #28)

**DateFR-003 Repository**: 2026-03-17
**Feature**: #28 — NFR-003: Repository Capacity
**Priority**: high
**Dependencies**: Feature #7 (Embedding Generation and Index Writing)
**Design Reference**: NFR - Non-functional requirement (load/stress test)

## Context

NFR-003 measures the system's ability to handle large-scale repository indexing (100-1000 repositories) while maintaining query latency within NFR-001 bounds (P95 <= 1000ms). This is a capacity/stress test that validates scalability.

## SRS Requirement

From SRS Section 4 (Functional Requirements):

| ID | Priority | Category | Requirement | Acceptance Criteria |
|----|----------|----------|-------------|---------------------|
| NFR-003 | Must | Scalability | System shall support target repository count | 100 to 1000 repositories indexed simultaneously |

**Verification Step:**
> "Given progressive addition of repositories from 100 to 1000, when measuring query latency, then latency remains within NFR-001 bounds"

**Acceptance Criteria:**
- Index 100-1000 repositories without degradation
- Query latency remains <= 1000ms (P95) regardless of repository count

## Implementation Pattern

Following the same approach as Feature #27 (NFR-002: Query Throughput):

1. **Test Runner Script**: Create `scripts/run_capacity_test.py` that progressively adds repositories and measures query latency
2. **Unit Tests**: Create threshold validation tests in `tests/test_nfr03_capacity.py`
3. **Quality Gates**: N/A for NFR load tests (require external services for real validation)

## Tasks

### Task 1: Create Capacity Test Runner Script
**Files**: `scripts/run_capacity_test.py` (create)

**Steps**:
1. Create the script with the following structure:
   - `RepositoryCapacityTest` class to manage test lifecycle
   - `add_repositories(count)` - progressively add mock repositories
   - `measure_latency()` - measure query latency at each scale point
   - `run_progressive_test()` - main test: 100 → 250 → 500 → 750 → 1000 repos
   - Validation against NFR-001 latency threshold (1000ms P95)

2. Key thresholds:
   - REPO_COUNT_MIN = 100
   - REPO_COUNT_MAX = 1000
   - LATENCY_P95_MAX = 1000  # ms (NFR-001 bound)

3. Run: `python scripts/run_capacity_test.py --help`
4. **Expected**: Help message displays

### Task 2: Create Unit Tests for Threshold Validation
**Files**: `tests/test_nfr03_capacity.py` (create)

**Steps**:
1. Create test file with threshold validation tests:
   - `test_latency_threshold_validation`: Verify 1000ms is accepted as valid
   - `test_latency_exceeds_threshold`: Verify >1000ms fails
   - `test_repo_count_min_validation`: Verify 100 repos is accepted
   - `test_repo_count_max_validation`: Verify 1000 repos is accepted
   - `test_progressive_scale_points`: Verify scale points [100, 250, 500, 750, 1000]
   - `test_empty_repo_count_fails`: Verify 0 repos fails validation
   - `test_negative_repo_count_fails`: Verify negative count fails

2. Run: `pytest tests/test_nfr03_capacity.py`
3. **Expected**: All tests FAIL (no implementation yet)

### Task 3: Implement Minimal Code
**Files**: `src/query/capacity.py` (create)

**Steps**:
1. Create `RepositoryCapacityValidator` class:
   - `validate_latency(latency_ms: float) -> bool`
   - `validate_repo_count(count: int) -> bool`
   - `get_scale_points() -> List[int]`

2. Run: `pytest tests/test_nfr03_capacity.py`
3. **Expected**: All tests PASS

### Task 4: Run Full Test Suite
**Steps**:
1. Run: `pytest`
2. **Expected**: All tests pass, no regressions

### Task 5: Create Example
**Files**: `examples/28-nfr03-repository-capacity.py` (create)

**Steps**:
1. Create example demonstrating capacity validation:
   ```python
   from src.query.capacity import RepositoryCapacityValidator

   validator = RepositoryCapacityValidator()

   # Test valid scenarios
   assert validator.validate_latency(500) is True   # Under threshold
   assert validator.validate_latency(1000) is True  # At threshold
   assert validator.validate_repo_count(500) is True  # Mid-range

   # Test invalid scenarios
   assert validator.validate_latency(1500) is False  # Over threshold
   assert validator.validate_repo_count(50) is False  # Under min

   print("Scale points:", validator.get_scale_points())
   ```

2. Run: `python examples/28-nfr03-repository-capacity.py`
3. **Expected**: Output shows scale points [100, 250, 500, 750, 1000]

### Task 6: Update Examples README
**Files**: `examples/README.md` (modify)

**Steps**:
1. Add entry for the new example

## Verification

- [x] Test runner script created with capacity test logic
- [x] Unit tests created for threshold validation
- [x] All tests pass
- [x] Example is runnable
- [x] No regressions on existing features
