# Implementation Plan: Feature #2 — Data Model and Migrations

**Feature ID**: 2
**Feature Title**: Data Model and Migrations
**Date**: 2026-03-14
**Milestone**: M1: Foundation
**Priority**: High

---

## 1. Overview

Implement SQLAlchemy ORM models for the core data entities and configure Alembic for database migrations. This feature establishes the persistence layer that all subsequent features depend on.

**Design Reference**: Section 5 (Data Model) from `docs/plans/2026-03-14-code-context-retrieval-design.md`

---

## 2. Scope

### In Scope
- SQLAlchemy 2.0 async models for: Repository, IndexJob, CodeChunk, APIKey, QueryLog
- Alembic migration configuration and initial migration
- Model unit tests with in-memory SQLite for isolation
- Integration tests with real PostgreSQL

### Out of Scope
- API endpoints (Feature #3+)
- Business logic (RepoManager, etc.)
- Vector/Qdrant integration (Feature #4+)

---

## 3. Implementation Tasks

### Task 1: Create Model Base and Mixins

**File**: `src/shared/models/base.py`

Create shared model infrastructure:
- `Base` class (declarative base for SQLAlchemy)
- Timestamp mixin (`created_at`, `updated_at`)
- UUID primary key mixin

```python
# Design-aligned schema:
# - All tables use UUID primary keys
# - All tables have created_at timestamp
# - Use async SQLAlchemy 2.0 style
```

### Task 2: Implement Repository Model

**File**: `src/shared/models/repository.py`

Per design Section 5 ER diagram:
- `id`: UUID PK
- `url`: String, unique, nullable=False (Git URL)
- `name`: String, nullable=False (display name)
- `languages`: JSON/Array (target languages)
- `status`: Enum (registered|indexing|indexed|error)
- `created_at`: Timestamp
- `last_indexed_at`: Timestamp, nullable

**Relationships**: One-to-many to IndexJob, One-to-many to CodeChunk

### Task 3: Implement IndexJob Model

**File**: `src/shared/models/index_job.py`

Per design Section 5 ER diagram:
- `id`: UUID PK
- `repo_id`: UUID FK → Repository
- `status`: Enum (queued|running|completed|failed)
- `trigger_type`: Enum (scheduled|manual)
- `started_at`: Timestamp, nullable
- `completed_at`: Timestamp, nullable
- `error_message`: Text, nullable
- `chunk_count`: Integer, default 0

**Relationships**: Many-to-one to Repository

### Task 4: Implement CodeChunk Model

**File**: `src/shared/models/code_chunk.py`

Per design Section 5 ER diagram:
- `id`: String PK (composite: `repo_id:file_path:symbol_hash`)
- `repo_id`: UUID FK → Repository
- `file_path`: String
- `language`: String
- `granularity`: Enum (file|class|function|symbol)
- `symbol_name`: String, nullable
- `content`: Text
- `start_line`: Integer
- `end_line`: Integer
- `indexed_at`: Timestamp

**Relationships**: Many-to-one to Repository

### Task 5: Implement APIKey Model

**File**: `src/shared/models/api_key.py`

Per design Section 5 ER diagram:
- `id`: UUID PK
- `key_hash`: String (SHA-256 hash)
- `name`: String (key description)
- `status`: Enum (active|revoked)
- `created_at`: Timestamp
- `revoked_at`: Timestamp, nullable

**Relationships**: One-to-many to QueryLog

### Task 6: Implement QueryLog Model

**File**: `src/shared/models/query_log.py`

Per design Section 5 ER diagram:
- `id`: UUID PK
- `api_key_id`: UUID FK → APIKey
- `query_text`: Text
- `query_type`: Enum (natural_language|symbol)
- `repo_filter`: String, nullable
- `language_filter`: String, nullable
- `result_count`: Integer
- `latency_ms`: Float
- `created_at`: Timestamp
- `correlation_id`: UUID

**Relationships**: Many-to-one to APIKey

### Task 7: Create Model Package

**File**: `src/shared/models/__init__.py`

Export all models for easy importing.

### Task 8: Configure Alembic

**Files**:
- `alembic.ini` (config file)
- `alembic/env.py` (async migration environment)
- `alembic/versions/001_initial.py` (initial migration)

Configure Alembic for async SQLAlchemy with asyncpg driver.

### Task 9: Update Database Session Module

**File**: `src/shared/db/session.py` (already exists, may need updates)

Ensure session factory supports model imports and migrations.

---

## 4. Test Plan

### Unit Tests (SQLite in-memory)

| Test | Description |
|------|-------------|
| `test_repository_create` | Create Repository with url, name, languages |
| `test_repository_unique_url` | Duplicate URL raises integrity error |
| `test_index_job_create` | Create IndexJob with UUID, QUEUED status |
| `test_index_job_repo_relationship` | Job references Repository correctly |
| `test_code_chunk_create` | Create CodeChunk with composite ID |
| `test_api_key_create` | Create APIKey with key_hash, status active |
| `test_api_key_revoked` | Revoke APIKey, check revoked_at |
| `test_query_log_create` | Create QueryLog with correlation_id |
| `test_query_log_api_key_relationship` | Log references APIKey correctly |

### Integration Tests (PostgreSQL)

| Test | Description |
|------|-------------|
| `test_alembic_upgrade` | `alembic upgrade head` creates all tables |
| `test_alembic_downgrade` | `alembic downgrade base` drops all tables |

---

## 5. Verification Steps Alignment

| Verification Step | Test Coverage |
|-------------------|---------------|
| Given a new database, when running alembic upgrade head, then all tables are created | `test_alembic_upgrade` |
| Given Repository model, when creating record with url, name, languages, then persisted | `test_repository_create` |
| Given IndexJob model, when creating job with status QUEUED, then persisted with UUID | `test_index_job_create` |
| Given CodeChunk model, when creating chunk, then persisted | `test_code_chunk_create` |
| Given APIKey model, when creating key, then persisted with status active | `test_api_key_create` |
| Given QueryLog model, when creating log entry, then persisted with correlation_id | `test_query_log_create` |

---

## 6. File Structure

```
src/shared/
├── models/
│   ├── __init__.py
│   ├── base.py
│   ├── repository.py
│   ├── index_job.py
│   ├── code_chunk.py
│   ├── api_key.py
│   └── query_log.py
├── db/
│   └── session.py (existing, may update)
alembic/
├── env.py
├── versions/
│   └── 001_initial.py
alembic.ini
tests/
├── test_models.py (unit tests)
└── test_migrations.py (integration tests)
```

---

## 7. Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| sqlalchemy[asyncio] | ^2.0.36 | Async ORM |
| asyncpg | ^0.30.0 | PostgreSQL async driver |
| alembic | ^1.14.0 | Database migrations |
| pytest | ^8.3.0 | Testing |
| pytest-asyncio | ^0.24.0 | Async test support |

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Alembic async configuration complexity | Use established patterns from SQLAlchemy 2.0 docs |
| Composite primary key for CodeChunk | Use String PK with application-generated ID |

---

## 9. Estimated Scope

- **Files to create**: ~10
- **Files to modify**: ~2
- **Test cases**: ~12
- **LOC estimate**: ~500
