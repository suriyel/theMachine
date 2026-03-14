# Code Context Retrieval System — Design Document

**Date**: 2026-03-14
**Status**: Approved
**SRS Reference**: docs/plans/2026-03-14-code-context-retrieval-srs.md
**UCD Reference**: docs/plans/2026-03-14-code-context-retrieval-ucd.md
**Template**: docs/templates/design-template.md

## 1. Design Drivers

- **NFR thresholds**: P95 ≤ 1000ms, ≥ 1000 QPS sustained / ≥ 2000 QPS peak, 99.9% uptime, single-node failure tolerance with zero query failures, linear horizontal scaling (±20%)
- **Constraints**: 6 target languages (Java, Python, TypeScript, JavaScript, C, C++), MCP protocol compliance, offline indexing / online query isolation (CON-003), any Git URL as data source
- **Interface requirements**: MCP over stdio/HTTP (AI agents), HTTPS REST + HTML/JS (developers), Git HTTPS/SSH (repositories), HTTP/local embedding model inference
- **User-confirmed tech selections**: tree-sitter (parsing), Qdrant (vector store), Elasticsearch (keyword index), bge-code (embeddings), bge-reranker (reranking)
- **UCD style**: Developer Dark theme, 7 components + 2 pages, JetBrains Mono code font, Lucide Icons

## 2. Approach Selection

**Selected**: Approach B — Python Microservices (Indexing Service + Query Service)

**Justification**:
1. Fully satisfies CON-003 (offline/online isolation) with two independent services
2. Query Service is stateless → supports multi-replica deployment for NFR-006/007
3. Pure Python stack provides native support for bge-code/bge-reranker/tree-sitter without cross-language overhead
4. Moderate operational complexity (2 services) vs. Go+Python dual-stack alternative
5. Perfect alignment with user-confirmed technology selections

**Alternatives considered**:
- **Approach A (Python Monolith)**: Disqualified — violates CON-003, cannot meet NFR-002/006/007
- **Approach C (Go Query + Python Indexing)**: Viable but dual-language stack increases maintenance cost; Go's advantage (goroutine concurrency) unnecessary at 1000 QPS target

## 3. Architecture

### 3.1 Architecture Overview

The system consists of two independent Python services sharing a storage layer:

- **Indexing Service** — Offline batch processing service. Clones repositories, parses code (tree-sitter), generates embeddings (bge-code), writes to search indices (Qdrant + Elasticsearch). Scheduled via Celery + Redis.
- **Query Service** — Online stateless service. Accepts queries (MCP + REST), performs keyword retrieval (ES) + semantic retrieval (Qdrant) in parallel, fuses results, applies neural reranking (bge-reranker), returns top-3 results. Web UI integrated via Jinja2 SSR + HTMX.
- **Storage Layer** — Qdrant (vectors) + Elasticsearch (keywords) + PostgreSQL (metadata: repos, jobs, API keys) + Redis (Celery broker + query cache).

### 3.2 Logical View

```mermaid
graph TB
    subgraph Presentation["Presentation Layer"]
        MCP["MCP Server<br/>(stdio/HTTP)"]
        REST["REST API<br/>(FastAPI)"]
        WEB["Web UI<br/>(Jinja2 + HTMX)"]
    end

    subgraph QueryBiz["Query Business Layer"]
        QH["Query Handler"]
        KR["Keyword Retriever"]
        SR["Semantic Retriever"]
        RF["Rank Fusion"]
        RR["Neural Reranker"]
        AUTH["Auth Middleware"]
    end

    subgraph IndexBiz["Indexing Business Layer"]
        RM["Repo Manager"]
        CC["Code Chunker<br/>(tree-sitter)"]
        EG["Embedding Generator<br/>(bge-code)"]
        SCHED["Scheduler<br/>(Celery Beat)"]
        WORKER["Index Worker<br/>(Celery)"]
    end

    subgraph Storage["Storage Layer"]
        PG[(PostgreSQL<br/>Metadata)]
        QD[(Qdrant<br/>Vectors)]
        ES[(Elasticsearch<br/>Keywords)]
        RD[(Redis<br/>Broker + Cache)]
    end

    MCP --> AUTH
    REST --> AUTH
    WEB --> AUTH
    AUTH --> QH
    QH --> KR
    QH --> SR
    KR --> RF
    SR --> RF
    RF --> RR

    KR --> ES
    SR --> QD
    AUTH --> PG

    SCHED --> WORKER
    WORKER --> RM
    RM --> CC
    CC --> EG
    EG --> QD
    EG --> ES
    RM --> PG
    WORKER --> RD
```

### 3.3 Component Diagram

