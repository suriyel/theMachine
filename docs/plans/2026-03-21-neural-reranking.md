# Feature #11 — Neural Reranking: Detailed Design

**Date**: 2026-03-21
**Feature ID**: 11
**FR**: FR-009
**Dependencies**: Feature #10 (Rank Fusion)
**Priority**: High

---

## 1. Overview

The Reranker module scores query-document pairs using a cross-encoder model (bge-reranker-v2-m3 via sentence-transformers) and selects the top-K results from fused candidates. On model failure, it falls back to the fusion-ranked order (passthrough) and logs a degradation warning.

**Verification Steps**:
- VS-1: Given 50 fused candidates and a query, when rerank() runs, then it returns top-6 candidates re-scored by the cross-encoder with relevance scores
- VS-2: Given fewer than 3 candidates, when rerank() runs, then it returns all available candidates without error
- VS-3: Given a reranker model failure (OOM, load error), when rerank() runs, then it falls back to the fusion-ranked order and logs a degradation warning

**Related NFRs**:
- NFR-001: p95 query latency < 1000 ms — reranker contributes ~260ms (p95) for 50 candidates in 2 batches of 32
- NFR-002: ≥ 1000 QPS sustained — reranker must not block; stateless per-request

---

## 2. Component Data-Flow Diagram

N/A — single-class feature, see Interface Contract below.

The `Reranker` class wraps a `CrossEncoder` model instance and exposes a single `rerank()` method. No internal component collaboration; data flows: query + candidates in → scored candidates out.

---

## 3. Interface Contract

| Method | Signature | Preconditions | Postconditions | Raises |
|--------|-----------|---------------|----------------|--------|
| `__init__` | `Reranker(model_name: str = "BAAI/bge-reranker-v2-m3")` | model_name is a valid sentence-transformers cross-encoder identifier | `self._model` is a loaded `CrossEncoder` instance; `self._model_loaded` is `True` | `RerankerModelError` if model fails to load (OOM, invalid name, download failure) |
| `rerank` | `rerank(query: str, candidates: list[ScoredChunk], top_k: int = 6) -> list[ScoredChunk]` | `query` is non-empty string; `candidates` is a list of `ScoredChunk` (may be empty); `top_k >= 1` | Returns `list[ScoredChunk]` of length `min(top_k, len(candidates))`, sorted by cross-encoder score descending; each chunk's `score` field is replaced with the cross-encoder relevance score | `RerankerModelError` is caught internally → fallback to input order |

**Fallback behavior** (captured in `rerank` postconditions):
- If `self._model` is `None` (failed to load at init): return `candidates[:top_k]` with original scores, log warning
- If model inference raises any exception at runtime: return `candidates[:top_k]` with original scores, log warning
- If `candidates` is empty: return `[]`
- If `len(candidates) <= top_k`: return all candidates re-scored (no truncation needed)

**Verification step traceability**:
- VS-1 → `rerank` postcondition: returns top-6 re-scored by cross-encoder
- VS-2 → `rerank` postcondition: returns all available candidates when fewer than top_k
- VS-3 → `rerank` fallback behavior: model failure → passthrough + warning log

---

## 4. Internal Sequence Diagram

N/A — single-class implementation, error paths documented in Algorithm §5 error handling table.

The `rerank()` method is a single linear flow: build pairs → predict scores → sort → truncate. No cross-method delegation.

---

## 5. Algorithm / Core Logic

### 5a. Flow Diagram — `rerank()`

```mermaid
flowchart TD
    START([rerank called]) --> CHK_EMPTY{candidates empty?}
    CHK_EMPTY -- YES --> RET_EMPTY([return empty list])
    CHK_EMPTY -- NO --> CHK_MODEL{model loaded?}
    CHK_MODEL -- NO --> FALLBACK[return candidates[:top_k] with original scores + log warning]
    CHK_MODEL -- YES --> BUILD[Build query-content pairs]
    BUILD --> PREDICT{model.predict succeeds?}
    PREDICT -- NO --> FALLBACK
    PREDICT -- YES --> ASSIGN[Assign cross-encoder scores to chunks]
    ASSIGN --> SORT[Sort by score descending]
    SORT --> TRUNC[Truncate to top_k]
    TRUNC --> RET([return scored chunks])
```

### 5b. Pseudocode — `rerank()`

