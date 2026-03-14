# Implementation Plan: Feature #9 - Semantic Retrieval (FR-009)

**Date**: 2026-03-15
**Feature**: #9 Semantic Retrieval (FR-009)
**Status**: Draft

## Overview

Implement Semantic Retrieval using Qdrant vector similarity search with embedding-based retrieval. This feature retrieves candidate chunks that are semantically similar to the query's meaning using vector embeddings, with configurable similarity threshold (default 0.6).

## Design Summary

From `docs/plans/2026-03-14-code-context-retrieval-design.md`:

- **Class**: `SemanticRetriever`
- **Dependencies**:
  - `qdrant`: AsyncQdrantClient
  - `encoder`: EmbeddingEncoder
  - `threshold`: float (default 0.6)
- **Method**: `retrieve(query: str, filters: dict) -> list[Candidate]`

## Implementation Tasks

### Task 1: Add SemanticRetriever Class

Location: `src/query/retriever.py`

Add a new `SemanticRetriever` class that:
1. Accepts Qdrant client, EmbeddingEncoder, and threshold parameter
2. Encodes query text into embedding using the encoder
3. Performs vector search in Qdrant collection
4. Filters results by configurable threshold (default 0.6)
5. Applies repo_filter and language_filter if provided
6. Returns list of Candidate objects

### Task 2: Qdrant Collection Configuration

From design:
- Collection name: `code_chunks` (or configurable)
- Vector field: `embedding`
- Payload fields: `chunk_id`, `repo_name`, `file_path`, `symbol`, `content`, `language`

### Task 3: Implement retrieve() Method

```python
async def retrieve(self, query: str, filters: dict) -> list[Candidate]:
    # 1. Validate query
    # 2. Encode query to embedding
    # 3. Build Qdrant search query with filters
    # 4. Execute vector search
    # 5. Filter by threshold
    # 6. Convert to Candidate objects
```

### Task 4: Handle Filters

- `repo_filter`: Filter by `repo_name` in Qdrant payload
- `language_filter`: Filter by `language` in Qdrant payload

### Task 5: Write Unit Tests

Create tests in `tests/test_retriever.py` covering:
- Happy path: semantic search returns matching results
- No matches: empty list when below threshold
- Configurable threshold: threshold=0.8 filters more results
- Repo filter: only returns chunks from specified repo
- Language filter: only returns chunks in specified language
- Empty query: raises ValueError

## Verification Steps

From `feature-list.json`:

1. Given query 'how to configure spring http client timeout' and indexed chunks about WebClient timeout, when semantic retrieval executes, then semantically related chunks appear despite keyword mismatch
2. Given a query with no semantic matches above threshold 0.6, when semantic retrieval executes, then empty candidate list is returned
3. Given threshold configured to 0.8, when semantic retrieval executes, then only chunks with similarity >= 0.8 are returned
4. Given query with repo filter, when semantic retrieval executes, then only chunks from specified repo are returned

## Dependencies

- Feature #7 (Embedding Generation and Index Writing) must be passing - ✅ PASSING
- QDRANT_URL config must be set - ✅ CONFIGURED
- EMBEDDING_MODEL config must be set - ✅ CONFIGURED

## Technical Details

- Use `AsyncQdrantClient.search()` with `query_vector`
- Score field from Qdrant is the similarity score
- Default collection: `code_chunks`
- Default threshold: 0.6
- Max results: 100 (same as KeywordRetriever)

## Files to Modify

1. `src/query/retriever.py` - Add SemanticRetriever class
2. `tests/test_retriever.py` - Add unit tests (new or extend existing)
