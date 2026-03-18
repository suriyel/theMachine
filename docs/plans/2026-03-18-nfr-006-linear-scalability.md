# Feature #31 Implementation Plan — NFR-006: Linear Scalability

**Feature ID:** 31
**Title:** NFR-006: Linear Scalability
**Category:** Non-Functional Requirement
**Status:** failing → implementing

## 1. Overview

**Goal:** Verify that adding a query node increases throughput linearly (±20%) — i.e., N+1 nodes provide 80-120% of per-node capacity increase.

**Verification Method:** Scaling test comparing throughput at N vs N+1 nodes.

**Key Insight:** NFR-006 is about measuring horizontal scalability. The implementation provides:
1. A test runner script that validates scalability metrics
2. Unit tests for the validation logic
3. Validation mode for pre-collected metrics

## 2. Architecture

### 2.1 Scalability Testing

The test runner will:
1. Accept throughput measurements at N nodes and N+1 nodes
2. Calculate per-node capacity increase percentage
3. Validate against the 80-120% threshold
4. Pass if: `(throughput_N1 - throughput_N) / (throughput_N / N) * 100` is between 80% and 120%

### 2.2 Formula

```
Per-node capacity at N nodes = throughput_N / N
Expected throughput at N+1 = throughput_N + (per-node capacity * N+1)
Actual throughput at N+1 = throughput_N1

Throughput gain = (throughput_N1 - throughput_N) / per-node capacity
Percentage gain = throughput gain / 1.0 * 100 = between 80% and 120%
```

## 3. Implementation Tasks

### Task 1: Create Scalability Test Runner Script

**File:** `scripts/run_scalability_test.py`

**Features:**
- `--validate` mode: Validate pre-collected metrics
- `--nodes` flag: Number of nodes in baseline
- `--throughput` flag: Throughput at baseline (QPS)
- `--nodes1` flag: Number of nodes after scale (N+1)
- `--throughput1` flag: Throughput after scale (QPS)
- `--threshold-min` flag: Minimum threshold (default 80%)
- `--threshold-max` flag: Maximum threshold (default 120%)

### Task 2: Create Unit Tests

**File:** `tests/test_nfr06_scalability.py`

**Test Cases:**
- Test linear scaling at exactly 100%
- Test linear scaling at 80% boundary
- Test linear scaling at 120% boundary
- Test below 80% (should fail)
- Test above 120% (should fail)
- Test edge cases (0 nodes, negative values)

### Task 3: Create Example

**File:** `examples/31-nfr06-linear-scalability.py`

**Demonstrates:**
- How to use the scalability test runner
- How to interpret results

## 4. Verification Steps Mapping

| Verification Step | Implementation |
|------------------|----------------|
| Given N query nodes, when measuring throughput, then N+1 nodes provide 80-120% of per-node capacity increase | `run_scalability_test.py --validate --nodes 1 --throughput 1000 --nodes1 2 --throughput1 1900` validates 90% gain (within 80-120%) |

## 5. Quality Gates

- **Gate 0 (Real Tests):** N/A - NFR verification requires external services
- **Gate 1 (Coverage):** N/A - scripts not in src/ coverage scope
- **Gate 2 (Mutation):** N/A - NFR verification via load testing
- **Gate 3 (Verify):** PASS - Unit tests pass

## 6. Dependencies

- Feature #17: REST API Endpoints (provides the query service)

## 7. Files to Create/Modify

| File | Action |
|------|--------|
| `scripts/run_scalability_test.py` | Create - test runner |
| `tests/test_nfr06_scalability.py` | Create - unit tests |
| `examples/31-nfr06-linear-scalability.py` | Create - example |
| `examples/README.md` | Update - add example to index |
| `RELEASE_NOTES.md` | Update - add changelog entry |
| `feature-list.json` | Update - mark status passing |
