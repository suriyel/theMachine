# Implementation Plan: Context Response Builder (FR-012)

## Feature
- **ID**: #12 Context Response Builder
- **FR**: FR-012
- **Priority**: High
- **Status**: Failing (dependencies: #11 passing ✓)

## SRS Requirements (FR-012)

From `docs/plans/2026-03-14-code-context-retrieval-srs.md`:

> **EARS**: The system shall return the top-3 most relevant context results, each including the repository name, file path, code symbol, relevance score, and content snippet.

**Acceptance Criteria**:
1. Given 50 ranked candidates after reranking, when response is built, then exactly 3 results are returned with fields: repository, path, symbol, score, content
2. Given zero candidates after full pipeline, when response is built, then empty results array is returned with no error
3. Given results with varying scores, when response is built, then results are ordered by score descending

## Design Context

From `docs/plans/2026-03-14-code-context-retrieval-design.md` Section 4.2:

- **Class**: QueryHandler orchestrates the pipeline
- **Sequence**: "QH->>QH: build top-3 response" (line 397)
- **Response Model**: `ContextResult` (repository, file_path, symbol, score, content)

Existing models in `src/query/api/v1/endpoints/query.py`:
- `ContextResult` dataclass with fields: repository, file_path, symbol (optional), score, content
- `QueryResponse` with: results (List[ContextResult]), query_time_ms

Existing `Candidate` in `src/query/retriever.py`:
- Fields: chunk_id, repo_name, file_path, symbol, content, score, language

## Implementation

### Files to Create/Modify

1. **Create**: `src/query/response_builder.py`
   - Create `ContextResponseBuilder` class

2. **Modify**: `src/query/__init__.py`
   - Export `ContextResponseBuilder`

3. **Create**: `tests/test_response_builder.py`
   - Unit tests for ContextResponseBuilder

4. **Create**: `examples/12-context-response-builder.py`
   - Runnable example

### Implementation Details

```python
class ContextResponseBuilder:
    """Builds ContextResult from Candidate list."""

    def __init__(self, top_k: int = 3):
        self._top_k = top_k

    def build(self, candidates: list[Candidate]) -> list[ContextResult]:
        """Build top-k context results from candidates.

        Args:
            candidates: List of Candidate objects (already ranked)

        Returns:
            List of ContextResult objects (max top_k), sorted by score descending
        """
        if not candidates:
            return []

        # Sort by score descending
        sorted_candidates = sorted(candidates, key=lambda c: c.score, reverse=True)

        # Take top k
        top_candidates = sorted_candidates[:self._top_k]

        # Transform to ContextResult
        return [
            ContextResult(
                repository=c.repo_name,
                file_path=c.file_path,
                symbol=c.symbol,
                score=c.score,
                content=c.content,
            )
            for c in top_candidates
        ]
```

### Edge Cases

1. **Empty list**: Return empty list (no error)
2. **Less than top_k candidates**: Return all available (sorted by score)
3. **Candidates with same score**: Order by chunk_id for stability

### TDD Tasks

1. **Red Phase** (write failing tests):
   - Test build with 50 candidates returns 3 results
   - Test build with 0 candidates returns empty list
   - Test results are ordered by score descending
   - Test transform has correct fields

2. **Green Phase** (implement minimal code):
   - Implement ContextResponseBuilder class

3. **Refactor Phase**:
   - Ensure clean code structure

### Quality Gates

- Line coverage >= 90%
- Branch coverage >= 80%
- Mutation score >= 80% (Windows: skipped)

## Verification Steps

1. Given 50 ranked candidates, when response built, then exactly 3 results
2. Given zero candidates, when response built, then empty results
3. Given results with varying scores, when response built, then ordered by score descending
