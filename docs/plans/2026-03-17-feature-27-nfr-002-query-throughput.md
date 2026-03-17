# Feature #27 Plan — NFR-002: Query Throughput

## Feature Summary
- **ID**: 27
- **Title**: NFR-002: Query Throughput
- **Category**: non-functional
- **Priority**: high
- **Dependencies**: Feature 17 (REST API Endpoints) ✓

## SRS Requirement
- **NFR-002**: Query service shall sustain target throughput
- **Target**: ≥ 1000 QPS sustained; ≥ 2000 QPS peak burst
- **Measurement**: Load test measuring sustained throughput over 10-minute window

## Verification Steps
1. Given k6 load test targeting 1000 QPS for 10 minutes, when measuring throughput, then sustained >= 1000 QPS
2. Given k6 load test targeting 2000 QPS burst, when measuring peak, then peak >= 2000 QPS achieved

## Design Reference
- Design doc § 2.1: NFR-002 (≥ 1000 QPS) → Gunicorn multi-worker (4-8 workers/node) × N query nodes + load balancer
- The locustfile.py already exists for load testing

## Implementation Plan

### 1. Create Load Test Runner Script
Create `scripts/run_throughput_test.py` that:
- Runs locust in headless mode with configurable parameters
- Supports sustained load test (1000 QPS for 10 minutes)
- Supports burst load test (2000 QPS)
- Parses locust output to extract throughput metrics
- Returns exit code 0 if thresholds met, 1 if failed

### 2. Create Unit Tests for Load Test Runner
Create `tests/test_nfr02_throughput.py` with:
- Test that runner script accepts correct parameters
- Test that runner correctly parses locust output
- Test threshold validation logic

### 3. Document Execution Procedure
Update `docs/test-cases/feature-27-nfr-002-query-throughput.md` with:
- Prerequisites (services running, indexed data)
- Test execution commands
- Expected results

### 4. Create Example Usage
Create `examples/27-query-throughput.py` demonstrating:
- How to run the throughput test
- How to interpret results

## Technical Details

### Load Test Tool
- Use locust (already available in project)
- Run in headless mode for CI/CD integration
- Output results in parseable format

### Test Parameters
- Sustained test: 1000 users, 10 minute duration
- Burst test: 2000 users, spike over 30 seconds

### Threshold Validation
- Sustained: RPS >= 1000 for 10 minutes
- Peak: RPS >= 2000 at any point during burst test

## Files to Create/Modify
1. `scripts/run_throughput_test.py` (new) - Load test runner
2. `tests/test_nfr02_throughput.py` (new) - Unit tests
3. `docs/test-cases/feature-27-nfr-002-query-throughput.md` (new) - ST test case
4. `examples/27-query-throughput.py` (new) - Example

## Dependencies
- Feature 17 (REST API Endpoints) must be passing
- Services: PostgreSQL, Redis, Qdrant, Elasticsearch, Query Service

## Notes
- Load testing requires actual services running
- Results may vary based on hardware
- For CI, use reduced load (e.g., 100 QPS for 1 minute) as smoke test