```
FUNCTION rerank(query: str, candidates: list[ScoredChunk], top_k: int = 6) -> list[ScoredChunk]
  // Step 1: Handle empty input
  IF candidates is empty THEN return []

  // Step 2: Check model availability
  IF self._model is None THEN
    log.warning("Reranker model not loaded, falling back to fusion order")
    return candidates[:top_k]

  // Step 3: Build query-document pairs for cross-encoder
  pairs = [(query, chunk.content) for chunk in candidates]

  // Step 4: Score pairs using cross-encoder
  TRY
    scores = self._model.predict(pairs, batch_size=32)
  CATCH Exception as e
    log.warning("Reranker inference failed: %s, falling back to fusion order", e)
    return candidates[:top_k]

  // Step 5: Assign scores and sort
  scored = [replace(chunk, score=float(score)) for chunk, score in zip(candidates, scores)]
  scored.sort(key=lambda c: c.score, reverse=True)

  // Step 6: Truncate and return
  return scored[:top_k]
END
```

### 5b-ii. Pseudocode — `__init__()`

```
FUNCTION __init__(model_name: str = "BAAI/bge-reranker-v2-m3")
  self._model_name = model_name
  self._model = None
  TRY
    self._model = CrossEncoder(model_name)
  CATCH Exception as e
    log.warning("Failed to load reranker model '%s': %s", model_name, e)
    // _model remains None — rerank() will use fallback path
END
```

### 5c. Boundary Decisions Table

| Parameter | Min | Max | Empty/Null | At boundary |
|-----------|-----|-----|------------|-------------|
| `candidates` | 0 items | unlimited | Return `[]` | 0 → `[]`; 1 → single item re-scored and returned |
| `top_k` | 1 | unlimited | N/A (int) | 1 → return single best; `top_k > len(candidates)` → return all |
| `query` | 1 char | unlimited | N/A (non-empty precondition) | Short queries work normally |
| `scores` (from model) | -∞ | +∞ | N/A | Negative scores are valid cross-encoder outputs; ordering preserved |

### 5d. Error Handling Table

| Condition | Detection | Response | Recovery |
|-----------|-----------|----------|----------|
| Model file not found / download fails | `CrossEncoder()` raises `OSError` or `HTTPError` | Log warning, set `_model = None` | `rerank()` uses fallback (passthrough) |
| Model OOM at load time | `CrossEncoder()` raises `RuntimeError` / `MemoryError` | Log warning, set `_model = None` | `rerank()` uses fallback |
| Model inference OOM / runtime error | `model.predict()` raises any `Exception` | Log warning, return `candidates[:top_k]` | Caller receives degraded but valid results |
| Empty candidates list | `len(candidates) == 0` | Return `[]` immediately | No action needed |
| Model returns NaN scores | `float(score)` produces NaN | NaN sorts unpredictably | Treat as fallback — check for NaN in scores, if any NaN detected, fall back to input order |

---

## 6. State Diagram

N/A — stateless feature. The `Reranker` is initialized once with a model and processes each `rerank()` call independently. No lifecycle states.

---

## 7. Test Inventory

| ID | Category | Traces To | Input / Setup | Expected | Kills Which Bug? |
|----|----------|-----------|---------------|----------|-----------------|
| T1 | happy path | VS-1, FR-009 AC-1 | 50 ScoredChunks with distinct content, query="spring webclient timeout", top_k=6 | Returns 6 chunks, each with cross-encoder score, sorted descending | Missing re-scoring: returning fusion scores instead of cross-encoder scores |
| T2 | happy path | VS-1 | 10 candidates, top_k=6 | Returns 6 chunks re-scored | Wrong truncation: returning more than top_k |
| T3 | boundary | VS-2, FR-009 AC-2 | 2 candidates, top_k=6 | Returns 2 chunks (all available), no error | Off-by-one: crashing when candidates < top_k |
| T4 | boundary | VS-2 | 1 candidate, top_k=6 | Returns 1 chunk re-scored | Edge case: single item list handling |
| T5 | boundary | §5c | 0 candidates (empty list), top_k=6 | Returns `[]` | Missing empty check: index error on empty list |
| T6 | error | VS-3, FR-009 AC-3 | Model fails to load (mock CrossEncoder raising RuntimeError), then call rerank() | Returns candidates[:top_k] in original order, warning logged | Missing fallback: raising exception to caller |
| T7 | error | VS-3, §5d | Model loaded but predict() raises RuntimeError during inference | Returns candidates[:top_k] in original order, warning logged | Missing try/except around predict() |
| T8 | boundary | §5c | top_k=1, 10 candidates | Returns exactly 1 chunk (the highest scored) | Wrong slice: returning all instead of top_k |
| T9 | happy path | §5b | Verify scores are float cross-encoder values, not original fusion scores | Each returned chunk.score != original score (replaced with CE score) | Bug: forgetting to replace score field |
| T10 | error | §5d NaN row | Model returns NaN for some scores | Falls back to input order, warning logged | NaN propagation causing sort failure |
| T11 | happy path | §3 postcondition | Verify return order is descending by score | `result[i].score >= result[i+1].score` for all i | Missing sort or wrong sort direction |

