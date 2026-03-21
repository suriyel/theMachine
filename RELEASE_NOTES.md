# Release Notes — code-context-retrieval

## [Unreleased]

### Added
- Initial project scaffold
- Feature #1: Project Skeleton & CI — FastAPI app factory, health endpoint (/api/v1/health), Settings config (pydantic-settings), async database engine/session factory, Alembic migration setup
- Example: 01-health-check.py
- Feature #2: Data Model & Migrations — SQLAlchemy models (Repository, IndexJob, ApiKey, ApiKeyRepoAccess, QueryLog), Alembic migration, async client wrappers (ElasticsearchClient, QdrantClientWrapper, RedisClient)
- Example: 02-data-models.py

### Changed
- Updated alembic/env.py to import Base.metadata as target_metadata
- Updated env-guide.md with additional mutmut 3.2.0 patch documentation

### Fixed
- Added missing pydantic-settings dependency to pyproject.toml
- Fixed get_engine docstring (ArgumentError → ValueError)

---

_Format: [Keep a Changelog](https://keepachangelog.com/) — Updated after every git commit._