```mermaid
graph LR
    Agent["AI Agent<br/>(Claude Code)"] -->|MCP stdio/HTTP| QS["Query Service<br/>:8000"]
    Browser["Developer<br/>Browser"] -->|HTTPS| QS
    Admin["Platform<br/>Engineer"] -->|REST API| QS
    Admin -->|REST API| IS["Indexing Service<br/>:8001"]

    QS -->|HTTP 9200| ES["Elasticsearch<br/>Cluster"]
    QS -->|gRPC 6334| QD["Qdrant<br/>Cluster"]
    QS -->|TCP 5432| PG["PostgreSQL"]
    QS -->|TCP 6379| RD["Redis"]

    IS -->|TCP 6379| RD
    IS -->|Git HTTPS/SSH| GIT["Git Repos"]
    IS -->|HTTP 9200| ES
    IS -->|gRPC 6334| QD
    IS -->|TCP 5432| PG
    IS -->|HTTP/local| EMB["Embedding<br/>Model<br/>(bge-code)"]
```

### 3.4 Tech Stack Decisions

| Decision | Choice | Rationale (SRS Trace) |
|----------|--------|----------------------|
| Language | Python 3.11+ | bge-code/bge-reranker/tree-sitter native support; unified stack |
| Web Framework | FastAPI | Async support, auto OpenAPI docs, high-performance ASGI |
| ASGI Server | Uvicorn + Gunicorn (multi-worker) | Multi-process bypasses GIL → NFR-001/002 |
| Task Queue | Celery + Redis | Mature distributed task scheduling, Beat for cron → FR-016 |
| Vector Store | Qdrant | User-confirmed; high-performance vector search → FR-009, NFR-001 |
| Keyword Index | Elasticsearch 8.x | User-confirmed; BM25 keyword retrieval → FR-008 |
| Code Parser | tree-sitter | User-confirmed; multi-language AST parsing → FR-004, CON-001 |
| Embedding Model | BAAI/bge-code-v1 | User-confirmed; code semantic embedding → FR-009 |
| Reranker | BAAI/bge-reranker-v2-m3 | User-confirmed; cross-encoder reranking → FR-011 |
| Metadata DB | PostgreSQL 16 | Relational storage for repos/jobs/API keys |
| Cache | Redis 7 | Celery broker + query result cache → NFR-001 |
| MCP SDK | mcp (Python SDK) | Official MCP protocol implementation → CON-002, IFR-001 |
| Web UI | Jinja2 + HTMX + Prism.js | Lightweight SSR, no SPA build; Prism.js syntax highlighting → FR-014 |

**NFR Satisfaction Strategy:**

| NFR | Strategy |
|-----|----------|
| NFR-001 (P95 ≤ 1000ms) | Redis query cache + Qdrant/ES parallel retrieval + bge-reranker GPU inference |
| NFR-002 (≥ 1000 QPS) | Gunicorn multi-worker (4-8 workers/node) × N query nodes + load balancer |
| NFR-005 (99.9%) | Query Service stateless multi-replica + Qdrant/ES/PG cluster mode |
| NFR-006 (linear scaling) | Stateless Query Service: add node = add throughput; Qdrant/ES sharded horizontal scaling |
| NFR-007 (zero failure) | Multi-replica + health checks + load balancer auto-removes failed nodes |

## 4. Key Feature Designs

### 4.1 Feature Group: Repository Management (FR-001, FR-002, FR-003, FR-004)

#### 4.1.1 Overview
Repository registration, clone/update, content extraction, and multi-granularity code chunking. Forms the core indexing pipeline.

#### 4.1.2 Class Diagram

```mermaid
classDiagram
    class RepoManager {
        -db: AsyncSession
        +register(url: str, languages: list[str]): Repository
        +get(repo_id: UUID): Repository
        +list_all(): list[Repository]
        +delete(repo_id: UUID): void
    }

    class GitCloner {
        -workspace_dir: Path
        +clone_or_update(repo: Repository): Path
        -_full_clone(url: str, dest: Path): void
        -_fetch_updates(dest: Path): void
    }

    class ContentExtractor {
        -supported_extensions: dict[str, str]
        +extract(repo_path: Path, languages: list[str]): list[RawContent]
        -_classify_file(path: Path): ContentType
    }

    class CodeChunker {
        -parsers: dict[str, TreeSitterParser]
        +chunk(content: RawContent): list[CodeChunk]
        -_parse_ast(source: str, lang: str): Tree
        -_extract_symbols(tree: Tree): list[Symbol]
        -_fallback_file_chunk(content: RawContent): CodeChunk
    }

    class TreeSitterParser {
        -language: Language
        +parse(source: bytes): Tree
        +query(pattern: str): list[Node]
    }

    class IndexWriter {
        -qdrant: QdrantClient
        -es: AsyncElasticsearch
        +write_chunks(chunks: list[CodeChunk], embeddings: list[Vector]): void
        +delete_by_repo(repo_id: UUID): void
    }

    RepoManager --> GitCloner : delegates clone
    ContentExtractor --> CodeChunker : feeds content
    CodeChunker --> TreeSitterParser : uses
    CodeChunker ..> IndexWriter : chunks flow to
```

#### 4.1.3 Sequence Diagram — Indexing Pipeline

