# Release Notes — code-context-retrieval

## [Unreleased]

### Added
- Initial project scaffold
- Feature #1: Project Skeleton & CI — FastAPI app factory, health endpoint (/api/v1/health), Settings config (pydantic-settings), async database engine/session factory, Alembic migration setup
- Example: 01-health-check.py
- Feature #2: Data Model & Migrations — SQLAlchemy models (Repository, IndexJob, ApiKey, ApiKeyRepoAccess, QueryLog), Alembic migration, async client wrappers (ElasticsearchClient, QdrantClientWrapper, RedisClient)
- Example: 02-data-models.py
- Feature #3: Repository Registration — RepoManager service (register, _validate_url, _derive_name), ValidationError/ConflictError exceptions, URL normalization (scheme, host, .git, trailing slash, SSH shorthand)
- Example: 03-repository-registration.py
- Feature #4: Git Clone & Update — GitCloner (clone_or_update, _clone, _update, _cleanup_partial, _run_git), CloneError exception, 300s timeout, partial file cleanup on failure
- Example: 04-git-clone-update.py

### Increment Wave 1 — Branch Selection Support (2026-03-21)
- **New**: Feature #33 — Branch Listing API (`GET /api/v1/repos/{id}/branches`)
- **Modified**: Feature #3 — Repository Registration now accepts optional `branch` parameter, stores in `indexed_branch`
- **Modified**: Feature #4 — Git Clone & Update supports `--branch` flag, `detect_default_branch()`, `list_remote_branches()`, resets to `origin/{branch}`
- **Modified**: Feature #19 — Web UI Search Page includes branch selector in registration form
- Features #3 and #4 reset to failing for re-verification

### Wave 1 Re-verification
- Feature #3: Repository Registration re-verified with branch parameter support — `register(url, branch?)` stores `indexed_branch`, IndexJob uses specified branch or "main" placeholder
- Feature #4: Git Clone & Update re-verified with branch support — `clone_or_update(branch?)` uses `--branch` for clone, `origin/{branch}` for update reset; new `detect_default_branch()` and `list_remote_branches()` methods

### Changed
- Updated alembic/env.py to import Base.metadata as target_metadata
- Updated env-guide.md with additional mutmut 3.2.0 patch documentation
- Updated alembic.ini with correct PostgreSQL credentials

### Fixed
- Added missing pydantic-settings dependency to pyproject.toml
- Fixed get_engine docstring (ArgumentError → ValueError)

---

_Format: [Keep a Changelog](https://keepachangelog.com/) — Updated after every git commit._
