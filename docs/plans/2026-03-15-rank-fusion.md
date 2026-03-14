# Implementation Plan — Rank Fusion (FR-010)

**Feature ID**: 10
**Feature Title**: Rank Fusion (FR-010)
**Date**: 2026-03-15
**Status**: Planned

## 1. Overview

Implement the Rank Fusion component that merges keyword and semantic retrieval results using Reciprocal Rank Fusion (RRF) with k=60.

## 2. Requirements Summary

From SRS FR-010:
- Merge keyword and semantic results using Reciprocal Rank Fusion (RRF) with k=60
- Given keyword results [A, B, C] and semantic results [B, D, E], when fusion executes, then merged list contains all 5 unique chunks (A, B, C, D, E) with B benefiting from dual appearance
- Given one retrieval method returns empty, fusion returns results from the non-empty method
- Given both empty, fusion returns empty list

## 3. Design

From Design Section 4.2:
- **Class**: `RankFusion`
- **Algorithm**: Reciprocal Rank Fusion (RRF)
- **Parameter**: `k: int = 60`
- **Method**: `fuse(keyword_results: list[Candidate], semantic_results: list[Candidate]) -> list[Candidate]`

### RRF Formula
```
score(doc) = sum(1.0 / (k + rank(doc_in_list))) for each list where doc appears
```

### Class Diagram
```python
class RankFusion:
    def __init__(self, k: int = 60):
        self.k = k

    def fuse(self, keyword_results: list[Candidate], semantic_results: list[Candidate]) -> list[Candidate]:
        """Merge keyword and semantic results using RRF."""
```

## 4. Implementation Tasks

### 4.1 Create RankFusion Class
- Create `src/query/rank_fusion.py`
- Implement `RankFusion` class with `k` parameter
- Implement `fuse()` method using RRF algorithm
- Handle edge cases: empty lists, duplicate chunk_ids

### 4.2 Create Candidate Dataclass
- Reuse existing `Candidate` dataclass from `src/query/models.py` (already exists from KeywordRetriever/SemanticRetriever)

### 4.3 Unit Tests
- Test RRF with overlapping results (keyword [A,B,C], semantic [B,D,E])
- Test RRF with empty keyword results
- Test RRF with empty semantic results
- Test RRF with both empty
- Test RRF with all unique results
- Test that duplicate chunk_ids are handled (deduplicated by chunk_id)

## 5. File List

| File | Action |
|------|--------|
| `src/query/rank_fusion.py` | Create |
| `tests/test_rank_fusion.py` | Create |

## 6. Dependencies

- Feature #8 (Keyword Retrieval) — provides Candidate class and keyword results format
- Feature #9 (Semantic Retrieval) — provides semantic results format

## 7. Verification Steps

From `feature-list.json`:
1. Given keyword results [A, B, C] and semantic results [B, D, E], when fusion executes, then merged list contains all 5 unique chunks (A, B, C, D, E) with B benefiting from dual appearance
2. Given keyword results empty and semantic results [A, B], when fusion executes, then fused list contains [A, B]
3. Given both retrieval methods return empty, when fusion executes, then empty list is returned