```mermaid
sequenceDiagram
    participant Sched as Scheduler/Admin
    participant Worker as Celery Worker
    participant RM as RepoManager
    participant GC as GitCloner
    participant CE as ContentExtractor
    participant CC as CodeChunker
    participant EG as EmbeddingGenerator
    participant IW as IndexWriter
    participant PG as PostgreSQL

    Sched->>Worker: enqueue index_job(repo_id)
    Worker->>RM: get(repo_id)
    RM->>PG: SELECT repository
    PG-->>RM: Repository
    RM-->>Worker: Repository

    Worker->>GC: clone_or_update(repo)
    alt First clone
        GC->>GC: _full_clone()
    else Existing
        GC->>GC: _fetch_updates()
    end
    GC-->>Worker: repo_path

    alt Clone failed
        Worker->>PG: UPDATE job SET status='failed'
        Worker-->>Sched: job failed
    end

    Worker->>CE: extract(repo_path, languages)
    CE-->>Worker: list[RawContent]

    alt No indexable content
        Worker->>PG: UPDATE job SET status='completed', chunks=0
        Worker-->>Sched: completed (zero chunks)
    end

    Worker->>CC: chunk(content) for each
    CC-->>Worker: list[CodeChunk]

    Worker->>EG: encode(chunks)
    EG-->>Worker: list[Vector]

    Worker->>IW: write_chunks(chunks, embeddings)
    Worker->>PG: UPDATE job SET status='completed'
    Worker-->>Sched: completed
```

#### 4.1.4 Design Notes
- **tree-sitter parsers**: Load one Language object per target language (6 total), select parser by file extension
- **Unsupported language fallback**: Index entire file as single file-level text chunk without symbol extraction (FR-004 AC2)
- **Incremental update**: clone_or_update uses `git fetch` + `git diff` to identify changed files, reprocess only changed chunks (delete old + write new)
- **Embedding batching**: EmbeddingGenerator uses batch_size=64 for bulk inference, reducing GPU/CPU call overhead

### 4.2 Feature Group: Query Pipeline (FR-005–FR-012)

#### 4.2.1 Overview
Query intake → keyword retrieval + semantic retrieval (parallel) → rank fusion → neural reranking → top-3 response. The core online path.

#### 4.2.2 Class Diagram

```mermaid
classDiagram
    class QueryHandler {
        -keyword_retriever: KeywordRetriever
        -semantic_retriever: SemanticRetriever
        -rank_fusion: RankFusion
        -reranker: NeuralReranker
        -cache: RedisCache
        +handle(query: QueryRequest): QueryResponse
    }

    class QueryRequest {
        +text: str
        +query_type: QueryType
        +repo_filter: str | None
        +language_filter: str | None
        +top_k: int = 3
    }

    class QueryType {
        <<enumeration>>
        NATURAL_LANGUAGE
        SYMBOL
    }

    class KeywordRetriever {
        -es: AsyncElasticsearch
        -index_name: str
        +retrieve(query: str, filters: dict): list[Candidate]
    }

    class SemanticRetriever {
        -qdrant: QdrantAsyncClient
        -encoder: EmbeddingEncoder
        -threshold: float
        +retrieve(query: str, filters: dict): list[Candidate]
    }

    class RankFusion {
        -k: int = 60
        +fuse(keyword_results: list[Candidate], semantic_results: list[Candidate]): list[Candidate]
    }

    class NeuralReranker {
        -model: CrossEncoder
        +rerank(query: str, candidates: list[Candidate]): list[Candidate]
    }

    class Candidate {
        +chunk_id: str
        +repo_name: str
        +file_path: str
        +symbol: str | None
        +content: str
        +score: float
    }

    class QueryResponse {
        +results: list[ContextResult]
        +query_time_ms: float
    }

    QueryHandler --> KeywordRetriever
    QueryHandler --> SemanticRetriever
    QueryHandler --> RankFusion
    QueryHandler --> NeuralReranker
    QueryHandler ..> QueryRequest : receives
    QueryHandler ..> QueryResponse : returns
    KeywordRetriever ..> Candidate : produces
    SemanticRetriever ..> Candidate : produces
    RankFusion ..> Candidate : merges
    NeuralReranker ..> Candidate : reorders
```

#### 4.2.3 Sequence Diagram — Query Flow

```mermaid
sequenceDiagram
    participant Client as Client (Agent/Browser)
    participant Auth as AuthMiddleware
    participant QH as QueryHandler
    participant Cache as Redis Cache
    participant KR as KeywordRetriever
    participant SR as SemanticRetriever
    participant ES as Elasticsearch
    participant QD as Qdrant
    participant RF as RankFusion
    participant RR as NeuralReranker

    Client->>Auth: query request + API key
    alt Invalid/missing key
        Auth-->>Client: 401 Unauthorized
    end
    Auth->>QH: validated QueryRequest

    QH->>Cache: get(cache_key)
    alt Cache hit
        Cache-->>QH: cached QueryResponse
        QH-->>Client: QueryResponse
    end

    par Parallel retrieval
        QH->>KR: retrieve(query, filters)
        KR->>ES: BM25 search
        ES-->>KR: keyword candidates
        KR-->>QH: list[Candidate]
    and
        QH->>SR: retrieve(query, filters)
        SR->>QD: vector search (threshold >= 0.6)
        QD-->>SR: semantic candidates
        SR-->>QH: list[Candidate]
    end

    QH->>RF: fuse(keyword_candidates, semantic_candidates)
    RF-->>QH: merged list[Candidate]

    alt < 2 candidates
        QH-->>Client: QueryResponse (as-is)
    end

    QH->>RR: rerank(query, candidates)
    RR-->>QH: reranked list[Candidate]

    QH->>QH: build top-3 response
    QH->>Cache: set(cache_key, response, ttl=300)
    QH-->>Client: QueryResponse
```

