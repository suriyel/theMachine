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
- **Feature #5: Content Extraction (FR-003)**
  - ContentExtractor class for extracting indexable content
  - Identify README, CHANGELOG, documentation, and source files
  - Support 6 languages: Java, Python, TypeScript, JavaScript, C, C++
  - Handle edge cases: empty files, large files (>10MB), binary files
  - Skip hidden directories and common build artifacts
  - RawContent dataclass and ContentType enum
  - 19 unit tests covering all verification steps
  - ST test case document with 3 test cases (all PASS)
  - Example: `examples/05-content-extraction.py`
- **Feature #6: Code Chunking with tree-sitter (FR-004)**
  - CodeChunker class for multi-granularity code chunking
  - Support 6 languages: Java, Python, TypeScript, JavaScript, C, C++
  - Extract file-level, class-level, function-level chunks
  - Support interface and type symbols for TypeScript
  - Fallback to file-level chunking for unsupported languages
  - ChunkType enum and CodeChunk dataclass
  - 19 unit tests (91.34% overall coverage)
  - ST test case document with 4 test cases (all PASS)
  - Example: `examples/06-code-chunking.py`
- **Feature #7: Embedding Generation and Index Writing (FR-004/FR-009)**
  - EmbeddingEncoder class using bge-code-v1 model (1024 dimensions)
  - IndexWriter class for Elasticsearch and Qdrant
  - Batch embedding generation with lazy model loading
  - Query encoding with semantic search prefix
  - Delete-by-repo for re-indexing support
  - 12 unit tests (92% coverage)
  - ST test case document with 4 test cases (all PASS)
  - Example: `examples/07-embedding-generation.py`
- **Feature #8: Keyword Retrieval (FR-008)**
  - KeywordRetriever class for BM25-based keyword search
  - Uses Elasticsearch multi_match query for lexical search
  - Supports repo_filter and language_filter parameters
  - Candidate dataclass for result representation
  - 12 unit tests (91.27% overall coverage)
  - ST test case document with 4 test cases (all PASS)
  - Example: `examples/08-keyword-retrieval.py`
  - Bug fix: Added missing language field to CodeChunker
- **Feature #9: Semantic Retrieval (FR-009)**
  - SemanticRetriever class for vector-based similarity search
  - Uses Qdrant for semantic vector storage and retrieval
  - Configurable similarity threshold (default 0.6)
  - Supports repo_filter and language_filter parameters
  - 13 unit tests (100% coverage)
  - ST test case document with 4 test cases (2 PASS, 2 PENDING - require indexed data)
  - Example: `examples/09-semantic-retrieval.py`
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
