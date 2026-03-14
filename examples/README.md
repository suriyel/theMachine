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

---

_Add a new row to the table above each time you create an example for a completed feature._
