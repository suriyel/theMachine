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
- **New**: Feature #36 — JavaScript: prototype-assigned function detection (`obj.x = function/arrow` → L3 chunk) + CommonJS `require()` import extraction to L1 imports list
- **New**: Feature #37 — TypeScript: `enum_declaration` → L2, `internal_module` (namespace) recursive unwrapping, `export namespace` support; decorator verification (already works natively)
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

### Feature #35: Java enum + record + static initializer
- **Modified**: Java `class_nodes` — added `enum_declaration` and `record_declaration` for L2 chunk production
- **Modified**: Java `function_nodes` — added `static_initializer` for L3 chunk production
- **Modified**: `_get_body_node` — handles `enum_body` → `enum_body_declarations` for method extraction in enums
- **Modified**: `_get_node_name` — returns `"<static>"` sentinel for `static_initializer` nodes
- Example: 08-java-enum-record-static.py

### Feature #7: Embedding Generation
- **New**: EmbeddingEncoder — DashScope text-embedding-v3 via OpenAI-compatible API (httpx), `encode_batch(texts, is_query)` with automatic batching (6/request), `encode_query(query)` with instruction prefix "Represent this code search query: "
- **New**: IndexWriter — `write_code_chunks()` (ES code_chunks + Qdrant code_embeddings), `write_doc_chunks()` (ES doc_chunks + Qdrant doc_embeddings), `write_rule_chunks()` (ES rule_chunks only, no vector), `delete_repo_index()` (all indices + collections)
- **New**: Retry logic — 3 retries with exponential backoff (1s, 2s, 4s) for ES/Qdrant write failures
- **New**: Custom exceptions — EmbeddingModelError, IndexWriteError
- **New**: Configs — EMBEDDING_MODEL, EMBEDDING_API_KEY, EMBEDDING_BASE_URL for DashScope API
- Example: 11-embedding-generation.py

### Feature #8: Keyword Retrieval (BM25)
- **New**: Retriever — `bm25_code_search(query, repo_id, languages?, top_k=200)` multi-match on content/symbol^2/signature/doc_comment, `bm25_doc_search(query, repo_id, top_k=200)` match on content, filtered by repo_id and optionally languages
- **New**: ScoredChunk — unified scored result dataclass with content_type discriminator ("code"/"doc"), code-specific fields (language, symbol, signature, doc_comment, line_start/end, parent_class), doc-specific fields (breadcrumb, heading_level)
- **New**: RetrievalError — raised when ES is unreachable (ConnectionError, TransportError, NotFoundError), caller handles degradation
- **New**: Input validation — empty/whitespace-only queries raise ValueError
- **Fixed**: Pre-existing test `test_encoder_init_missing_api_key_raises_error` made robust for mutmut environment
- Example: 12-keyword-retrieval.py

### Feature #9: Semantic Retrieval (Vector)
- **New**: Retriever.vector_code_search(query, repo_id, languages?, top_k=200) — encodes query via EmbeddingEncoder.encode_query(), searches Qdrant code_embeddings collection with cosine similarity, returns ScoredChunks with content_type="code"
- **New**: Retriever.vector_doc_search(query, repo_id, top_k=200) — same pattern for doc_embeddings collection, returns ScoredChunks with content_type="doc"
- **New**: Qdrant payload filtering — repo_id (always) + languages (optional via MatchAny)
- **New**: Error wrapping — EmbeddingModelError and Qdrant errors (UnexpectedResponse, RpcError, ConnectionError) wrapped into RetrievalError
- **New**: Degradation warning — logs warning when Qdrant is unreachable per SRS FR-007 AC-3
- Example: 13-semantic-retrieval.py

### Increment Wave 3 — Retrieval Quality Evaluation Pipeline (2026-03-21)
- **New**: Feature #40 — Evaluation Corpus Management (`EvalCorpusBuilder`, `eval/repos.json`, `eval_` index namespace)
- **New**: Feature #41 — LLM Query Generation & Relevance Annotation (`LLMAnnotator`, MiniMax2.5 API, dual annotation, Cohen's Kappa, golden dataset)
- **New**: Feature #42 — Retrieval Quality Evaluation & Reporting (`EvalRunner`, MRR@10/NDCG@10/Recall@200/Precision@3, per-language/per-stage breakdown)
- **New configs**: MINIMAX_API_KEY, MINIMAX_BASE_URL, MINIMAX_MODEL

