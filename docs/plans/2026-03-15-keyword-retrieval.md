# Implementation Plan — Feature #8: Keyword Retrieval (FR-008)

**Date**: 2026-03-15
**Feature**: Keyword Retrieval (FR-008)
**Status**: In Progress

## Overview

Implement KeywordRetriever class for BM25-based keyword search against Elasticsearch. This is part of the Query Pipeline (FR-005–FR-012) that retrieves candidate chunks using lexical search.

## Design Reference

From `docs/plans/2026-03-14-code-context-retrieval-design.md` Section 4.2:

- **Class**: `KeywordRetriever`
- **Interface**: `retrieve(query: str, filters: dict) -> list[Candidate]`
- **Storage**: AsyncElasticsearch
- **Index**: `code_chunks` (standard name for keyword index)
- **Search Type**: BM25

## Implementation Steps

### Step 1: Create KeywordRetriever class

**File**: `src/query/retriever.py` (new file)

Create the KeywordRetriever class:
- Accept AsyncElasticsearch client and index name in constructor
- Implement `retrieve(query: str, filters: dict) -> list[Candidate]` method
- Use BM25 search via Elasticsearch `multi_match` query
- Apply filters for repo_filter and language_filter
- Return list of Candidate objects with score

### Step 2: Create Candidate dataclass

**File**: `src/query/models.py` (new file or extend existing)

Create Candidate dataclass:
- chunk_id: str
- repo_name: str
- file_path: str
- symbol: str | None
- content: str
- score: float

### Step 3: Create unit tests

**File**: `tests/test_keyword_retriever.py` (new file)

Write tests for:
1. Query matching - matching chunks appear in results
2. No match - empty list returned
3. Repo filter - only chunks from specified repo
4. Language filter - only chunks in specified language
5. Combined filters - repo + language filter
6. Error handling - connection errors

### Step 4: Run TDD cycle

- Red: Tests fail (no implementation)
- Green: Implement minimum code to pass tests
- Refactor: Clean up code while keeping tests green

## Acceptance Criteria (from SRS FR-008)

| ID | Criterion | Test |
|----|-----------|------|
| AC1 | Query "WebClient timeout" matches chunk with "WebClient.builder().responseTimeout() | Verify matching chunk in results |
| AC2 | Query with no matches returns empty list | Verify empty list returned |
| AC3 | Query with repo filter returns only that repo's chunks | Verify repo_name matches filter |
| AC4 | Query with language filter returns only that language | Verify language matches filter |

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/query/models.py` | Create Candidate dataclass |
| `src/query/retriever.py` | Create KeywordRetriever class |
| `tests/test_keyword_retriever.py` | Create unit tests |
| `src/query/__init__.py` | Export KeywordRetriever, Candidate |

## Dependencies

- Feature #7 (Embedding Generation) - provides index structure
- Elasticsearch connection - via storage clients
