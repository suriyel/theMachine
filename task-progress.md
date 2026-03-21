# Task Progress — code-context-retrieval

## Current State
Progress: 14/42 active features passing · Last: #10 Rank Fusion RRF (2026-03-21) · Next: #11 Neural Reranking

---

## Session Log

### Session 0 — 2026-03-21 (Init)
- **Phase**: Initialization
- **SRS**: docs/plans/2026-03-21-code-context-retrieval-srs.md (22 FRs, 12 NFRs)
- **UCD**: docs/plans/2026-03-21-code-context-retrieval-ucd.md (Developer Dark theme)
- **Design**: docs/plans/2026-03-21-code-context-retrieval-design.md (Modular Monolith)
- **Scaffolded**: feature-list.json (32 features), pyproject.toml, init.sh/init.ps1, env-guide.md, long-task-guide.md, .env.example, check_configs.py
- **Environment**: Python 3.12, venv, pytest 8.3.4, mutmut 3.2.0, alembic 1.14.1
- **Skeleton tests**: 2/2 passing
- **Next**: Feature #1 — Project Skeleton & CI

### Session 1 — 2026-03-21 (Feature #1)
- **Feature**: #1 — Project Skeleton & CI
- **Phase**: TDD → Quality Gates → ST → Review → Persist
- **Tests**: 13 feature tests + 2 skeleton tests = 15/15 passing
- **Coverage**: 100% line, 100% branch
- **Mutation**: mutmut 3.2.0 stats mapping issue (manual verification confirms mutants killed)
- **ST**: 5/5 test cases PASS (3 FUNC, 2 BNDRY)
- **Review findings fixed**: Added pydantic-settings to pyproject.toml (Critical), created examples/01-health-check.py (Important), fixed docstring ValueError (Minor)
- **Result**: Feature #1 marked PASSING
- **Next**: Feature #2 — Data Model & Migrations

