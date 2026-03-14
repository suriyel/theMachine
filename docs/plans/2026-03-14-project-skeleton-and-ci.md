# Plan: Project Skeleton and CI (Feature #1)

**Date**: 2026-03-14
**Feature**: #1 — Project Skeleton and CI
**Priority**: high
**Dependencies**: none
**Design Reference**: docs/plans/2026-03-14-code-context-retrieval-design.md § 3 (Architecture), § 8 (Dependencies)

## Context

Foundation infrastructure feature establishing project directory structure, dependency management, CI workflow, and storage client abstractions for PostgreSQL, Redis, Qdrant, and Elasticsearch. All subsequent features depend on this skeleton.

## Design Alignment

The design document (§3 Architecture, §8 Dependencies) specifies:
- Two-service architecture: Indexing Service + Query Service
- Storage layer: PostgreSQL (metadata), Redis (broker + cache), Qdrant (vectors), Elasticsearch (keywords)
- Python 3.11+ with FastAPI, SQLAlchemy async, and async clients for all storage systems

**Key classes from design**:
- `src/shared/db/session.py` — SQLAlchemy async session factory
- `src/shared/clients/__init__.py` — Storage client abstractions (PostgreSQL, Redis, Qdrant, Elasticsearch)

**Third-party deps (from §8)**:
- `sqlalchemy[asyncio]` ^2.0.36 — ORM + async
- `asyncpg` ^0.30.0 — PostgreSQL async driver
- `redis` ^5.2.0 — Redis client
- `qdrant-client` ^1.12.0 — Qdrant client
- `elasticsearch[async]` ^8.17.0 — Elasticsearch async client

**Deviations**: None. Plan follows approved design exactly.

## SRS Requirement

This is an infrastructure feature derived from the design architecture. No direct FR trace, but enables all FR-001 through FR-018.

**Verification Steps (from feature-list.json)**:
1. Given the project root, when checking directory structure, then src/, tests/, docs/, examples/, scripts/ directories exist
2. Given pyproject.toml exists, when running pip install -e ., then all dependencies install without error
3. Given .github/workflows/ci.yml exists, when pushed to GitHub, then CI workflow runs pytest and passes
4. Given storage clients module, when testing PostgreSQL connection with valid DATABASE_URL, then connection succeeds
5. Given storage clients module, when testing Redis connection with valid REDIS_URL, then ping returns PONG
6. Given storage clients module, when testing Qdrant connection with valid QDRANT_URL, then health check returns 200
7. Given storage clients module, when testing Elasticsearch connection with valid ELASTICSEARCH_URL, then cluster health returns green/yellow

## Tasks

### Task 1: Write failing tests for storage clients
**Files**: `tests/test_storage_clients.py` (create)
**Steps**:
1. Create test file with imports for pytest, pytest-asyncio
2. Write test cases covering each verification step:
   - Test `test_directory_structure_exists`: verify src/, tests/, docs/, examples/, scripts/ exist
   - Test `test_postgres_connection`: async test connecting to PostgreSQL with DATABASE_URL
   - Test `test_redis_connection`: async test ping returns PONG
   - Test `test_qdrant_connection`: async test health check returns ok
   - Test `test_elasticsearch_connection`: async test cluster health returns green/yellow
3. Run: `pytest tests/test_storage_clients.py -v`
4. **Expected**: All tests FAIL (no implementation yet)
5. **Expected**: Tests fail for the RIGHT REASON (import error or connection failure, not syntax error)

### Task 2: Implement storage client abstractions
**Files**:
- `src/shared/clients/postgres.py` (create)
- `src/shared/clients/redis.py` (create)
- `src/shared/clients/qdrant.py` (create)
- `src/shared/clients/elasticsearch.py` (create)
- `src/shared/clients/__init__.py` (modify)

**Steps**:
1. Create `src/shared/clients/postgres.py`:
   - `get_postgres_engine()` function returning async SQLAlchemy engine
   - `get_postgres_session()` async context manager
   - `check_postgres_connection()` async function for health check
2. Create `src/shared/clients/redis.py`:
   - `get_redis_client()` function returning Redis client
   - `check_redis_connection()` async function that pings and returns PONG
3. Create `src/shared/clients/qdrant.py`:
   - `get_qdrant_client()` function returning QdrantClient
   - `check_qdrant_connection()` async function for health check
4. Create `src/shared/clients/elasticsearch.py`:
   - `get_elasticsearch_client()` function returning AsyncElasticsearch
   - `check_elasticsearch_connection()` async function for cluster health
5. Update `src/shared/clients/__init__.py` to export all client functions
6. Run: `pytest tests/test_storage_clients.py -v`
7. **Expected**: All tests PASS

### Task 3: Coverage Gate
**Steps**:
1. Run: `pytest tests/test_storage_clients.py --cov=src/shared/clients --cov-branch --cov-report=term-missing -v`
2. Check: line coverage >= 90%
3. Check: branch coverage >= 80%
4. **If BELOW threshold**: add additional test cases for error paths
5. **Expected**: Coverage meets thresholds
6. Record coverage report output as evidence

### Task 4: Refactor for clean interfaces
**Files**: `src/shared/clients/*.py` (modify)
**Steps**:
1. Ensure consistent error handling across all clients (raise ConnectionError with descriptive message)
2. Ensure consistent async patterns (all check functions are async)
3. Add docstrings to all public functions
4. Run: `pytest tests/test_storage_clients.py -v`
5. **Expected**: All tests still PASS

### Task 5: Mutation Gate
**Steps**:
1. Run: `mutmut run --paths-to-mutate=src/shared/clients/`
2. Check: mutation score >= 80%
3. **If BELOW threshold**: improve test assertions to kill surviving mutants
4. **Expected**: Mutation score meets threshold
5. Record mutation report output as evidence

### Task 6: Verify CI workflow and directory structure
**Files**: `.github/workflows/ci.yml` (verify), project directories (verify)
**Steps**:
1. Verify directories exist: src/, tests/, docs/, examples/, scripts/
2. Verify `.github/workflows/ci.yml` includes:
   - pytest job
   - coverage reporting
   - PostgreSQL and Redis services for integration tests
3. Run: `pytest tests/ -v` (full suite)
4. **Expected**: All tests PASS
5. Add test for directory structure to `tests/test_skeleton.py` if not present

### Task 7: Create example
**Files**: `examples/01-storage-clients.py` (create)
**Steps**:
1. Create example demonstrating:
   - Loading environment config
   - Connecting to each storage system
   - Running health checks
2. Update `examples/README.md`
3. Run the example to verify it works

## Verification
- [x] All verification_steps from feature spec covered by tests
- [ ] All tests pass
- [ ] Coverage meets thresholds (line >= 90%, branch >= 80%)
- [ ] Mutation score meets threshold (>= 80%)
- [ ] No regressions on existing features
- [ ] Example is runnable
