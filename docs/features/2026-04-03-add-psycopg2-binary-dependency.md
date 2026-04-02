# Feature Detailed Design: Add psycopg2-binary for Celery Worker Sync DB Access (Feature #50)

**Date**: 2026-04-03
**Feature**: #50 — Add psycopg2-binary for Celery worker sync DB access
**Priority**: high
**Category**: bugfix (CONDENSED mode)
**Dependencies**: Feature #21 (Scheduled Index Refresh)
**Design Reference**: docs/plans/2026-03-21-code-context-retrieval-design.md § 4.9.9
**SRS Reference**: FR-019, FR-020

## Context

The Celery worker's `_get_sync_session()` in `src/indexing/scheduler.py` creates a synchronous SQLAlchemy session using `create_engine()` with a `postgresql://` URL. This requires the `psycopg2` driver at runtime, but the project only declares `asyncpg` as a dependency. Any Celery task that touches the database (scheduled reindex, manual reindex) crashes with `ImportError: No module named 'psycopg2'`. The fix is to add `psycopg2-binary>=2.9` to the `[project.optional-dependencies] dev` section of `pyproject.toml`.

## Design Alignment

### System Design § 4.9.9

> **Problem**: Celery worker's `_get_sync_session()` requires a synchronous PostgreSQL driver (`psycopg2`), but only `asyncpg` is installed. Any Celery task touching the DB crashes.
>
> **Fix**: Add `psycopg2-binary>=2.9` to `[project.optional-dependencies] dev` in `pyproject.toml`.

- **Key classes**: No new classes. Single-line change to `pyproject.toml`.
- **Interaction flow**: `reindex_repo_task()` / `scheduled_reindex_all()` → `_get_sync_session()` → `create_engine(sync_url)` → psycopg2 driver loaded by SQLAlchemy.
- **Third-party deps**: `psycopg2-binary>=2.9` (new addition)
- **Deviations**: None.

### Root Cause

`_get_sync_session()` (scheduler.py:17-27) converts the async DATABASE_URL to a sync `postgresql://` scheme and calls `create_engine(sync_url)`. SQLAlchemy's default dialect for `postgresql://` is `psycopg2`. Since `psycopg2` is not in the dependency list, any import attempt at session creation time raises `ImportError`.

## SRS Requirement

### FR-019: Scheduled Index Refresh

**Priority**: Must
**EARS**: While the system is running, the system shall execute repository re-indexing jobs on a configurable cron schedule, defaulting to weekly (Sunday 02:00 UTC).
**Acceptance Criteria**:
- AC-1: Given the default configuration, when a week has elapsed since the last index, then the scheduler shall automatically trigger re-indexing for all registered repositories.
- AC-2: Given a custom cron expression configured for a specific repository, when the cron fires, then that repository shall be re-indexed.
- AC-3: Given a scheduled job that fails, then the system shall log the failure and retry once after 1 hour; if the retry also fails, the system shall log an error and skip until the next scheduled window.
- AC-4: Given a re-index already in progress for a repository when the schedule fires, then the system shall skip the duplicate and log an informational message.

### FR-020: Manual Reindex Trigger

**Priority**: Must
**EARS**: When an administrator sends a reindex request for a specific repository, the system shall queue an immediate re-indexing job for that repository.
**Acceptance Criteria**:
- AC-1: Given a POST request to `/api/v1/repos/{repo_id}/reindex` with valid admin credentials, when processed, then the system shall queue an indexing job and return the job ID with status "queued".
- AC-2: Given a reindex request for a non-existent repository, then the system shall return 404.

## Component Data-Flow Diagram

N/A — single-file configuration change (pyproject.toml), no runtime component collaboration to diagram. The fix enables an existing data flow (`_get_sync_session()` → psycopg2 driver) that was blocked by a missing dependency declaration.

## Interface Contract

This bugfix does not add or modify any public methods. It enables the existing `_get_sync_session()` to function correctly by satisfying its implicit runtime dependency.