#### 4.2.4 Design Notes
- **Parallel retrieval**: KeywordRetriever and SemanticRetriever execute concurrently via `asyncio.gather()`, not sequentially
- **Rank Fusion**: Reciprocal Rank Fusion (RRF) with k=60, no score calibration needed
- **Semantic threshold**: SemanticRetriever accepts `threshold` parameter (default 0.6); candidates below threshold are discarded
- **Cache strategy**: cache_key = hash(query_text + repo_filter + language_filter), TTL=300s; index update invalidates caches for affected repo
- **Rerank degradation**: Skip reranking model when < 2 candidates, return as-is

### 4.3 Feature Group: Query Interfaces (FR-013, FR-014, FR-015, FR-018)

#### 4.3.1 Overview
MCP protocol service, Web UI, language filtering, API key authentication. The system's external access layer.

#### 4.3.2 Class Diagram

```mermaid
classDiagram
    class MCPServer {
        -query_handler: QueryHandler
        -tool_name: str = "search_code_context"
        +handle_tool_call(request: MCPToolCall): MCPToolResult
        -_parse_params(params: dict): QueryRequest
    }

    class WebRouter {
        -query_handler: QueryHandler
        -templates: Jinja2Templates
        +search_page(request: Request): HTMLResponse
        +search_api(query: SearchForm): JSONResponse
    }

    class APIRouter {
        -query_handler: QueryHandler
        +query(request: QueryRequest): QueryResponse
    }

    class AuthMiddleware {
        -db: AsyncSession
        +verify_api_key(key: str): APIKeyRecord
        +require_auth(request: Request): Request
    }

    class LanguageFilter {
        -supported: set[str]
        +validate(language: str): str
        +apply(candidates: list[Candidate], language: str): list[Candidate]
    }

    MCPServer --> QueryHandler : delegates
    WebRouter --> QueryHandler : delegates
    APIRouter --> QueryHandler : delegates
    WebRouter --> AuthMiddleware : uses
    APIRouter --> AuthMiddleware : uses
    MCPServer --> AuthMiddleware : uses
    QueryHandler --> LanguageFilter : uses
```

#### 4.3.3 Sequence Diagram — MCP Tool Call

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant MCP as MCPServer
    participant Auth as AuthMiddleware
    participant QH as QueryHandler

    Agent->>MCP: tool_call("search_code_context", params)
    MCP->>MCP: _parse_params(params)

    alt Missing required params
        MCP-->>Agent: MCP error (invalid_params)
    end

    MCP->>Auth: verify_api_key(params.api_key)
    alt Invalid key
        MCP-->>Agent: MCP error (unauthorized)
    end

    MCP->>QH: handle(QueryRequest)
    QH-->>MCP: QueryResponse
    MCP-->>Agent: MCP tool_result(results)
```

#### 4.3.4 Design Notes
- **MCP implementation**: Uses `mcp` Python SDK, exposes single tool `search_code_context` with params: query (required), repo (optional), language (optional), api_key (required)
- **MCP transport**: Supports stdio (local agent) and HTTP SSE (remote agent)
- **Web UI**: Jinja2 templates + HTMX for search interaction, Prism.js syntax highlighting; UCD Developer Dark theme via CSS custom properties
- **Language filter**: LanguageFilter.validate() checks against CON-001's 6 languages; unsupported → 422 with supported language list
- **Authentication**: AuthMiddleware looks up API key hash in PostgreSQL, verifies key status (active/revoked)

### 4.4 Feature Group: Scheduling & Operations (FR-016, FR-017)

#### 4.4.1 Overview
Scheduled index refresh and manual reindex triggering.

#### 4.4.2 Class Diagram

```mermaid
classDiagram
    class IndexScheduler {
        -celery_app: Celery
        -repo_manager: RepoManager
        +schedule_all(): void
        +trigger_manual(repo_id: UUID): IndexJob
        +get_job_status(job_id: UUID): JobStatus
    }

    class IndexJob {
        +id: UUID
        +repo_id: UUID
        +status: JobStatus
        +started_at: datetime | None
        +completed_at: datetime | None
        +error_message: str | None
        +chunk_count: int
    }

    class JobStatus {
        <<enumeration>>
        QUEUED
        RUNNING
        COMPLETED
        FAILED
    }

    IndexScheduler --> IndexJob : creates/manages
    IndexJob --> JobStatus : has