**Negative test ratio**: 5 negative (T5, T6, T7, T8, T10) / 11 total = 45% ≥ 40% ✓

---

## 8. TDD Task Decomposition

### Task 1: Write failing tests
**Files**: `tests/test_reranker.py`
**Steps**:
1. Create test file with imports (`ScoredChunk`, `Reranker`, `unittest.mock`, `pytest`, `math`)
2. Create helper `_make_chunks(n)` that generates n `ScoredChunk` instances with distinct `chunk_id` and `content`
3. Write tests T1–T11 from Test Inventory (§7):
   - T1: `test_rerank_50_candidates_returns_top6_rescored` — mock CrossEncoder.predict to return descending scores, verify 6 results with CE scores
   - T2: `test_rerank_10_candidates_top6` — 10 candidates, verify 6 returned
   - T3: `test_rerank_fewer_than_topk` — 2 candidates, top_k=6, verify 2 returned
   - T4: `test_rerank_single_candidate` — 1 candidate, verify 1 returned
   - T5: `test_rerank_empty_candidates` — empty list, verify `[]`
   - T6: `test_rerank_model_load_failure_fallback` — mock CrossEncoder init to raise, verify fallback
   - T7: `test_rerank_inference_failure_fallback` — mock predict to raise, verify fallback + warning
   - T8: `test_rerank_topk_one` — top_k=1, verify single result
   - T9: `test_rerank_scores_replaced` — verify chunk scores are CE scores, not originals
   - T10: `test_rerank_nan_scores_fallback` — mock predict to return NaN, verify fallback
   - T11: `test_rerank_descending_order` — verify output sorted descending
4. Run: `pytest tests/test_reranker.py -v`
5. **Expected**: All tests FAIL (ImportError or assertion failures)

### Task 2: Implement minimal code
**Files**: `src/query/reranker.py`, `src/query/__init__.py`
**Steps**:
1. Create `src/query/reranker.py` with `Reranker` class per §5 pseudocode
2. Import `CrossEncoder` from `sentence_transformers` (with try/except for import)
3. Implement `__init__()` with model loading + fallback (§5b-ii)
4. Implement `rerank()` with full algorithm (§5b): empty check → model check → build pairs → predict → NaN check → assign scores → sort → truncate
5. Export from `src/query/__init__.py`
6. Run: `pytest tests/test_reranker.py -v`
7. **Expected**: All tests PASS

### Task 3: Coverage Gate
1. Run: `pytest --cov=src --cov-branch --cov-report=term-missing tests/`
2. Check: line ≥ 90%, branch ≥ 80%
3. If below: add tests for uncovered lines/branches
4. Record coverage output

### Task 4: Refactor
1. Review `reranker.py` for clarity — ensure logging messages are descriptive
2. Ensure `dataclasses.replace` is used consistently for immutability
3. Run: `pytest tests/ -v` — all tests pass

### Task 5: Mutation Gate
1. Run: `mutmut run --paths-to-mutate=src/query/reranker.py`
2. Run: `mutmut results`
3. Check: mutation score ≥ 80%
4. If below: strengthen assertions in test cases
5. Record mutation output

### Task 6: Create example
1. Create `examples/15-neural-reranking.py`
2. Demonstrate: creating mock candidates, running reranker, showing re-scored results, fallback behavior
3. Run example to verify

---

## Verification Checklist

- [x] All verification_steps traced to Interface Contract postconditions (VS-1→rerank postcondition, VS-2→rerank postcondition, VS-3→fallback behavior)
- [x] All verification_steps traced to Test Inventory rows (VS-1→T1/T2, VS-2→T3/T4, VS-3→T6/T7)
- [x] Algorithm pseudocode covers all non-trivial methods (`rerank`, `__init__`)
- [x] Boundary table covers all algorithm parameters (candidates, top_k, query, scores)
- [x] Error handling table covers all Raises entries (load failure, inference failure, empty input, NaN)
- [x] Test Inventory negative ratio ≥ 40% (45%)
- [x] Every skipped section has explicit "N/A — [reason]" (§2, §4, §6)
