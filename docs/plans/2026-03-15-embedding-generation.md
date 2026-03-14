# Feature #7: Embedding Generation and Index Writing

**Date**: 2026-03-15
**Feature ID**: 7
**Category**: M2: Core Indexing
**Priority**: high

## Overview

Implement embedding generation for code chunks using bge-code model and write indexed content to both Elasticsearch (keyword search) and Qdrant (vector search). This feature completes the indexing pipeline after code chunking (Feature #6).

## Design Reference

From `docs/plans/2026-03-14-code-context-retrieval-design.md`:
- **Section 4.5**: Embedding & Reranking Models
- **Class**: `EmbeddingEncoder` with `encode()` and `encode_query()` methods
- **Class**: `IndexWriter` with `write_chunks()` and `delete_by_repo()` methods
- Uses `sentence-transformers` library for bge-code-v1 embeddings
- Batch size: 64 for bulk inference

## Dependencies

- Feature #6: Code Chunking (completed, passing)
- Storage services: PostgreSQL, Qdrant, Elasticsearch

## Implementation Tasks

### Task 1: EmbeddingEncoder Class

Create `src/indexing/embedding_encoder.py`:

1. **Constructor**: Load sentence-transformers model (BAAI/bge-code-v1)
2. **encode(texts: list[str])**: Batch encode code chunks, return list of vectors
3. **encode_query(query: str)**: Encode single query with query prefix
4. **dimension property**: Return embedding dimension (1024 for bge-code-v1)

**Key design decisions**:
- Model loaded once at instantiation (lazy loading)
- Prefer GPU (`device="cuda"`) if available, fallback to CPU
- Handle empty input gracefully

### Task 2: IndexWriter Class

Create `src/indexing/index_writer.py`:

1. **Constructor**: Initialize QdrantClient and AsyncElasticsearch clients
2. **write_chunks(chunks: list[CodeChunk], embeddings: list[Vector])**:
   - Write to Elasticsearch: content, metadata (repo_id, file_path, language, symbol_name, chunk_id)
   - Write to Qdrant: vectors with payload (repo_id, file_path, language, chunk_id)
   - Use batch writes for efficiency
3. **delete_by_repo(repo_id: UUID)**: Delete all chunks for a repository before re-indexing

**Key design decisions**:
- Elasticsearch index name: `code_chunks`
- Qdrant collection name: `code_chunks`
- Qdrant uses payload filtering by repo_id

### Task 3: Unit Tests

Create `tests/test_embedding_encoder.py`:
- Test encode returns correct number of vectors
- Test encode returns correct dimension (1024)
- Test encode_query works
- Test empty input handling
- Test GPU/CPU fallback

Create `tests/test_index_writer.py`:
- Test write_chunks to Elasticsearch
- Test write_chunks to Qdrant
- Test delete_by_repo removes all chunks
- Test batch writing efficiency

### Task 4: Integration

- Integrate with existing indexing pipeline in `src/indexing/tasks.py` (or create new Celery task)
- Handle embedding generation + index writing as single atomic operation

## Acceptance Criteria

| ID | Criterion | Test |
|----|-----------|------|
| AC1 | Given 100 code chunks, when embedding generation runs, then 100 embedding vectors are produced with correct dimension | Unit test |
| AC2 | Given embeddings and chunks, when writing to indices, then Elasticsearch contains 100 documents with content, metadata, and chunk_id | Integration test |
| AC3 | Given embeddings and chunks, when writing to indices, then Qdrant collection contains 100 points with same chunk_ids | Integration test |
| AC4 | Given an existing repository being re-indexed, when writing new chunks, then old chunks for that repo_id are deleted first | Integration test |

## Files to Create/Modify

- `src/indexing/embedding_encoder.py` (new)
- `src/indexing/index_writer.py` (new)
- `tests/test_embedding_encoder.py` (new)
- `tests/test_index_writer.py` (new)
- `src/indexing/__init__.py` (update exports)
- `src/indexing/tasks.py` (integrate if exists, or create)

## Notes

- Feature #7 is part of the indexing pipeline, not query pipeline
- Feature #8 (Keyword Retrieval) and #9 (Semantic Retrieval) depend on this feature
- Uses sentence-transformers >= 3.3.0 as per design doc
