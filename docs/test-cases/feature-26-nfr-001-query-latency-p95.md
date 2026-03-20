# Feature 26: NFR-001 Query Latency P95 - ST Test Cases

## Header

| Field | Value |
|-------|-------|
| Feature ID | 26 |
| Feature Title | NFR-001: Query Latency P95 |
| Related Requirements | NFR-001 |
| SRS Reference | docs/plans/2026-03-14-code-context-retrieval-srs.md |
| Design Reference | docs/plans/2026-03-14-code-context-retrieval-design.md |
| Date | 2026-03-17 |
| Standard | ISO/IEC/IEEE 29119-3 |

## Summary

| Category | Count |
|----------|-------|
| Functional (FUNC) | 1 |
| Boundary (BNDRY) | 1 |
| Performance (PERF) | 1 |
| **Total** | **3** |

## Test Cases

### ST-PERF-026-001: P95 Latency Under Load

| Field | Value |
|-------|-------|
| Case ID | ST-PERF-026-001 |
| Category | Performance |
| Feature | NFR-001 |
| Verification Step | Given k6 load test with 1000 concurrent users for 10 minutes, when measuring P95 latency, then P95 <= 1000ms |

**Preconditions:**
- Query Service running on http://localhost:8000
- PostgreSQL, Redis, Qdrant, Elasticsearch running
- At least one repository indexed with code chunks

**Test Steps:**

| Step | Operation | Expected Result |
|------|-----------|-----------------|
| 1 | Start Locust with 1000 users | Locust starts |
| 2 | Run load test for 10 minutes | Test completes |
| 3 | Extract P95 latency from report | P95 <= 1000ms |

**Execution Command:**
```bash
locust -f locustfile.py --headless -u 1000 -r 100 -t 10m --host http://localhost:8000
```

**Expected Result:** P95 latency <= 1000ms

**Status:** PENDING - Requires infrastructure

---

### ST-FUNC-026-001: Query Cache Hit

| Field | Value |
|-------|-------|
| Case ID | ST-FUNC-026-001 |
| Category | Functional |
| Feature | NFR-001 (Redis Query Cache) |
| Verification Step | Given repeated identical query, when cache is enabled, then second request returns cached result |

**Preconditions:**
- Query Service running with Redis cache enabled
- API key configured

**Test Steps:**

| Step | Operation | Expected Result |
|------|-----------|-----------------|
| 1 | Submit query "how to configure WebClient timeout" | 200 OK, results returned |
| 2 | Submit identical query again | 200 OK, results returned faster |
| 3 | Verify response includes cached indicator | Latency < 50ms on cache hit |

**Expected Result:** Cache hit returns result in < 50ms

**Status:** PENDING - Requires running services

---

### ST-BNDRY-026-001: Cache Miss on Different Query

| Field | Value |
|-------|-------|
| Case ID | ST-BNDRY-026-001 |
| Category | Boundary |
| Feature | NFR-001 (Redis Query Cache) |
| Verification Step | Given different query, when cache miss occurs, then handler computes result normally |

**Preconditions:**
- Query Service running with Redis cache enabled

**Test Steps:**

| Step | Operation | Expected Result |
|------|-----------|-----------------|
| 1 | Submit query "Java RestTemplate example" | 200 OK |
| 2 | Submit different query "Python Flask routing" | 200 OK, computed fresh |
| 3 | Verify second result is different | Different content returned |

**Expected Result:** Different queries produce different results

**Status:** PENDING - Requires running services

---

## Traceability Matrix

| Case ID | Requirement | verification_step | Automated Test | Result |
|---------|-------------|-------------------|----------------|--------|
| ST-PERF-026-001 | NFR-001 | P95 <= 1000ms @ 1000 QPS | locust load test | PENDING |
| ST-FUNC-026-001 | NFR-001 | Cache hit returns faster | Manual/auto test | PENDING |
| ST-BNDRY-026-001 | NFR-001 | Different query = cache miss | Manual/auto test | PENDING |

## Real Test Case Execution Summary

| Type | Total | Passed | Failed | Pending |
|------|-------|--------|--------|---------|
| Real | 3 | 0 | 0 | 3 |
| Mock | 0 | 0 | 0 | 0 |

## Notes

- **Infrastructure Limitation**: This feature requires Docker to run load testing infrastructure (PostgreSQL, Redis, Qdrant, Elasticsearch). Docker requires sudo permission which is not available.
- **Locust File Created**: locustfile.py has been created at project root for load testing when infrastructure becomes available.
- **Redis Cache Implemented**: The query cache module (src/query/cache.py) has been implemented and integrated into the query endpoint. Unit tests pass with 90% coverage.
- **Execution Command**: When services are available, run: `locust -f locustfile.py --headless -u 1000 -r 100 -t 10m --host http://localhost:8000`