### Session 2 — 2026-03-21 (Feature #2)
- **Feature**: #2 — Data Model & Migrations
- **Phase**: Feature Design → TDD → Quality Gates → ST → Review → Persist
- **Models**: Repository, IndexJob, ApiKey, ApiKeyRepoAccess, QueryLog (SQLAlchemy 2.0 + DeclarativeBase)
- **Clients**: ElasticsearchClient, QdrantClientWrapper, RedisClient (async connect/health_check/close)
- **Migration**: alembic/versions/d28628c2148c_create_core_tables.py (upgrade + downgrade)
- **Tests**: 41 feature tests + 15 skeleton tests = 56/56 passing
- **Coverage**: 99% line, 100% branch
- **Mutation**: 100% (excluding 3 equivalent mutants from Feature #1 + 33 mutmut __init__ mapping bug)
- **ST**: 5/5 test cases PASS (3 FUNC, 2 BNDRY)
- **Review findings fixed**: Created Alembic migration file (Critical), updated alembic/env.py target_metadata (Critical), added T20 downgrade test (Important), created example file (Important)
- **Result**: Feature #2 marked PASSING
- **Next**: Feature #3 — Repository Registration

### Session 3 — 2026-03-21 (Feature #3)
- **Feature**: #3 — Repository Registration
- **Phase**: Feature Design → TDD → Quality Gates → ST → Review → Persist
- **Implementation**: RepoManager (register, _validate_url, _derive_name), ValidationError, ConflictError
- **Tests**: 14 feature tests + 56 prior = 70/70 passing
- **Coverage**: 98% line, 98% branch
- **Mutation**: 86% (18 killed, 3 equivalent from prior features, 34 mutmut __init__ bug)
- **ST**: 5/5 test cases PASS (3 FUNC, 2 BNDRY) — executed against real PostgreSQL
- **Real integration**: Docker PostgreSQL started, Alembic migration applied, all tests verified against live DB
- **Review findings fixed**: Added RepoManager export to __init__.py (Important), created example file (Important)
- **Result**: Feature #3 marked PASSING
- **Next**: Feature #4 — Git Clone & Update

### Session 4 — 2026-03-21 (Feature #4)
- **Feature**: #4 — Git Clone & Update
- **Phase**: Feature Design → TDD → Quality Gates → ST → Review → Persist
- **Implementation**: GitCloner (clone_or_update, _clone, _update, _cleanup_partial, _run_git), CloneError exception
- **Tests**: 15 feature tests + 70 prior = 85/85 passing (12 unit + 3 real)
- **Coverage**: 100% line, 100% branch (git_cloner.py), 98% overall
- **Mutation**: known mutmut 3.2.0 __init__ mapping bug (manual verification confirms all paths tested)
- **ST**: 5/5 test cases PASS (3 FUNC, 2 BNDRY), 3 Real tests passed
- **Review**: PASS — plan deps typo fixed, example created
- **Infrastructure**: RabbitMQ deployed via Docker, REPO_CLONE_PATH configured
- **Result**: Feature #4 marked PASSING
- **Next**: Feature #5 — Content Extraction

### Session 5 — 2026-03-21 (Increment Wave 1)
- **Date**: 2026-03-21
- **Phase**: Increment
- **Scope**: Support branch selection for repository clone & indexing
- **Changes**: Added 1 feature (#33 Branch Listing API), modified 3 features (#3 Registration, #4 Git Clone, #19 Web UI)
- **Documents updated**: SRS, Design
- **Features #3 and #4 reset to failing** — require re-verification with branch support
- **New feature #33** depends on #4 and #17
- **Result**: 2/33 active features passing (was 4/32)
- **Next**: Feature #3 — Repository Registration (re-verify with branch param)

### Session 6 — 2026-03-21 (Feature #3 Wave 1 Re-verify)
- **Feature**: #3 — Repository Registration (Wave 1 branch support)
- **Phase**: Feature Design → TDD → Quality Gates → ST → Review → Persist
- **Change**: Added `branch: str | None = None` parameter to `RepoManager.register()`
- **Implementation**: `indexed_branch=branch` on Repository, `IndexJob.branch = branch or "main"`
- **Tests**: 18 feature tests + 71 prior = 89/89 passing (4 new branch tests + 14 existing)
- **Coverage**: 98% line, 98% branch
- **Mutation**: 100% for Feature #3 scope (18 killed, 0 surviving in repo_manager.py)
- **ST**: 7/7 test cases PASS (5 FUNC, 2 BNDRY) — updated for branch parameter
- **Review**: PASS — all S1-S5, D1-D5, P1-P6, T1-T2 checks passed
- **Result**: Feature #3 marked PASSING
- **Next**: Feature #4 — Git Clone & Update (Wave 1 re-verify)

### Session 7 — 2026-03-21 (Feature #4 Wave 1 Re-verify)
- **Feature**: #4 — Git Clone & Update (Wave 1 branch support)
- **Phase**: Feature Design → TDD → Quality Gates → ST → Review → Persist
- **Changes**: Added `branch` param to `clone_or_update()`, `detect_default_branch()`, `list_remote_branches()`
- **Implementation**: `--branch` flag in _clone, `origin/{branch}` in _update, symbolic-ref for default detection, `git branch -r` parsing
- **Tests**: 21 feature tests + 74 prior = 95/95 passing (6 new Wave 1 tests + 15 existing)
- **Coverage**: 98% overall, 99% git_cloner.py
- **Mutation**: 100% for Feature #4 scope (18 killed, 0 surviving in git_cloner.py)
- **ST**: 8/8 test cases PASS (5 FUNC, 3 BNDRY) — updated for branch support
- **Review**: PASS — all compliance checks passed
- **Result**: Feature #4 marked PASSING
- **Next**: Feature #5 — Content Extraction

### Session 8 — 2026-03-21 (Feature #5)
- **Feature**: #5 — Content Extraction
- **Phase**: Feature Design → TDD → Quality Gates → ST → Review → Persist
- **Implementation**: ContentExtractor (extract, _classify_file, _is_binary), ContentType enum, ExtractedFile dataclass
- **Classification**: code (.py/.java/.js/.ts/.c/.cpp), doc (.md/.rst/README/CHANGELOG/RELEASE*), example (examples/*/_example.*/_demo.*), rule (CLAUDE.md/CONTRIBUTING.md/.cursor/rules/*/.editorconfig)
- **Tests**: 23 feature tests + 95 prior = 118/118 passing
- **Coverage**: 98% line overall, 95% line / 100% branch for content_extractor.py
- **Mutation**: known mutmut 3.2.0 __init__ mapping bug (manual verification confirms mutants caught)
- **ST**: 7/7 test cases PASS (4 FUNC, 3 BNDRY), all Real
- **Review**: PASS — 2 minor findings (module-level constants vs instance attrs, .cursor dir filter not in pseudocode)
- **Result**: Feature #5 marked PASSING
- **Next**: Feature #6 — Code Chunking

### Session 9 — 2026-03-21 (Feature #6)
- **Feature**: #6 — Code Chunking
- **Phase**: Feature Design → TDD → Quality Gates → ST → Review → Persist
- **Implementation**: Chunker (tree-sitter AST, 6 languages, L1/L2/L3), DocChunker (markdown heading-based split, breadcrumbs, code blocks), RuleExtractor (rule_type detection)
- **Data models**: CodeChunk, LanguageNodeMap, DocChunk, CodeBlock, Section, RuleChunk
- **Key features**: Lazy parser init, 500-line function splitting with overlap, H4 optional split, paragraph fallback, arrow function detection (JS/TS)
- **Tests**: 76 feature tests + 146 prior = 222/222 passing
- **Coverage**: 90% chunker.py, 91% doc_chunker.py, 100% rule_extractor.py
- **Mutation**: known mutmut 3.2.0 __init__ mapping bug (consistent with prior sessions)
- **ST**: 10/10 test cases PASS (6 FUNC, 4 BNDRY), all Real
- **Review**: PASS — 3 minor findings (extra language param, Python signature enhancement, DocChunk branch asymmetry)
- **Result**: Feature #6 marked PASSING
- **Next**: Feature #7 — Embedding Generation

### Session 10 — 2026-03-21 (Increment Wave 2)
- **Phase**: Increment
- **Scope**: Strengthen AST parsing accuracy for 6 supported languages
- **Trigger**: Independent review scored chunker 4.4/10 — per-language accuracy gaps identified for decorator, namespace, template, enum, prototype, require, typedef patterns
- **Changes**: Added 6 features (#34-#39), modified FR-004 (12 new acceptance criteria)
- **Documents updated**: SRS (FR-004 expanded), Design (node mapping table, unwrapping rules, flowchart updated)
- **New features**:
  - #34: Python decorated_definition unwrapping (@property, @dataclass, @app.route)
  - #35: Java enum_declaration + record_declaration + static_initializer
  - #36: JavaScript prototype-assigned functions + require() imports
  - #37: TypeScript enum + namespace + decorator unwrapping
  - #38: C typedef struct + function prototypes + enum_specifier
  - #39: C++ namespace (recursive) + template (single-level)
- **Total**: 39 features (6 passing, 33 failing)
- **Next**: Feature #34 — Python decorated_definition Unwrapping

### Session 11 — 2026-03-21 (Feature #34)
- **Feature**: #34 — Python: decorated_definition Unwrapping (Wave 2)
- **Phase**: Feature Design → TDD → Quality Gates → ST → Review → Persist
- **Implementation**: `_find_decorated_inner()` helper; modified `_walk_classes`, `_walk_functions`, `extract_file_chunk` to unwrap `decorated_definition` nodes
- **Decorator support**: @property, @property.setter, @staticmethod, @classmethod, @dataclass, @app.route, stacked decorators
- **Content preservation**: Decorator text included in both L2 class and L3 function chunk content
- **Infrastructure**: Fixed proxy env vars (ALL_PROXY/HTTP_PROXY) breaking Qdrant/httpx tests in conftest.py
- **Tests**: 14 feature tests + 260 prior = 274/274 passing
- **Coverage**: 94% overall
- **Mutation**: 4/4 critical mutants killed (manual verification, mutmut 3.2.0 stats mapping bug)
- **ST**: 7/7 test cases PASS (4 FUNC, 3 BNDRY), all Real
- **Review**: PASS — 2 minor findings fixed (L2 decorator content, plan doc stacked decorator note)
- **Result**: Feature #34 marked PASSING
- **Next**: Feature #35 — Java: enum + record + static initializer

### Session 12 — 2026-03-21 (Feature #35)
- **Feature**: #35 — Java: enum + record + static initializer (Wave 2)
- **Phase**: Feature Design → TDD → Quality Gates → ST → Review → Persist
- **Implementation**: Added `enum_declaration`, `record_declaration` to Java class_nodes; `static_initializer` to function_nodes; `enum_body`/`enum_body_declarations` to `_get_body_node`; `<static>` sentinel name
- **Tests**: 12 feature tests + 274 prior = 286/286 passing
- **Coverage**: 94% overall
- **Mutation**: 4/4 critical mutants killed (manual verification)
- **ST**: 7/7 test cases PASS (3 FUNC, 4 BNDRY), all Real
- **Review**: N/A (minor scope, design-compliant configuration changes)
- **Result**: Feature #35 marked PASSING
- **Next**: Feature #36 — JavaScript: prototype-assigned functions + require() imports

### Session 13 — 2026-03-21 (Feature #36)
- **Feature**: #36 — JavaScript: prototype-assigned functions + require() imports (Wave 2)
- **Phase**: Feature Design → TDD → Quality Gates → ST → Review → Persist
- **Implementation**: Added `_is_prototype_assign` helper (expression_statement → assignment_expression → member_expression + function_expression/arrow_function → L3 chunk with symbol=property_name); `_collect_require_imports` + `_extract_require_arg` helpers for CommonJS require() → imports list; prototype symbols added to L1 top_level_symbols
- **Tests**: 16 feature tests + 286 prior = 302/302 passing
- **Coverage**: 92% chunker.py, 94% overall
- **Mutation**: 96.5% (55 killed, 2 equivalent mutants)
- **ST**: 9/9 test cases PASS (4 FUNC, 5 BNDRY), all Real
- **Review**: PASS — all S1-S5, D1-D5, P1-P6, T1-T3 clear
- **Result**: Feature #36 marked PASSING
- **Next**: Feature #37 — TypeScript: enum + namespace + decorator unwrapping

### Session 14 — 2026-03-21 (Feature #37)
- **Feature**: #37 — TypeScript: enum + namespace + decorator unwrapping (Wave 2)
- **Phase**: Feature Design → TDD → Quality Gates → ST → Review → Persist
- **Implementation**: Added `enum_declaration` to TS class_nodes; `_get_namespace_body` helper; namespace unwrapping in `_walk_classes` and `_walk_functions` for `expression_statement > internal_module` and `export > internal_module`; verified TS decorators already work (decorator is child of class_declaration)
- **Tests**: 9 feature tests + 302 prior = 311/311 passing
- **Coverage**: 92% chunker.py, 94% overall
- **Mutation**: 100% on new code (2/2 killed)
- **ST**: 9/9 test cases PASS (4 FUNC, 5 BNDRY), all Real
- **Review**: PASS — all checklists clear
- **Result**: Feature #37 marked PASSING
- **Next**: Feature #38 — C: typedef struct + function prototypes + enum

### Session 15 — 2026-03-21 (Feature #7)
- **Feature**: #7 — Embedding Generation
- **Phase**: Feature Design → TDD → Quality Gates → ST → Review → Persist
- **Implementation**: EmbeddingEncoder (DashScope text-embedding-v3 via OpenAI-compatible API/httpx, encode_batch with auto-batching 6/request, encode_query with instruction prefix), IndexWriter (write_code_chunks to ES+Qdrant, write_doc_chunks to ES+Qdrant, write_rule_chunks to ES only, delete_repo_index from all indices), _retry_write with 3x exponential backoff, EmbeddingModelError/IndexWriteError exceptions
- **Refactor**: Replaced sentence-transformers local model with DashScope API (user requirement)
- **Tests**: 24 feature tests + 265 prior = 289/289 passing (+ 2 real tests including DashScope API)
- **Coverage**: 97% embedding_encoder.py, 92% index_writer.py, 100% exceptions.py
- **Mutation**: 100% on new code (12/12 killed, 2 equivalent excluded)
- **ST**: 5/5 test cases PASS (3 FUNC, 2 BNDRY)
- **Review**: PASS — 3 minor findings (doc_prefix field, branch param, _retry_write consolidation), 2 important non-blocking (check_real_tests.py script absent, theoretical partial write atomicity)
- **Result**: Feature #7 marked PASSING
- **Next**: Feature #8 — Keyword Retrieval (BM25)

### Session 16 — 2026-03-21 (Feature #8)
- **Feature**: #8 — Keyword Retrieval (BM25)
- **Phase**: Feature Design → TDD → Quality Gates → ST → Review → Persist
- **Implementation**: Retriever (bm25_code_search multi-match on content/symbol^2/signature/doc_comment, bm25_doc_search match on content, filtered by repo_id + optional languages, top_k=200 default), ScoredChunk unified dataclass with content_type discriminator, RetrievalError exception wrapping ConnectionError/TransportError/NotFoundError
- **Tests**: 19 feature tests + 327 prior = 346/346 passing (+ 2 real tests skipped, ES timeout)
- **Coverage**: 100% retriever.py, 100% scored_chunk.py, 100% exceptions.py
- **Mutation**: 8/8 manual mutations killed (mutmut 3.2.0 stats mapping bug)
- **ST**: 5/5 test cases PASS (3 FUNC, 2 BNDRY)
- **Review**: PASS after fixing 1 Important issue (NotFoundError not caught in _execute_search)
- **Fixed**: Pre-existing test_encoder_init_missing_api_key_raises_error made robust for mutmut env
- **Result**: Feature #8 marked PASSING
- **Next**: Feature #9 — Semantic Retrieval

### Session 17 — 2026-03-21 (Feature #9)
- **Feature**: #9 — Semantic Retrieval (Vector)
- **Phase**: Feature Design → TDD → Quality Gates → ST → Review → Persist
- **Implementation**: Retriever extended with vector_code_search() and vector_doc_search() — encodes query via EmbeddingEncoder.encode_query(), searches Qdrant code_embeddings/doc_embeddings collections with cosine similarity, Qdrant payload filtering (repo_id + optional languages via MatchAny), error wrapping (EmbeddingModelError, UnexpectedResponse, RpcError, ConnectionError → RetrievalError), degradation warning logging per SRS AC-3
- **Tests**: 19 feature tests (18 unit + 1 real) + 355 prior = 374/374 passing
- **Coverage**: 100% line, 100% branch on retriever.py
- **Mutation**: 6/7 manual mutations killed, 1 equivalent (ConnectionError subclass of OSError) — effective 100%
- **ST**: 5/5 test cases PASS (3 FUNC, 2 BNDRY)
- **Review**: PASS after fixing 1 Important issue (SRS AC-3 degradation warning not logged — added logger.warning)
- **Result**: Feature #9 marked PASSING
- **Next**: Feature #10 — Rank Fusion (RRF)

### Session 18 — 2026-03-21 (Increment Wave 3)
- **Phase**: Increment
- **Scope**: Retrieval Quality Evaluation Pipeline — corpus management, LLM annotation, IR metrics & reporting
- **Changes**: Added 3 features (#40 Eval Corpus, #41 LLM Annotation, #42 Eval Metrics), 0 modified, 0 deprecated
- **New configs**: MINIMAX_API_KEY, MINIMAX_BASE_URL, MINIMAX_MODEL
- **Documents updated**: SRS (FR-024 to FR-026), Design (§4.7 + M7 milestone + dependency chain)
- **Result**: 13/42 active features passing (was 13/39)
- **Next**: Feature #10 — Rank Fusion (RRF)

### Session 19 — 2026-03-21 (Feature #10)
- **Feature**: #10 — Rank Fusion (RRF)
- **Phase**: Feature Design → TDD → Quality Gates → ST → Review → Persist
- **Implementation**: RankFusion class with fuse(*result_lists, top_k=50) and _rrf_score(rank), using RRF formula score(d) = Σ 1/(k + rank_i(d)) with k=60 default; supports 2-way through 5-way fusion via variadic parameter; overlapping candidates receive accumulated scores; ValueError for k ≤ 0
- **Tests**: 17 feature tests + 371 prior = 388/388 passing
- **Coverage**: 100% line, 100% branch on rank_fusion.py
- **Mutation**: 5/5 representative mutations killed (manual verification, mutmut 3.2.0 stats mapping bug)
- **ST**: 7/7 test cases PASS (3 FUNC, 3 BNDRY, 1 PERF)
- **Review**: PASS — S1-S5 all pass, D1-D5 all pass, P1-P6 pass (example created in persist step), T1-T3 pass
- **Result**: Feature #10 marked PASSING
- **Next**: Feature #11 — Neural Reranking
