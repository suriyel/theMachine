# Plan: Neural Reranking (Feature #11)

**Date**: 2026-03-15
**Feature**: #11 — Neural Reranking (FR-011)
**Priority**: high
**Dependencies**: Feature #10 (Rank Fusion) - passing
**Design Reference**: docs/plans/2026-03-14-code-context-retrieval-design.md § 4.5

## Context

Feature #11 implements neural reranking for the query pipeline. After keyword and semantic retrieval fuse results using RRF, the NeuralReranker reorders candidates using a cross-encoder model (bge-reranker-v2-m3) to achieve better relevance ranking. This improves nDCG@3 score to >= 0.7.

## Design Alignment

### Key Classes (from Design § 4.5)
- **NeuralReranker**: Main class for reranking candidates
  - `model: CrossEncoder` - sentence-transformers CrossEncoder
  - `model_name: str = "BAAI/bge-reranker-v2-m3"` - configured via RERANKER_MODEL env
  - `max_length: int = 512` - token limit for truncation
  - `rerank(query: str, candidates: list[Candidate]) -> list[Candidate]` - main method

### Interaction Flow
1. QueryHandler receives fused candidate list from RankFusion
2. QueryHandler calls NeuralReranker.rerank(query, candidates)
3. NeuralReranker uses CrossEncoder to score query-document pairs
4. Candidates are reordered by relevance score descending
5. Returns reordered list to QueryHandler

### Third-Party Dependencies
- sentence-transformers (CrossEncoder)
- torch (backend for sentence-transformers)
- Environment: RERANKER_MODEL=BAAI/bge-reranker-v2-m3

### Design Notes (from § 4.5.3)
- **Model loading**: Models loaded once at service startup, not per-request
- **GPU inference**: Prefers GPU (`device="cuda"`) when available; degrades to CPU otherwise
- **Reranker truncation**: Inputs exceeding max_length=512 tokens are truncated to prevent OOM

### Deviations
None - plan aligns with design.

## SRS Requirement

### FR-011: Rerank Results
**Priority**: Must
**EARS**: When a fused candidate list is produced, the system shall reorder candidates using neural query-document relevance scoring, achieving nDCG@3 >= 0.7 on the evaluation dataset.
**Acceptance Criteria**:
- Given a fused candidate list and a query from the evaluation dataset, when reranking executes, then the reranked results achieve nDCG@3 >= 0.7 as measured on the held-out evaluation set
- Given a fused candidate list with fewer than 2 items, when reranking executes, then the items are returned in their current order without applying the reranking model

## Verification Steps

From feature-list.json:
1. Given a fused candidate list with >= 2 items, when reranking executes, then candidates are reordered by neural relevance score
2. Given a fused candidate list with < 2 items, when reranking executes, then items are returned in current order without model invocation
3. Given evaluation dataset queries, when reranking is applied, then nDCG@3 >= 0.7 on held-out set

## Tasks

### Task 1: Write failing tests
**Files**: `tests/test_neural_reranker.py` (create)
**Steps**:
1. Create test file with imports (pytest, unittest.mock)
2. Write test cases:
   - Test 1 (Happy path): Reranker reorders candidates by score - mock CrossEncoder
   - Test 2 (Edge case): < 2 items returns original order without model call
   - Test 3 (Error handling): Empty candidate list returns empty list
   - Test 4 (Error handling): Model load failure raises appropriate exception
   - Test 5 (Boundary): Very long query gets truncated
3. Run: `pytest tests/test_neural_reranker.py`
4. **Expected**: All tests FAIL (no implementation yet)

### Task 2: Implement NeuralReranker class
**Files**: `src/query/reranker.py` (create)
**Steps**:
1. Create `src/query/reranker.py`:
   - Import CrossEncoder from sentence_transformers
   - Define Candidate dataclass (chunk_id, content, score, repo_id, file_path, symbol)
   - Create NeuralReranker class with:
     - `__init__(model_name: str, max_length: int = 512)`
     - `_load_model()` - load CrossEncoder, prefer cuda
     - `rerank(query: str, candidates: list[Candidate]) -> list[Candidate]`
   - Implement rerank:
     - If len(candidates) < 2: return original list
     - Build query-document pairs
     - Call model.predict() on pairs
     - Sort candidates by score descending
     - Return reordered list
2. Run: `pytest tests/test_neural_reranker.py`
3. **Expected**: All tests PASS

### Task 3: Refactor
- Clean up code structure
- Add docstrings
- Ensure type hints

### Task 4: Run quality gates
**Steps**:
1. Coverage: `pytest --cov=src --cov-branch --cov-report=term-missing`
   - Threshold: line >= 90%, branch >= 80%
2. Mutation: `mutmut run --paths-to-mutate=src/query/reranker.py`
   - Threshold: score >= 80%
3. Verify: All tests still pass

## Expected Artifacts

- `src/query/reranker.py` - NeuralReranker class
- `tests/test_neural_reranker.py` - Unit tests
- `examples/11-neural-reranking.py` - Usage example
