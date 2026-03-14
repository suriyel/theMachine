# code-context-retrieval — Examples

Runnable examples demonstrating completed features. Each example corresponds to a feature in `feature-list.json`.

## Index

| # | Feature | File | How to run |
|---|---------|------|------------|
| 01 | Project Skeleton and CI | [01-storage-clients.py](01-storage-clients.py) | `python examples/01-storage-clients.py` |

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

---

_Add a new row to the table above each time you create an example for a completed feature._
