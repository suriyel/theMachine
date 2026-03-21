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

### Feature #5: Content Extraction
- **New**: ContentExtractor — walks cloned repo, classifies files into 4 types (code/doc/example/rule) by extension and path patterns
- **New**: ContentType enum (CODE, DOC, EXAMPLE, RULE, UNKNOWN), ExtractedFile dataclass
- **New**: Binary detection (null byte in first 8KB), oversized file skip (>1MB), hidden dir pruning (.git)
- **New**: Graceful skip for encoding errors and permission issues with logged warnings
- Example: 05-content-extraction.py

### Feature #6: Code Chunking
- **New**: Chunker — tree-sitter AST parsing for 6 languages (Python, Java, JS, TS, C, C++), producing L1 (file), L2 (class), L3 (function) chunks with symbol, signature, doc_comment extraction
- **New**: CodeChunk, LanguageNodeMap dataclasses; EXT_TO_LANGUAGE and LANGUAGE_NODE_MAPS constants
- **New**: 500-line function splitting with 50-line overlap windows
- **New**: DocChunker — markdown heading-based splitting (H2/H3), breadcrumb construction, code block extraction, paragraph fallback, H4 optional split, token-limit enforcement
- **New**: DocChunk, CodeBlock dataclasses; Section namedtuple
- **New**: RuleExtractor — rule_type detection (agent_rules, contribution_guide, editor_config, linter_config), CLAUDE.md/CONTRIBUTING.md/.cursor/rules pattern matching
- **New**: RuleChunk dataclass
- **New**: Lazy parser initialization (one per language, reused across files)
- **New**: Arrow function detection for JavaScript/TypeScript (lexical_declaration/export_statement)
- Example: 06-code-chunking.py

### Increment Wave 2 — AST Parsing Accuracy Enhancement (2026-03-21)
- **Modified**: FR-004 — expanded EARS and 12 new acceptance criteria covering decorator/namespace/template/enum/prototype/require/typedef patterns
- **New**: Feature #34 — Python: `decorated_definition` unwrapping (@property, @dataclass, @app.route, @staticmethod, @classmethod)
- **New**: Feature #35 — Java: `enum_declaration`, `record_declaration`, `static_initializer` support
- **New**: Feature #36 — JavaScript: prototype-assigned function detection + `require()` import extraction
- **New**: Feature #37 — TypeScript: `enum_declaration`, `namespace`/`module` unwrapping, decorator unwrapping
- **New**: Feature #38 — C: `typedef struct` → L2, function prototype declarations → L3, `enum_specifier` → L2
- **New**: Feature #39 — C++: `namespace_definition` recursive unwrapping, `template_declaration` single-level unwrapping
- **Design updated**: AST node mapping table expanded, wrapper unwrapping rules table added, chunking flowchart updated

### Feature #34: Python decorated_definition Unwrapping
- **New**: `_find_decorated_inner()` helper — finds inner class/function node inside `decorated_definition` wrapper
- **Modified**: `_walk_classes` — unwraps `decorated_definition` to produce L2 class chunks with decorator text preserved
- **Modified**: `_walk_functions` — unwraps `decorated_definition` to produce L3 function chunks with decorator text preserved
- **Modified**: `extract_file_chunk` — unwraps `decorated_definition` to include decorated symbols in `top_level_symbols`
- **Fixed**: Proxy env vars (`ALL_PROXY`, `HTTP_PROXY`, etc.) cleared in test conftest to fix Qdrant/httpx client test failures
- Example: 07-decorated-definition-chunking.py

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