```

#### 4.4.3 Flow Diagram — Schedule & Manual Reindex

```mermaid
flowchart TD
    S1([Celery Beat: Weekly Tick]) --> A[Load all registered repos]
    A --> B{For each repo}
    B --> C{Active job exists?}
    C -- YES --> D[Skip repo, log warning]
    C -- NO --> E[Enqueue index_job]
    D --> B
    E --> B
    B -- Done --> F([End: All jobs queued])

    S2([Admin: Manual Reindex]) --> G{Active job for repo?}
    G -- YES --> H([Reject: 409 Conflict])
    G -- NO --> I[Enqueue index_job]
    I --> J([Return: job_id + QUEUED])
```

#### 4.4.4 Design Notes
- **Celery Beat**: Default weekly schedule (crontab), configurable via environment variable to daily or custom
- **Job deduplication**: Only one active job (QUEUED or RUNNING) per repo at a time, prevents duplicate indexing
- **Partial failure**: schedule_all() enqueues each repo independently; single repo failure doesn't affect others; failed repos trigger alert notification (log + extensible webhook)

### 4.5 Feature Group: Embedding & Reranking Models

#### 4.5.1 Overview
bge-code embedding encoding and bge-reranker neural reranking. Core model inference components.

#### 4.5.2 Class Diagram

```mermaid
classDiagram
    class EmbeddingEncoder {
        -model: SentenceTransformer
        -model_name: str = "BAAI/bge-code-v1"
        -batch_size: int = 64
        -dimension: int
        +encode(texts: list[str]): list[Vector]
        +encode_query(query: str): Vector
    }

    class NeuralReranker {
        -model: CrossEncoder
        -model_name: str = "BAAI/bge-reranker-v2-m3"
        -max_length: int = 512
        +rerank(query: str, candidates: list[Candidate]): list[Candidate]
    }

    class Vector {
        +values: list[float]
        +dimension: int
    }

    EmbeddingEncoder ..> Vector : produces
    NeuralReranker ..> Candidate : reorders
