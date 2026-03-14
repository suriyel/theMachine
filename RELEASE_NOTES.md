# Release Notes — code-context-retrieval

## [Unreleased]

### Added
- Initial project scaffold
- **Feature #1: Project Skeleton and CI**
  - Directory structure: src/, tests/, docs/, examples/, scripts/
  - Storage client abstractions for PostgreSQL, Redis, Qdrant, Elasticsearch
  - Health check functions for all storage services
  - FastAPI application with lifespan management
  - SQLAlchemy async session factory
  - Pydantic v2 Settings configuration with .env support
  - CI workflow with pytest and coverage reporting
  - Example: `examples/01-storage-clients.py`
- **Feature #2: Data Model and Migrations**
  - SQLAlchemy 2.0 async models: Repository, IndexJob, CodeChunk, APIKey, QueryLog
  - Alembic migration configuration with async PostgreSQL support
  - Initial migration creating all 5 tables with proper FK constraints (CASCADE delete)
  - Enum types: RepoStatus, JobStatus, TriggerType, ChunkGranularity, KeyStatus, QueryType
  - Composite primary key for CodeChunk (repo_id:file_path:symbol_hash)
  - Secure API key storage with SHA-256 hashing
  - Query correlation ID for request tracing
  - 34 model tests with 96.67% coverage
  - ST test case document with 12 test cases (all PASS)
  - Example: `examples/02-data-models.py`

### Changed
- (none yet)

### Fixed
- (none yet)

---

_Format: [Keep a Changelog](https://keepachangelog.com/) — Updated after every git commit._
