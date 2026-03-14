# Implementation Plan — Feature #13: Query Handler - Natural Language

**Date**: 2026-03-15
**Feature**: Query Handler - Natural Language (FR-005)
**Priority**: High
**Status**: In Progress

## 1. Overview

Implement the `QueryHandler` class that orchestrates the full retrieval pipeline:
1. Validate query input (non-empty, non-whitespace)
2. Execute keyword retrieval (parallel)
3. Execute semantic retrieval (parallel)
4. Fuse results using Reciprocal Rank Fusion
5. Apply neural reranking (if >= 2 candidates)
6. Build final response with top-k results

## 2. Class Design

### QueryHandler Class

```
QueryHandler
├── keyword_retriever: KeywordRetriever
├── semantic_retriever: SemanticRetriever
├── rank_fusion: RankFusion
├── reranker: NeuralReranker
├── response_builder: ContextResponseBuilder
├── cache: RedisCache (optional, for future)
├── semantic_threshold: float (from config)
├── rrf_k: int (from config)
├── top_k: int (from config)
│
├── handle(request: QueryRequest) -> QueryResponse
└── _validate_query(query: str) -> None (raises ValueError)
```

### QueryRequest (existing in endpoints/query.py)

```
QueryRequest
├── query: str (min_length=1)
├── query_type: str (natural_language/symbol)
├── repo: Optional[str]
├── language: Optional[str]
└── top_k: int (1-10)
```

### QueryResponse (existing in endpoints/query.py)

```
QueryResponse
├── results: List[ContextResult]
└── query_time_ms: float
```

## 3. Verification Steps

From feature-list.json:
1. **Given** natural language query 'how to use spring WebClient timeout', **when** submitted to QueryHandler, **then** query is accepted and retrieval pipeline initiated
2. **Given** empty query string, **when** submitted to QueryHandler, **then** validation error is returned indicating query must not be empty
3. **Given** query with only whitespace, **when** submitted to QueryHandler, **then** validation error is returned

## 4. Implementation Tasks

### Task 1: Create QueryHandler class (src/query/handler.py)

- Initialize with dependencies: KeywordRetriever, SemanticRetriever, RankFusion, NeuralReranker, ContextResponseBuilder
- Implement `handle(QueryRequest) -> QueryResponse` method
- Implement `_validate_query(query: str)` private method for validation

### Task 2: Implement validation logic

- Raise `ValueError` with clear message for empty/whitespace-only queries
- Validation happens BEFORE any retrieval to fail fast

### Task 3: Implement retrieval orchestration

- Build filters dict from request (repo_filter, language_filter)
- Execute keyword and semantic retrieval in parallel using `asyncio.gather()`
- Handle empty results gracefully (pass empty list to fusion)

### Task 4: Implement ranking pipeline

- Apply RankFusion to merge results
- Skip NeuralReranker if < 2 candidates (per design notes)
- Build final response with ContextResponseBuilder

### Task 5: Add timing

- Track query_time_ms and include in response

## 5. Test Cases to Write

### Unit Tests (test_handler.py)

1. `test_handle_valid_nl_query_initiates_pipeline` - Happy path
2. `test_handle_empty_query_raises_validation_error` - Empty string
3. `test_handle_whitespace_only_query_raises_validation_error` - Whitespace only
4. `test_handle_parallel_retrieval` - Both retrievers called
5. `test_handle_fusion_applied` - RankFusion receives both result sets
6. `test_handle_reranker_skipped_with_single_candidate` - < 2 candidates
7. `test_handle_reranker_applied_with_multiple_candidates` - >= 2 candidates
8. `test_handle_response_contains_timing` - query_time_ms included
9. `test_handle_empty_results_returns_empty_list` - No matches
10. `test_handle_repo_filter_passed_to_retrievers` - Filter propagation

## 6. Dependencies

- KeywordRetriever (existing: src/query/retriever.py)
- SemanticRetriever (existing: src/query/retriever.py)
- RankFusion (existing: src/query/rank_fusion.py)
- NeuralReranker (existing: src/query/reranker.py)
- ContextResponseBuilder (existing: src/query/response_builder.py)
- Settings (existing: src/query/config.py)

## 7. Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| src/query/handler.py | Create | QueryHandler class |
| tests/test_handler.py | Create | Unit tests |
| src/query/__init__.py | Modify | Export QueryHandler |
| src/query/api/v1/endpoints/query.py | Modify | Use QueryHandler |

## 8. Edge Cases

1. Empty query → ValueError with "query must not be empty"
2. Whitespace-only query → ValueError with "query must not be empty"
3. Single candidate → Skip reranking, return as-is
4. Both retrievers return empty → Return empty results
5. Repository filter → Pass to both retrievers
6. Language filter → Pass to both retrievers

## 9. Design Notes (from design doc)

- Parallel retrieval: KeywordRetriever and SemanticRetriever execute concurrently via `asyncio.gather()`
- Rank Fusion: Reciprocal Rank Fusion (RRF) with k=60
- Semantic threshold: default 0.6 from config
- Rerank degradation: Skip reranking when < 2 candidates
- Cache strategy: Not implemented in this feature (future)