| Method | Signature | Preconditions | Postconditions | Raises |
|--------|-----------|---------------|----------------|--------|
| `_get_sync_session` | `_get_sync_session() -> Session` | Given `psycopg2-binary` is installed (via `pip install -e '.[dev]'`) and `DATABASE_URL` env var is set | A valid SQLAlchemy `Session` bound to a sync PostgreSQL engine is returned | `ImportError` if psycopg2 is not installed; `sqlalchemy.exc.OperationalError` if DB unreachable |

**Design rationale**:
- `psycopg2-binary` is chosen over `psycopg2` (source build) to avoid requiring `libpq-dev` / C compiler in the Docker build environment. This aligns with standard practice for development and container environments.
- The dependency is placed in `[project.optional-dependencies] dev` (not core dependencies) because it is only needed by the Celery worker process, which uses the dev install profile.

**Cross-feature contract alignment**: Feature #50 does not appear in Design §6.2 as Provider or Consumer — it is a dependency-level fix, not an API contract change.

## Visual Rendering Contract

N/A — backend-only feature, no visual output.

## Internal Sequence Diagram

N/A — single-class implementation with no internal method delegation. The fix is a dependency declaration, not code logic.

## Algorithm / Core Logic

N/A — no algorithm. The fix is adding one line (`"psycopg2-binary>=2.9"`) to the `dev` optional-dependencies list in `pyproject.toml`. The runtime behavior of `_get_sync_session()` is unchanged; the fix simply ensures its implicit dependency is satisfied.

### Error Handling

| Condition | Detection | Response | Recovery |
|-----------|-----------|----------|----------|
| `psycopg2` not installed (pre-fix state) | `ImportError` raised by SQLAlchemy when `create_engine().connect()` is called | Celery task crashes, exception logged | Install `psycopg2-binary` (this fix) |
| `psycopg2-binary` version too old (<2.9) | Potential incompatibility with PostgreSQL 15+ features | `OperationalError` or silent data issues | Pin `>=2.9` in dependency spec |
| `DATABASE_URL` not set or empty | `create_engine("")` creates invalid engine | `OperationalError` on first query | Set `DATABASE_URL` env var correctly |

## State Diagram

N/A — stateless feature. The dependency declaration has no lifecycle.

## Test Inventory

| ID | Category | Traces To | Input / Setup | Expected | Kills Which Bug? |
|----|----------|-----------|---------------|----------|-----------------|
| A | FUNC/happy | FR-019/FR-020, §Interface Contract | `pip install -e '.[dev]'` completed; `import psycopg2` in Python | Import succeeds without `ImportError` | psycopg2-binary missing from dependency list |
| B | FUNC/happy | FR-019/FR-020, verification_step_2 | `_get_sync_session()` called with valid `DATABASE_URL` set (mocked `create_engine`) | Returns a `Session` object; `create_engine` called with sync URL | _get_sync_session broken due to missing driver |
| C | FUNC/error | §Interface Contract Raises, §Error Handling row 1 | `psycopg2` not importable (simulated via patching) | `ImportError` raised | Silent failure if driver missing but not detected |
| D | BNDRY/edge | §Error Handling row 3 | `DATABASE_URL` is empty string `""` | `create_engine` called with `""`, no crash at session creation (deferred connection) | Crash on missing env var before any DB operation |
| E | BNDRY/dep-spec | §Design Alignment, pyproject.toml | Read `pyproject.toml` `[project.optional-dependencies] dev` list | `"psycopg2-binary>=2.9"` is present in the list | Dependency omitted or wrong version spec |
| F | INTG/db | §Interface Contract + DATABASE_URL | Real PostgreSQL instance available; `_get_sync_session()` called; execute `SELECT 1` | Query returns `1`; session connects successfully | psycopg2 installed but incompatible with actual DB version |
| G | FUNC/error | §Error Handling row 2 | `DATABASE_URL` points to unreachable host | `OperationalError` raised on first query attempt | Missing error propagation on bad connection |

**Negative test ratio**: 3 negative (C, D, G) / 7 total = 43% >= 40% threshold. PASS.

**ATS category coverage check**:
- FR-019 requires: FUNC, BNDRY — covered by rows A/B (FUNC), D/E (BNDRY)
- FR-020 requires: FUNC, BNDRY — covered by rows A/B (FUNC), D/E (BNDRY)
- INTG: row F covers the external PostgreSQL dependency