### Feature #10: Rank Fusion (RRF)
- **New**: RankFusion — `fuse(*result_lists, top_k=50)` using Reciprocal Rank Fusion with k=60, merging N ranked lists into a single unified ranking
- **New**: RRF score formula: `score(d) = Σ 1/(k + rank_i(d))` — overlapping candidates across lists receive boosted scores
- **New**: Supports 2-way (BM25 + vector), 4-way (BM25 code/doc + vector code/doc), and 5-way (+ symbol boost) fusion via variadic parameter
- **New**: Input validation — `ValueError` for k ≤ 0
- **New**: Pure computation — no external dependencies, ~2ms for 400 candidates
- Example: 14-rank-fusion.py

### Feature #11: Neural Reranking
- **New**: Reranker — `rerank(query, candidates, top_k=6)` using bge-reranker-v2-m3 cross-encoder via sentence-transformers, scoring query-document pairs and selecting top-K results sorted by relevance
- **New**: Graceful fallback to fusion-ranked order on model load failure, inference error, or NaN scores — logs degradation warning
- **New**: Batch inference with batch_size=32 for cross-encoder efficiency
- **New**: Pure computation module — no external I/O dependencies at runtime (model loaded at init)

### Feature #12: Context Response Builder
- **New**: ResponseBuilder — `build(chunks, query, query_type, repo?, rules?)` splits reranked ScoredChunks by `content_type` into dual-list response (codeResults + docResults)
- **New**: Content truncation — content exceeding 2000 chars truncated with `...` marker and `truncated: true` flag
- **New**: Rules section — optional categorized rules (agent_rules, contribution_guide, linter_config) from repository rule chunks
- **New**: Pydantic response models — QueryResponse, CodeResult, DocResult, RulesSection
- **New**: Pure computation — stateless transformer, no external dependencies
- Example: 12-context-response-builder.py