```

#### 4.5.3 Design Notes
- **EmbeddingEncoder**: Uses `encode()` for batch chunk encoding during indexing; `encode_query()` for single query encoding with query prefix
- **Model loading**: Models loaded once at service startup, not per-request
- **GPU inference**: Prefers GPU (`device="cuda"`) when available; degrades to CPU otherwise
- **Reranker truncation**: Inputs exceeding max_length=512 tokens are truncated to prevent OOM

## 5. Data Model

```mermaid
erDiagram
    REPOSITORY ||--o{ INDEX_JOB : "has jobs"
    REPOSITORY ||--o{ CODE_CHUNK : "contains chunks"
    API_KEY ||--o{ QUERY_LOG : "generates"

    REPOSITORY {
        uuid id PK
        string url "Git URL (unique)"
        string name "Display name"
        string[] languages "Target languages"
        string status "registered|indexing|indexed|error"
        timestamp created_at
        timestamp last_indexed_at
    }

    INDEX_JOB {
        uuid id PK
        uuid repo_id FK
        string status "queued|running|completed|failed"
        string trigger_type "scheduled|manual"
        timestamp started_at
        timestamp completed_at
        string error_message "nullable"
        int chunk_count
    }

    CODE_CHUNK {
        string id PK "repo_id:file_path:symbol_hash"
        uuid repo_id FK
        string file_path
        string language
        string granularity "file|class|function|symbol"
        string symbol_name "nullable"
        text content
        int start_line
        int end_line
        timestamp indexed_at
    }

    API_KEY {
        uuid id PK
        string key_hash "SHA-256 hash"
        string name "Key description"
        string status "active|revoked"
        timestamp created_at
        timestamp revoked_at "nullable"
    }

    QUERY_LOG {
        uuid id PK
        uuid api_key_id FK
        string query_text
        string query_type "natural_language|symbol"
        string repo_filter "nullable"
        string language_filter "nullable"
        int result_count
        float latency_ms
        timestamp created_at
        string correlation_id
    }
```

**Storage Distribution:**

| Data | Store | Rationale |
|------|-------|-----------|
| Repository, IndexJob, APIKey, QueryLog | PostgreSQL | Relational metadata, ACID transactions |
| CodeChunk content + metadata | Elasticsearch | BM25 full-text retrieval (FR-008) |
| CodeChunk embeddings | Qdrant | Vector similarity retrieval (FR-009) |
| Cross-store linking | Same `chunk_id` in ES and Qdrant | Enables fusion across retrieval methods |

## 6. API / Interface Design

### REST API (Query Service :8000)

| Method | Path | FR Trace | Auth | Description |
|--------|------|----------|------|-------------|
| POST | `/api/v1/query` | FR-005/006/007/012 | API Key | Submit query, return Top-3 results |
| GET | `/api/v1/query` | FR-005/012 | API Key | GET-style query (query params) |
| POST | `/api/v1/repos` | FR-001 | API Key (Admin) | Register repository |
| GET | `/api/v1/repos` | FR-001 | API Key | List registered repositories |
| POST | `/api/v1/repos/{id}/reindex` | FR-017 | API Key (Admin) | Trigger manual reindex |
| GET | `/api/v1/repos/{id}/jobs` | FR-016/017 | API Key (Admin) | View indexing job status |
| GET | `/api/v1/health` | NFR-005 | None | Health check |
| GET | `/api/v1/metrics` | NFR-008 | None | Prometheus metrics endpoint |

### Query Request/Response Contract

```
POST /api/v1/query
Headers: X-API-Key: <key>
Body: {
  "query": "how to use WebClient timeout",
  "query_type": "natural_language",  // or "symbol"
  "repo": "spring-framework",       // optional
  "language": "Java",               // optional
  "top_k": 3                        // optional, default 3
}

Response 200: {
  "results": [
    {
      "repository": "spring-framework",
      "file_path": "web/src/main/java/WebClient.java",
      "symbol": "WebClient.builder()",
      "score": 0.92,
      "content": "public static WebClient.Builder builder() { ... }"
    }
  ],
  "query_time_ms": 142.5
}
```

### MCP Interface (IFR-001)

| Tool Name | Parameters | Returns |
|-----------|-----------|---------|
| `search_code_context` | query (required), repo (optional), language (optional), api_key (required) | `{ results: [...], query_time_ms: float }` |

Transport: stdio (local) or HTTP SSE (remote)

## 7. UI/UX Approach

**Strategy**: Jinja2 SSR + HTMX + CSS Variables (UCD tokens)

| UCD Component | Implementation | Library |
|---------------|---------------|---------|
| Search Input | `<input>` + HTMX `hx-post` | HTMX |
| Language Filter | Chip buttons with `hx-get` | HTMX |
| Result Card | Jinja2 partial template | Jinja2 |
| Score Badge | CSS class `.score-high/.score-mid/.score-low` | CSS |
| Empty State | Conditional Jinja2 block | Jinja2 |
| Error Alert | HTMX `hx-swap="outerHTML"` on error | HTMX |
| Login Form | Standard `<form>` POST | Native |
| Syntax Highlighting | Prism.js with custom dark theme | Prism.js |

**UCD Token Mapping**: All UCD style tokens defined as CSS custom properties (`--color-primary`, `--font-code`, etc.) in `:root`. Components reference tokens directly. Developer Dark syntax highlighting colors mapped to a custom Prism.js theme.

**Responsive**: CSS Grid + media queries for 3 breakpoints (Desktop ≥1024, Tablet 768-1023, Mobile <768).

## 8. Third-Party Dependencies

| Library / Framework | Version | Purpose | License | Compatibility |
|---|---|---|---|---|
| Python | 3.11+ | Runtime | PSF | Base |
| fastapi | ^0.115.0 | Web framework | MIT | Python ≥3.8 |
| uvicorn[standard] | ^0.34.0 | ASGI server | BSD-3 | Python ≥3.8 |
| gunicorn | ^23.0.0 | Process manager | MIT | Python ≥3.7 |
| celery[redis] | ^5.4.0 | Task queue | BSD-3 | Python ≥3.8 |
| redis | ^5.2.0 | Redis client | MIT | Python ≥3.8 |
| sqlalchemy[asyncio] | ^2.0.36 | ORM + async | MIT | Python ≥3.7 |
| asyncpg | ^0.30.0 | PostgreSQL async driver | Apache-2.0 | Python ≥3.8 |
| alembic | ^1.14.0 | DB migrations | MIT | SQLAlchemy ≥1.4 |
| qdrant-client | ^1.12.0 | Qdrant vector DB client | Apache-2.0 | Python ≥3.8 |
| elasticsearch[async] | ^8.17.0 | Elasticsearch client | Apache-2.0 | ES 8.x |
| sentence-transformers | ^3.3.0 | Embedding encoder (bge-code) | Apache-2.0 | PyTorch ≥1.11 |
| torch | ^2.5.0 | ML runtime | BSD-3 | Python ≥3.8, CUDA 12.x opt |
| tree-sitter | ^0.24.0 | Code parser | MIT | Python ≥3.9 |
| tree-sitter-java | ^0.23.0 | Java grammar | MIT | tree-sitter ≥0.22 |
| tree-sitter-python | ^0.23.0 | Python grammar | MIT | tree-sitter ≥0.22 |
| tree-sitter-typescript | ^0.23.0 | TS/JS grammar | MIT | tree-sitter ≥0.22 |
| tree-sitter-c | ^0.23.0 | C grammar | MIT | tree-sitter ≥0.22 |
| tree-sitter-cpp | ^0.23.0 | C++ grammar | MIT | tree-sitter ≥0.22 |
| mcp | ^1.0.0 | MCP protocol SDK | MIT | Python ≥3.10 |
| gitpython | ^3.1.43 | Git operations | BSD-3 | Python ≥3.7 |
| jinja2 | ^3.1.4 | Template engine | BSD-3 | Python ≥3.7 |
| passlib[bcrypt] | ^1.7.4 | API key hashing | BSD-2 | Python ≥3.7 |
| pydantic | ^2.10.0 | Data validation | MIT | Python ≥3.8 |
| prometheus-client | ^0.21.0 | Metrics export | Apache-2.0 | Python ≥3.8 |
| httpx | ^0.28.0 | HTTP client (testing) | BSD-3 | Python ≥3.8 |
| pytest | ^8.3.0 | Testing framework | MIT | Python ≥3.8 |
| pytest-asyncio | ^0.24.0 | Async test support | Apache-2.0 | pytest ≥7.0 |

### 8.1 Version Constraints

- **torch ≥2.5**: Required for sentence-transformers ≥3.3 compatibility
- **tree-sitter ≥0.24**: New Python bindings API; tree-sitter-language packages ≥0.23 required
- **elasticsearch ≥8.17**: Required for ES 8.x cluster compatibility
- **mcp ≥1.0**: Stable MCP SDK; earlier versions had breaking API changes

### 8.2 Dependency Graph

```mermaid
graph LR
    App["Application"]
    App --> FastAPI["fastapi ^0.115"]
    App --> Celery["celery ^5.4"]
    App --> ST["sentence-transformers ^3.3"]
    App --> TS["tree-sitter ^0.24"]
    App --> MCP["mcp ^1.0"]

    FastAPI --> Pydantic["pydantic ^2.10"]
    FastAPI --> Uvicorn["uvicorn ^0.34"]

    ST --> Torch["torch ^2.5"]
    ST --> HF["huggingface-hub"]

    Celery --> Redis["redis ^5.2"]

    App --> SQLAlchemy["sqlalchemy ^2.0"]
    SQLAlchemy --> Asyncpg["asyncpg ^0.30"]

    App --> QdrantC["qdrant-client ^1.12"]
    App --> ESC["elasticsearch ^8.17"]

    TS --> TSJava["tree-sitter-java"]
    TS --> TSPy["tree-sitter-python"]
    TS --> TSTS["tree-sitter-typescript"]
    TS --> TSC["tree-sitter-c/cpp"]
```

**License audit**: All MIT/BSD/Apache-2.0. No GPL/AGPL risk.

## 9. Testing Strategy

| Test Type | Scope | Tooling | Coverage Target |
|-----------|-------|---------|----------------|
| Unit | Individual module logic | pytest + pytest-asyncio | ≥80% line coverage |
| Integration | Module interactions (API→Handler→ES/Qdrant) | pytest + testcontainers | All FR acceptance criteria |
| Load | NFR-001/002 performance verification | k6 | P95 ≤ 1000ms @ 1000 QPS |
| E2E (MCP) | MCP protocol end-to-end | pytest + mcp SDK | FR-013 acceptance criteria |
| E2E (Web UI) | Web UI end-to-end | Playwright | FR-014/015 acceptance criteria |
| Chaos | Single-node failure tolerance | Manual kill + verify | NFR-007 |
| Security | Authentication bypass attempts | pytest | FR-018 acceptance criteria |

**Test doubles**: Integration tests use testcontainers to spin up real ES/Qdrant/PG/Redis containers — no mocking of storage layer.

## 10. Deployment / Infrastructure

```
Load Balancer (Nginx/Traefik)
├── Query Service Node 1 (:8000) — Gunicorn + Uvicorn workers
├── Query Service Node 2 (:8000) — Gunicorn + Uvicorn workers
└── Query Service Node N (:8000)

Indexing Service (Celery Workers + Beat)
├── Worker 1
├── Worker 2
└── Worker N

Storage Layer
├── Qdrant Cluster
├── Elasticsearch Cluster (3 nodes)
├── PostgreSQL (HA)
└── Redis (HA)
```

- **Containerization**: Docker Compose (dev) / Kubernetes (prod)
- **Query Service**: Stateless, Deployment 2+ replicas, HPA based on CPU/QPS
- **Indexing Workers**: StatefulSet or Deployment, scale based on task queue length
- **Storage Layer**: Official Docker images or cloud-managed services

## 11. Development Plan

### 11.1 Milestones

| Milestone | Scope | Exit Criteria |
|-----------|-------|---------------|
| M1: Foundation | Project skeleton, CI, core abstractions, storage clients | Build passes, dev environment reproducible |
| M2: Indexing Pipeline | Repo management + clone + parse + chunk + embed + write index | Can index a Git repo and generate chunks |
| M3: Query Pipeline | Query handling + keyword + semantic + fusion + rerank + response | Can execute query and return Top-3 results |
| M4: Interfaces | MCP server + REST API + auth + Web UI + language filter | All interfaces functional |
| M5: Operations | Scheduled refresh + manual reindex + metrics + logging | Operational features complete |
| M6: Polish & Release | NFR verification, documentation, load/chaos testing | All quality gates met, release-ready |

### 11.2 Task Decomposition & Priority

| Priority | Feature | FR Trace | Dependencies | Milestone |
|----------|---------|----------|-------------|-----------|
| P0 | Project skeleton + CI + storage clients | — | None | M1 |
| P0 | Data model + migrations | — | Skeleton | M1 |
| P1 | Repository registration | FR-001 | Data model | M2 |
| P1 | Git clone/update | FR-002 | FR-001 | M2 |
| P1 | Content extraction | FR-003 | FR-002 | M2 |
| P1 | Code chunking (tree-sitter) | FR-004 | FR-003 | M2 |
| P1 | Embedding generation + index writing | FR-009 (partial) | FR-004 | M2 |
| P1 | Keyword retrieval | FR-008 | M2 indexed data | M3 |
| P1 | Semantic retrieval | FR-009 | M2 indexed data | M3 |
| P1 | Rank fusion | FR-010 | FR-008, FR-009 | M3 |
| P1 | Neural reranking | FR-011 | FR-010 | M3 |
| P1 | Context response builder | FR-012 | FR-011 | M3 |
| P1 | Query handler (NL + Symbol + Repo-scoped) | FR-005/006/007 | FR-012 | M3 |
| P1 | API key authentication | FR-018 | Data model | M4 |
| P1 | REST API endpoints | FR-005-012 | FR-018, Query pipeline | M4 |
| P1 | MCP server | FR-013 | REST API | M4 |
| P2 | Web UI search page | FR-014 | REST API, UCD | M4 |
| P2 | Language filter | FR-015 | Query pipeline | M4 |
| P2 | Web UI login page | FR-018 | FR-014 | M4 |
| P1 | Scheduled index refresh | FR-016 | Indexing pipeline | M5 |
| P1 | Manual reindex trigger | FR-017 | FR-016 | M5 |
| P1 | Metrics endpoint | NFR-008 | Query pipeline | M5 |
| P1 | Query logging | NFR-009 | Query pipeline | M5 |

### 11.3 Dependency Chain

```mermaid
graph LR
    SK["Skeleton + CI<br/>P0"] --> DM["Data Model<br/>P0"]
    DM --> R1["Repo Registration<br/>FR-001 P1"]
    R1 --> R2["Git Clone/Update<br/>FR-002 P1"]
    R2 --> R3["Content Extract<br/>FR-003 P1"]
    R3 --> R4["Code Chunking<br/>FR-004 P1"]
    R4 --> EMB["Embedding + Write<br/>FR-009p P1"]

    EMB --> KR["Keyword Retrieval<br/>FR-008 P1"]
    EMB --> SemR["Semantic Retrieval<br/>FR-009 P1"]
    KR --> FUSE["Rank Fusion<br/>FR-010 P1"]
    SemR --> FUSE
    FUSE --> RERANK["Neural Rerank<br/>FR-011 P1"]
    RERANK --> RESP["Response Builder<br/>FR-012 P1"]
    RESP --> QH["Query Handler<br/>FR-005/006/007 P1"]

    DM --> AUTH["Auth Middleware<br/>FR-018 P1"]
    QH --> API["REST API<br/>P1"]
    AUTH --> API
    API --> MCPS["MCP Server<br/>FR-013 P1"]

    API --> WEBUI["Web UI Search<br/>FR-014 P2"]
    QH --> LANG["Language Filter<br/>FR-015 P2"]
    WEBUI --> LOGIN["Web UI Login<br/>FR-018p P2"]

    R1 --> SCHED["Scheduled Refresh<br/>FR-016 P1"]
    EMB --> SCHED
    SCHED --> MANUAL["Manual Reindex<br/>FR-017 P1"]

    QH --> METRICS["Metrics<br/>NFR-008 P1"]
    QH --> QLOG["Query Log<br/>NFR-009 P1"]
```

### 11.4 Risk & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| bge-code embedding quality insufficient (nDCG@3 < 0.7) | High | Med | Prepare fallback models (CodeBERT, UniXcoder); embedding layer decoupled for hot-swap |
| Qdrant/ES cluster latency exceeds target at 1000 QPS | High | Low | Early M3 benchmarking; shard + replica tuning; add read replicas if needed |
| tree-sitter edge cases in some language constructs | Med | Med | Degrade to file-level chunk (FR-004 AC2); progressive language support |
| PyTorch GPU inference too slow on CPU-only environments | High | Med | Early M3 CPU vs GPU benchmarking; consider ONNX Runtime as lightweight alternative |
| MCP SDK version instability | Med | Low | Pin verified version; thin MCP interface wrapper for easy SDK upgrade |

## 12. Open Questions / Risks

The following SRS Open Questions are resolved by this design:

1. **Rate limiting**: Deferred to M5. Initial implementation uses global capacity limit only. Per-key rate limiting can be added via middleware (token bucket in Redis).
2. **Multi-tenancy**: V1 — all authenticated users see all repos. Repo-level ACL is a V2 feature requiring API key → repo mapping table.
3. **Index retention**: V1 — replace immediately (delete old chunks, write new). Rollback requires versioned collection naming in Qdrant/ES (V2 feature).
4. **Embedding model**: Resolved — BAAI/bge-code-v1 for embeddings, BAAI/bge-reranker-v2-m3 for reranking.
5. **Web UI depth**: Resolved — Web UI is search-only (FR-014/015). Admin operations (repo registration, reindex) via REST API only.