> INTG coverage: 1 row (F) for the PostgreSQL database dependency.

**Design Interface Coverage Gate**:
- §4.9.9 names `_get_sync_session()` as the affected function — covered by rows B, C, D, F, G.
- `pyproject.toml` dependency declaration — covered by row E.
- All design-specified items have test coverage. PASS.

## Tasks

### Task 1: Write failing tests
**Files**: `tests/unit/test_psycopg2_dependency.py`
**Steps**:
1. Create test file with imports for `subprocess`, `importlib`, `unittest.mock`, `toml`/`tomllib`
2. Write tests matching Test Inventory:
   - Test A: Assert `import psycopg2` succeeds (no ImportError)
   - Test B: Patch `create_engine`, call `_get_sync_session()`, assert `Session` returned and `create_engine` called with sync URL
   - Test C: Patch `psycopg2` import to raise `ImportError`, assert `_get_sync_session()` propagates it
   - Test D: Set `DATABASE_URL=""`, call `_get_sync_session()`, assert no crash at creation time
   - Test E: Parse `pyproject.toml`, assert `"psycopg2-binary>=2.9"` in dev dependencies list
   - Test F: (INTG — skip in unit, mark `pytest.mark.integration`)
   - Test G: Patch `create_engine` to raise `OperationalError`, assert it propagates
3. Run: `python -m pytest tests/unit/test_psycopg2_dependency.py -v`
4. **Expected**: Test E FAILS (psycopg2-binary not yet in pyproject.toml); Test A may FAIL if not installed. Others may pass since they test existing code with mocks.

### Task 2: Implement minimal code
**Files**: `pyproject.toml`
**Steps**:
1. Add `"psycopg2-binary>=2.9",` to the `dev` list under `[project.optional-dependencies]`
2. Run: `pip install -e '.[dev]'`
3. Run: `python -m pytest tests/unit/test_psycopg2_dependency.py -v`
4. **Expected**: All tests PASS

### Task 3: Coverage Gate
1. Run: `python -m pytest tests/unit/test_psycopg2_dependency.py --cov=src/indexing/scheduler --cov-report=term-missing`
2. Check thresholds: line >= 90%, branch >= 80%. `_get_sync_session()` is 5 lines; all paths covered by tests B/C/D/G.
3. Record coverage output as evidence.

### Task 4: Refactor
1. No refactoring expected — the change is a single dependency line addition.
2. Run full test suite: `python -m pytest tests/ -v`. All tests PASS.

### Task 5: Mutation Gate
1. Run: `mutmut run --paths-to-mutate=src/indexing/scheduler.py --tests-dir=tests/unit/test_psycopg2_dependency.py`
2. Check threshold: mutation score >= 80%.
3. Note: `_get_sync_session()` has limited mutatable surface (string replace, create_engine call, Session call). Tests B/D/G should kill most mutants.
4. Record mutation output as evidence.

## Verification Checklist
- [x] All SRS acceptance criteria (from srs_trace FR-019, FR-020) traced to Interface Contract postconditions — the bugfix enables all FR-019/FR-020 ACs by making `_get_sync_session()` functional
- [x] All SRS acceptance criteria traced to Test Inventory rows — rows A, B cover the happy paths that all ACs depend on
- [x] Algorithm pseudocode covers all non-trivial methods — N/A, no algorithm (dependency fix)
- [x] Boundary table covers all algorithm parameters — N/A, no algorithm; error handling table provided
- [x] Error handling table covers all Raises entries — ImportError (row C), OperationalError (row G), empty URL (row D)
- [x] Test Inventory negative ratio >= 40% — 43% (3/7)
- [x] Visual Rendering Contract complete for ui:true features — N/A (ui:false)
- [x] Each Visual Rendering Contract element has >= 1 UI/render Test Inventory row — N/A (ui:false)
- [x] Every skipped section has explicit "N/A — [reason]"
- [x] All functions/methods named in §4.9.9 have at least one Test Inventory row — `_get_sync_session()` covered by B, C, D, F, G
