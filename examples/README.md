# code-context-retrieval — Examples

Runnable examples demonstrating completed features. Each example corresponds to a feature in `feature-list.json`.

## Index

| # | Feature | File | How to run |
|---|---------|------|------------|
| 01 | Project Skeleton and CI | [01-storage-clients.py](01-storage-clients.py) | `python examples/01-storage-clients.py` |
| 02 | Data Model and Migrations | [02-data-models.py](02-data-models.py) | `python examples/02-data-models.py` |
| 03 | Repository Registration (FR-001) | [03-repository-registration.py](03-repository-registration.py) | `python examples/03-repository-registration.py` |
| 05 | Content Extraction (FR-003) | [05-content-extraction.py](05-content-extraction.py) | `python examples/05-content-extraction.py` |
| 06 | Code Chunking (FR-004) | [06-code-chunking.py](06-code-chunking.py) | `python examples/06-code-chunking.py` |
| 07 | Embedding Generation (FR-004/009) | [07-embedding-generation.py](07-embedding-generation.py) | `python examples/07-embedding-generation.py` |
| 08 | Keyword Retrieval (FR-008) | [08-keyword-retrieval.py](08-keyword-retrieval.py) | `python examples/08-keyword-retrieval.py` |
| 09 | Semantic Retrieval (FR-009) | [09-semantic-retrieval.py](09-semantic-retrieval.py) | `python examples/09-semantic-retrieval.py` |
| 10 | Rank Fusion (FR-010) | [10-rank-fusion.py](10-rank-fusion.py) | `python examples/10-rank-fusion.py` |
| 11 | Neural Reranking (FR-011) | [11-neural-reranking.py](11-neural-reranking.py) | `python examples/11-neural-reranking.py` |
| 12 | Context Response Builder (FR-012) | [12-context-response-builder.py](12-context-response-builder.py) | `python examples/12-context-response-builder.py` |
| 13 | Query Handler - Natural Language (FR-005) | [13-query-handler-nl.py](13-query-handler-nl.py) | `python examples/13-query-handler-nl.py` |
| 14 | Query Handler - Symbol Query (FR-006) | [14-query-handler-symbol.py](14-query-handler-symbol.py) | `python examples/14-query-handler-symbol.py` |
| 15 | Query Handler - Repository Scoped (FR-007) | [15-query-handler-repo-scoped.py](15-query-handler-repo-scoped.py) | `python examples/15-query-handler-repo-scoped.py` |
| 16 | API Key Authentication (FR-018) | [16-api-key-authentication.py](16-api-key-authentication.py) | `python examples/16-api-key-authentication.py` |
| 17 | REST API Endpoints | [17-rest-api-endpoints.py](17-rest-api-endpoints.py) | `python examples/17-rest-api-endpoints.py` |
| 18 | MCP Server (FR-013) | [18-mcp-server.py](18-mcp-server.py) | `python -m src.query.mcp` |
| 19 | Web UI Search Page (FR-014) | [19-web-ui-search-page.py](19-web-ui-search-page.py) | `python examples/19-web-ui-search-page.py` |
| 20 | Language Filter (FR-015) | [20-language-filter.py](20-language-filter.py) | `python examples/20-language-filter.py` |
| 27 | NFR-002: Query Throughput | [27-query-throughput.py](27-query-throughput.py) | `python examples/27-query-throughput.py --validate-sustained 1200` |
| 28 | NFR-003: Repository Capacity | [28-nfr03-repository-capacity.py](28-nfr03-repository-capacity.py) | `python examples/28-nfr03-repository-capacity.py` |

## Prerequisites

Before running examples, ensure:

1. **Environment activated**: `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Unix)
2. **.env configured**: Set required environment variables (DATABASE_URL, REDIS_URL, QDRANT_URL, ELASTICSEARCH_URL)
3. **Dependencies installed**: `pip install -e .`

## Feature 01: Storage Clients

Demonstrates health check functions for all storage services:
- PostgreSQL connection and version check
- Redis PING/PONG latency test
- Qdrant health check
- Elasticsearch cluster health

## Feature 02: Data Model and Migrations

Demonstrates SQLAlchemy async model usage:
- Repository: Create and query Git repository metadata
- IndexJob: Track indexing job status
- CodeChunk: Store code segments with composite IDs
- APIKey: Secure API key storage with SHA-256 hashing
- QueryLog: Query execution logging with correlation IDs
- ORM relationships: Repository → IndexJob, Repository → CodeChunk

## Feature 05: Content Extraction (FR-003)

Demonstrates the ContentExtractor for extracting indexable content:
- Identify README, CHANGELOG, and documentation files
- Extract source code files by language (.java, .py, .ts, .js, .c, .cpp)
- Filter by target languages
- Handle edge cases: empty files, large files, binary files

## Feature 06: Code Chunking (FR-004)

Demonstrates the CodeChunker for segmenting source code:
- Multi-granularity chunking: file, class, function levels
- Support for 6 languages: Java, Python, TypeScript, JavaScript, C, C++
- Interface and type symbol extraction for TypeScript
- Fallback to file-level chunking for unsupported languages

## Feature 07: Embedding Generation (FR-004/009)

Demonstrates embedding generation and index writing:
- Generate embeddings using bge-code-v1 model (1024 dimensions)
- Encode queries with semantic search prefix
- Write chunks and vectors to Elasticsearch and Qdrant
- Delete old chunks before re-indexing

## Feature 08: Keyword Retrieval (FR-008)

Demonstrates BM25-based keyword search:
- Basic keyword search across code chunks
- Repo filter to scope results to a specific repository
- Language filter to scope results to a specific programming language
- Combined filters for precise retrieval
- Returns ranked results with BM25 scores

## Feature 09: Semantic Retrieval (FR-009)

Demonstrates vector-based semantic search:
- Basic semantic search using Qdrant vector similarity
- Configurable similarity threshold (default 0.6)
- Repo filter to scope results to a specific repository
- Language filter to scope results to a specific programming language
- Combined filters for precise retrieval
- Returns ranked results with similarity scores

## Feature 10: Rank Fusion (FR-010)

Demonstrates Reciprocal Rank Fusion (RRF) for merging search results:
- Merge keyword and semantic retrieval results
- RRF algorithm with configurable k parameter (default 60)
- Duplicate deduplication by chunk_id
- Handles edge cases: empty lists, partial empty
- Preserves original Candidate metadata

## Feature 11: Neural Reranking (FR-011)

Demonstrates cross-encoder neural reranking:
- Reorder fused candidates using bge-reranker-v2-m3 cross-encoder
- Score query-document pairs for relevance
- Handles edge cases: empty list, single item (pass-through)
- GPU acceleration when available (CUDA)
- Updates candidate scores with neural relevance scores

## Feature 12: Context Response Builder (FR-012)

Demonstrates building API response from ranked candidates:
- Transform Candidate objects to ContextResult format
- Limit results to top-k (default 3)
- Sort by score descending with stability for equal scores
- Handle edge cases: empty list, fewer than top_k candidates
- Map all required fields: repository, file_path, symbol, score, content

## Feature 13: Query Handler - Natural Language (FR-005)

Demonstrates the QueryHandler orchestration:
- Accept natural language queries and initiate retrieval pipeline
- Validate non-empty input (empty/whitespace rejection)
- Execute keyword and semantic retrieval in parallel
- Apply rank fusion to merge results
- Apply neural reranking for candidates >= 2
- Build final response with top-k results and timing
- Support repo and language filters

## Feature 14: Query Handler - Symbol Query (FR-006)

Demonstrates symbol query handling:
- Accept code symbol identifiers as queries (e.g., org.springframework.web.client.RestTemplate)
- Validate non-whitespace input
- Execute retrieval pipeline for symbol lookups
- Support dot-notation for fully qualified names

## Feature 15: Query Handler - Repository Scoped (FR-007)

Demonstrates repository-scoped query filtering:
- Accept queries with target repository filter
- Restrict retrieval to specified repository only
- Handle non-existent repository gracefully (returns empty, no error)
- Support combined repo + language filters

## Feature 16: API Key Authentication (FR-018)

Demonstrates API key authentication:
- Hash API keys using SHA-256
- Verify keys against database with ACTIVE status
- Return 401 for missing/invalid/revoked keys
- Integration with FastAPI via AuthMiddleware

## Feature 17: REST API Endpoints

Demonstrates the REST API endpoints:
- POST /api/v1/query - Submit query via JSON body
- GET /api/v1/query - Submit query via query parameters
- GET /api/v1/health - Health check (no auth required)
- GET /api/v1/metrics - Prometheus metrics (no auth required)
- Error handling: 401 for auth failures, 422 for validation errors

## Feature 18: MCP Server (FR-013)

Demonstrates the MCP Server:
- Exposes search_code_context tool via MCP protocol
- Supports stdio transport for local AI agent integration
- Supports HTTP SSE transport for remote AI agent integration
- Tool parameters: query (required), api_key (required), repo (optional), language (optional)
- Error handling: missing params, invalid auth, empty query

## Feature 19: Web UI Search Page (FR-014)

Demonstrates the Web UI search interface:
- Interactive search page with syntax-highlighted results
- Language filter chips (All, Java, Python, TypeScript, JavaScript, C, C++)
- Developer Dark theme with Prism.js syntax highlighting
- HTMX for seamless page updates

## Feature 20: Language Filter (FR-015)

Demonstrates the LanguageFilter class:
- Validate language filters (case-insensitive)
- Support 6 languages: Java, Python, TypeScript, JavaScript, C, C++
- Return normalized lowercase language or raise ValueError for unsupported
- Filter Candidate objects by programming language

## Feature 27: NFR-002 Query Throughput

Demonstrates the throughput test runner for NFR-002:
- Validate sustained throughput threshold (>= 1000 QPS)
- Validate burst throughput threshold (>= 2000 QPS)
- Run full locust load tests (requires services running)
- Quick validation mode for CI/CD pipelines

Quick validation examples:
```bash
python examples/27-query-throughput.py --validate-sustained 1200  # PASS
python examples/27-query-throughput.py --validate-burst 2500     # PASS
```

## Feature 28: NFR-003 Repository Capacity

Demonstrates the capacity test runner for NFR-003:
- Validate repository count range (100-1000)
- Validate latency threshold (P95 <= 1000ms, NFR-001 bound)
- Progressive scale points: [100, 250, 500, 750, 1000]
- Run full capacity tests (requires services running with indexed data)
- Quick validation mode for CI/CD pipelines

Quick validation examples:
```bash
python examples/28-nfr03-repository-capacity.py  # Validate thresholds
python scripts/run_capacity_test.py --validate --repos 500 --latency 800   # PASS
python scripts/run_capacity_test.py --validate --repos 1000 --latency 950  # PASS
```

---

_Add a new row to the table above each time you create an example for a completed feature._
