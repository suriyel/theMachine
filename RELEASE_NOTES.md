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

### Changed
- (none yet)

### Fixed
- (none yet)

---

_Format: [Keep a Changelog](https://keepachangelog.com/) — Updated after every git commit._