### Feature #13: Natural Language Query Handler
- **New**: QueryHandler — `handle_nl_query(query, repo, languages?)` orchestrates 4-way async parallel retrieval (BM25 code + vector code + BM25 doc + vector doc), unified RRF fusion (top-50), neural rerank (top-6), and response building
- **New**: Query expansion — `_extract_identifiers()` extracts camelCase/PascalCase/snake_case/dot-separated identifiers from NL queries; symbol boost search fires ES term queries on `symbol.raw` with weight 0.3
- **New**: Degraded response — `degraded=True` on QueryResponse when any retrieval path fails or times out; partial results returned from successful paths
- **New**: Input validation — `ValidationError` for empty/whitespace queries and queries exceeding 500 chars
- **New**: `detect_query_type()` stub returning "nl" (Feature #14 will extend)
- **Modified**: QueryResponse model — added `degraded: bool = False` field
- Example: 13-nl-query-handler.py
- Example: 15-neural-reranking.py

### Feature #14: Symbol Query Handler
- **New**: `detect_query_type(query)` — auto-detection heuristic classifies queries as "symbol" (dots, `::`, `#`, camelCase, PascalCase, snake_case with no spaces) or "nl" (natural language)
- **New**: `handle_symbol_query(query, repo)` — ES term exact match on `symbol.raw` → fuzzy fallback (`fuzziness=AUTO`) → NL pipeline fallback; reranks results (top-6), builds response with `query_type="symbol"`
- **New**: Input validation — `ValidationError` for empty/whitespace queries and queries exceeding 200 chars
- Example: 14-symbol-query.py

### Feature #17: REST API Endpoints
- **New**: query_router — `POST /api/v1/query` with query type detection (NL/symbol), AuthMiddleware dependency, permission check, error mapping (ValidationError→400, RetrievalError→500)
- **New**: repos_router — `GET /api/v1/repos` (list), `POST /api/v1/repos` (register with URL+branch), `POST /api/v1/repos/{id}/reindex` (admin trigger), error mapping (ConflictError→409, KeyError→404)
- **New**: keys_router — `POST/GET /api/v1/keys`, `DELETE /api/v1/keys/{id}`, `POST /api/v1/keys/{id}/rotate` — admin-only API key CRUD
- **Modified**: health_router — enhanced `GET /api/v1/health` with per-service connectivity checks (ES, Qdrant, Redis, PostgreSQL), unauthenticated
- **New**: Pydantic schemas and FastAPI dependency injection (deps.py)
- Example: 17-rest-api-endpoints.py

### Feature #18: MCP Server
- **New**: `create_mcp_server(query_handler, session_factory, es_client)` factory — creates FastMCP instance with 3 tools
- **New**: `search_code_context` tool — validates query, detects query type (NL/symbol), delegates to QueryHandler, returns JSON matching REST API response format. `top_k` and `max_tokens` params reserved for future use.
- **New**: `list_repositories` tool — queries DB for all repos with optional case-insensitive fuzzy filter on name/URL
- **New**: `get_chunk` tool — retrieves full chunk content from ES by document ID (code_chunks then doc_chunks), bypasses truncation limit
- **New**: Error handling — ValueError for input validation (empty query/chunk_id), RuntimeError for retrieval/DB failures, all caught by FastMCP as MCP error responses
- Example: 18-mcp-server.py

### Feature #16: API Key Authentication
- **New**: AuthMiddleware — FastAPI dependency for X-API-Key header validation, SHA-256 hash lookup (Redis cache TTL=300s → PostgreSQL fallback), rate limiting (10 failures/IP/minute → 429 via Redis INCR/EXPIRE), role-based permissions (read: query+list_repos, admin: all), repository access control (admin bypasses, read checks ApiKeyRepoAccess), graceful Redis failure (fail-open rate limit, DB fallback for key lookup)
- **New**: APIKeyManager — create_key(name, role, repo_ids) generates secrets.token_urlsafe(32), stores SHA-256 hash, returns plaintext once; revoke_key deactivates + invalidates Redis cache; rotate_key revokes old + creates new with same name/role/repos; list_keys returns all keys
- **New**: ROLE_PERMISSIONS static map for fast permission checks without DB lookups
- Example: 16-api-key-authentication.py

### Feature #22: Manual Reindex Trigger
- **Formalized**: POST /api/v1/repos/{repo_id}/reindex endpoint (already implemented in Feature #17)
- Admin role required (403 for read-only keys), 404 for non-existent repos
- Creates IndexJob with status="pending" and returns job_id

### Feature #38: C: typedef struct + function prototypes + enum
- **New**: C `class_nodes` now includes `struct_specifier` and `enum_specifier` — typedef structs produce L2 chunks with typedef alias as symbol, enums produce L2 chunks
- **New**: C function prototype detection — `declaration` nodes with `function_declarator` (no body) produce L3 chunks
- **New**: `preproc_ifdef`/`preproc_if` recursion in `_walk_classes` and `_walk_functions` for C/C++ header guard unwrapping
- **New**: `_find_child_of_type` and `_get_typedef_name` helper functions
- Example: 21-c-typedef-prototype-enum.py

### Feature #33: Branch Listing API
- **New**: `GET /api/v1/repos/{id}/branches` endpoint — returns sorted list of remote branch names and `default_branch` for a registered+cloned repository
- **New**: `BranchListResponse` schema (branches: list[str], default_branch: str)
- **Modified**: `ROLE_PERMISSIONS` — added `list_branches` to `read` and `admin` roles
- **New**: 404 for unknown repo, 409 for uncloned repo, 500 for GitCloner failure
- Example: 20-branch-listing-api.py

### Feature #21: Scheduled Index Refresh
- **New**: `create_celery_app(broker_url, schedule_cron=None)` — Celery app factory with Beat schedule configuration, configurable cron (default: weekly Sunday 02:00 UTC), 5-field cron string parsing
- **New**: `scheduled_reindex_all` — periodic Celery task that queries active repos, skips those with in-progress jobs (pending/running IndexJob), enqueues `reindex_repo_task` for eligible repos
- **New**: `reindex_repo_task` — per-repo task with branch fallback chain (indexed_branch → default_branch → "main"), creates IndexJob, retries once after 1 hour on failure (MaxRetriesExceededError logged and skipped)
- **New**: Sync SQLAlchemy session helper for Celery worker context
- Example: 19-scheduled-index-refresh.py

### Feature #15: Repository-Scoped Query
- **Modified**: Retriever — `bm25_code_search`, `bm25_doc_search`, `vector_code_search`, `vector_doc_search` now accept `repo_id: str | None = None`; when None, searches span all indexed repositories; when specified, results restricted via ES term filter and Qdrant payload filter
- **Modified**: QueryHandler — `handle_nl_query`, `handle_symbol_query`, `_run_pipeline`, `_symbol_boost_search` accept `repo: str | None = None`; symbol query inline ES queries (term + fuzzy) conditionally include repo filter
- **Modified**: `_build_code_query`, `_build_doc_query` — omit `filter` key from ES bool clause when no filter conditions exist
- **Modified**: `_build_qdrant_filter` — returns `None` (not empty Filter) when no conditions, accepted by qdrant-client
- **New**: Non-existent repository returns empty result set (no exception) — ES/Qdrant return 0 hits gracefully
- Example: 15-repo-scoped-query.py

### Feature #38: C typedef struct + prototypes + enum
- **New**: `type_definition` containing `struct_specifier` → L2 chunk with typedef name as symbol
- **New**: `declaration` with `function_declarator` (no body) → L3 prototype chunk
- **New**: `enum_specifier` added to C `class_nodes` → L2 chunk
- **New**: `preproc_ifdef`/`preproc_if` recursion for class/function/import detection inside header guards
- Example: 21-c-typedef-prototype-enum.py

### Feature #39: C++ namespace + template unwrapping
- **New**: Recursive `namespace_definition` unwrapping in `_walk_classes`, `_walk_functions`, and `extract_file_chunk` — supports nested namespaces, C++17 `a::b::c` syntax, inline namespaces
- **New**: Single-level `template_declaration` unwrapping — template class → L2 chunk, template function → L3 chunk
- **New**: `_collect_namespace_symbols()` helper for L1 top_level_symbols extraction from namespaces
- **New**: Namespace + template combined patterns (e.g., `namespace ns { template<T> class Tmpl {} }`)
- Example: 22-cpp-namespace-template-chunking.py

### Feature #19: Web UI Search Page
- **New**: `WebRouter` class (`src/query/web_router.py`) — 4 SSR routes: search page, search results (htmx partial), repository registration, branch listing
- **New**: `CodeHighlighter` + `UCDDarkStyle` (`src/query/highlighter.py`) — Pygments syntax highlighting with UCD Developer Dark theme token colors
- **New**: Jinja2 templates (`_base.html`, `search.html`, partials) with htmx integration for partial page updates
- **New**: Static CSS (`style.css`) with full UCD color, typography, and spacing tokens as CSS custom properties
- **New**: Developer Dark theme: bg `#0d1117`, search input 44px, repo dropdown 200px, language checkboxes, result cards with syntax highlighting, empty state, header 56px
- **New**: Registration form with branch selector (fetches branches via Branch Listing API)
- Example: 24-web-ui-search.sh

### Feature #20: Language Filter
- **New**: `LanguageFilter` class (`src/query/language_filter.py`) — validates and normalizes language filter values against supported set (CON-001: java, python, typescript, javascript, c, c++)
- **New**: Integrated into both `handle_nl_query` and `handle_symbol_query` paths in QueryHandler
- **New**: Unsupported languages raise `ValidationError` → HTTP 400 with supported language list
- **New**: Case normalization (e.g., "Java" → "java"), whitespace stripping, empty/None → no filter
- Example: 23-language-filter.py

### Feature #23: Metrics Endpoint
- **New**: `metrics_registry` module (`src/query/metrics_registry.py`) — Prometheus metrics using prometheus-client==0.21.1
- **New**: Metrics: `query_latency_seconds` (histogram), `retrieval_latency_seconds` (histogram), `rerank_latency_seconds` (histogram), `query_total` (counter), `cache_hit_ratio` (gauge), `index_size_chunks` (gauge)
- **New**: `GET /metrics` endpoint — unauthenticated, Prometheus text format
- **New**: Helper functions: `record_query_latency`, `record_retrieval_latency`, `record_rerank_latency`, `set_cache_hit_ratio`, `set_index_size`
- **Fixed**: mutmut v3 stats collection — conftest sets MUTANT_UNDER_TEST env var and skips Jinja2 template tests in mutants/ directory
- Example: 23-metrics-endpoint.py

### Feature #24: Query Logging
- **New**: `QueryLogger` class (`src/query/query_logger.py`) — structured JSON logging to stdout via Python `logging` module
- **New**: Fields: query, query_type, api_key_id, result_count, retrieval_ms, rerank_ms, total_ms, timestamp (ISO 8601 UTC)
- **New**: Non-fatal — all logging wrapped in try/except, I/O failures never block query responses
- Example: 24-query-logging.py

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
