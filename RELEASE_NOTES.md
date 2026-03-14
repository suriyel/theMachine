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
- **Feature #3: Repository Registration (FR-001)**
  - RepoManager service with register, get, get_by_url, list_all, delete operations
  - Git URL validation via GitHub API (validate_git_url function)
  - FastAPI endpoints: POST /api/v1/repos, GET /api/v1/repos
- **Feature #4: Git Clone or Update (FR-002)**
  - GitCloner class for cloning/updating Git repositories
  - Retry logic with exponential backoff (3 retries, 1s→2s→4s)
  - Handle auth failures immediately without retry
  - Workspace directory management
  - Custom exceptions: GitCloneError, GitCloneFailedError, GitFetchError
  - 15 unit tests + 2 integration tests (95% coverage)
  - ST test case document with 4 test cases (all PASS)
  - Example: `examples/04-git-clone-update.py`
  - skip_validation query parameter to bypass GitHub API validation
  - Duplicate URL detection (409 Conflict)
  - 16 tests (8 unit, 8 integration) - all passing
  - ST test case document with 4 test cases (all PASS)
  - Example: `examples/03-repository-registration.py`
- **Feature #5: Content Extraction (FR-003)**
  - ContentExtractor class for extracting indexable content
  - Identifies README, CHANGELOG, documentation, and source files
  - Supports 6 languages: Java, Python, TypeScript, JavaScript, C, C++
  - Handles edge cases: empty files, large files (>10MB), binary files
  - RawContent dataclass and ContentType enum
  - 19 unit tests (95.49% coverage)
  - ST test case document with 3 test cases (all PASS)
  - Example: `examples/05-content-extraction.py`

### Changed
- (none yet)

### Fixed
- (none yet)

---

_Format: [Keep a Changelog](https://keepachangelog.com/) — Updated after every git commit._
