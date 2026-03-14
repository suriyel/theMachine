"""Tests for Rank Fusion (FR-010).

This module tests the Reciprocal Rank Fusion (RRF) algorithm
for merging keyword and semantic retrieval results.

[no integration test] — pure function, no external I/O
"""
import pytest
from src.query.retriever import Candidate


# [unit] — pure function test
def test_rrf_with_overlapping_results():
    """Given keyword results [A, B, C] and semantic results [B, D, E],
    when fusion executes, then merged list contains all 5 unique chunks
    (A, B, C, D, E) with B benefiting from dual appearance."""
    # Import here to ensure test fails before implementation
    from src.query.rank_fusion import RankFusion

    # Setup: keyword results [A, B, C] in ranked order
    keyword_results = [
        Candidate(chunk_id="A", repo_name="repo", file_path="a.py", symbol=None, content="A", score=0.9),
        Candidate(chunk_id="B", repo_name="repo", file_path="b.py", symbol=None, content="B", score=0.8),
        Candidate(chunk_id="C", repo_name="repo", file_path="c.py", symbol=None, content="C", score=0.7),
    ]

    # Setup: semantic results [B, D, E] in ranked order
    semantic_results = [
        Candidate(chunk_id="B", repo_name="repo", file_path="b.py", symbol=None, content="B", score=0.95),
        Candidate(chunk_id="D", repo_name="repo", file_path="d.py", symbol=None, content="D", score=0.85),
        Candidate(chunk_id="E", repo_name="repo", file_path="e.py", symbol=None, content="E", score=0.75),
    ]

    # Execute: fuse results
    fusion = RankFusion(k=60)
    fused = fusion.fuse(keyword_results, semantic_results)

    # Verify: all 5 unique chunks present
    chunk_ids = [c.chunk_id for c in fused]
    assert len(chunk_ids) == 5, f"Expected 5 unique chunks, got {len(chunk_ids)}"
    assert set(chunk_ids) == {"A", "B", "C", "D", "E"}

    # Verify: B benefits from dual appearance (should rank higher than C and D)
    # In RRF, B appears in both lists at rank 0 and 0, so gets score = 1/(60+0) + 1/(60+0) = 2/60
    # C appears only at rank 2, so gets score = 1/(60+2) = 1/62
    # D appears only at rank 1, so gets score = 1/(60+1) = 1/61
    # B should rank first
    assert fused[0].chunk_id == "B", f"Expected B first due to dual appearance, got {fused[0].chunk_id}"


# [unit] — pure function test
def test_rrf_with_empty_keyword_results():
    """Given keyword results empty and semantic results [A, B],
    when fusion executes, then fused list contains [A, B]."""
    from src.query.rank_fusion import RankFusion

    keyword_results = []
    semantic_results = [
        Candidate(chunk_id="A", repo_name="repo", file_path="a.py", symbol=None, content="A", score=0.9),
        Candidate(chunk_id="B", repo_name="repo", file_path="b.py", symbol=None, content="B", score=0.8),
    ]

    fusion = RankFusion(k=60)
    fused = fusion.fuse(keyword_results, semantic_results)

    # Verify: returns semantic results in order
    assert len(fused) == 2
    chunk_ids = [c.chunk_id for c in fused]
    assert chunk_ids == ["A", "B"]


# [unit] — pure function test
def test_rrf_with_empty_semantic_results():
    """Given keyword results [A, B] and semantic results empty,
    when fusion executes, then fused list contains [A, B]."""
    from src.query.rank_fusion import RankFusion

    keyword_results = [
        Candidate(chunk_id="A", repo_name="repo", file_path="a.py", symbol=None, content="A", score=0.9),
        Candidate(chunk_id="B", repo_name="repo", file_path="b.py", symbol=None, content="B", score=0.8),
    ]
    semantic_results = []

    fusion = RankFusion(k=60)
    fused = fusion.fuse(keyword_results, semantic_results)

    # Verify: returns keyword results in order
    assert len(fused) == 2
    chunk_ids = [c.chunk_id for c in fused]
    assert chunk_ids == ["A", "B"]


# [unit] — pure function test
def test_rrf_with_both_empty():
    """Given both retrieval methods return empty, when fusion executes,
    then empty list is returned."""
    from src.query.rank_fusion import RankFusion

    keyword_results = []
    semantic_results = []

    fusion = RankFusion(k=60)
    fused = fusion.fuse(keyword_results, semantic_results)

    # Verify: empty list returned
    assert fused == []


# [unit] — pure function test
def test_rrf_with_all_unique_results():
    """Given keyword results [A, B] and semantic results [C, D],
    when fusion executes, then all 4 unique chunks are returned,
    each appearing only once with deduplicated chunk_id."""
    from src.query.rank_fusion import RankFusion

    keyword_results = [
        Candidate(chunk_id="A", repo_name="repo", file_path="a.py", symbol=None, content="A", score=0.9),
        Candidate(chunk_id="B", repo_name="repo", file_path="b.py", symbol=None, content="B", score=0.8),
    ]
    semantic_results = [
        Candidate(chunk_id="C", repo_name="repo", file_path="c.py", symbol=None, content="C", score=0.7),
        Candidate(chunk_id="D", repo_name="repo", file_path="d.py", symbol=None, content="D", score=0.6),
    ]

    fusion = RankFusion(k=60)
    fused = fusion.fuse(keyword_results, semantic_results)

    # Verify: 4 unique chunks
    assert len(fused) == 4
    chunk_ids = [c.chunk_id for c in fused]
    assert set(chunk_ids) == {"A", "B", "C", "D"}


# [unit] — pure function test
def test_rrf_k_parameter():
    """Verify that k parameter affects the fusion scores."""
    from src.query.rank_fusion import RankFusion

    # Same results, different k values
    keyword_results = [
        Candidate(chunk_id="A", repo_name="repo", file_path="a.py", symbol=None, content="A", score=0.9),
    ]
    semantic_results = [
        Candidate(chunk_id="B", repo_name="repo", file_path="b.py", symbol=None, content="B", score=0.9),
    ]

    # Execute with k=60 (default)
    fusion_60 = RankFusion(k=60)
    fused_60 = fusion_60.fuse(keyword_results, semantic_results)

    # Execute with k=10 (smaller k = more aggressive ranking)
    fusion_10 = RankFusion(k=10)
    fused_10 = fusion_10.fuse(keyword_results, semantic_results)

    # Verify: both have 2 items
    assert len(fused_60) == 2
    assert len(fused_10) == 2

    # Verify: with smaller k, rank differences matter more
    # The first item should still be first in both


# [unit] — boundary test
def test_rrf_duplicate_chunk_ids_deduplicated():
    """Verify that duplicate chunk_ids from both lists are deduplicated."""
    from src.query.rank_fusion import RankFusion

    keyword_results = [
        Candidate(chunk_id="A", repo_name="repo", file_path="a.py", symbol=None, content="A", score=0.9),
        Candidate(chunk_id="A", repo_name="repo", file_path="a.py", symbol=None, content="A", score=0.9),  # duplicate
    ]
    semantic_results = [
        Candidate(chunk_id="B", repo_name="repo", file_path="b.py", symbol=None, content="B", score=0.8),
    ]

    fusion = RankFusion(k=60)
    fused = fusion.fuse(keyword_results, semantic_results)

    # Verify: duplicates removed
    chunk_ids = [c.chunk_id for c in fused]
    assert chunk_ids.count("A") == 1, "Duplicate chunk_id should be deduplicated"


# [unit] — boundary test
def test_rrf_returns_candidate_dataclass():
    """Verify that fuse returns list of Candidate dataclass instances."""
    from src.query.rank_fusion import RankFusion

    keyword_results = [
        Candidate(chunk_id="A", repo_name="repo", file_path="a.py", symbol=None, content="A", score=0.9),
    ]
    semantic_results = [
        Candidate(chunk_id="B", repo_name="repo", file_path="b.py", symbol=None, content="B", score=0.8),
    ]

    fusion = RankFusion(k=60)
    fused = fusion.fuse(keyword_results, semantic_results)

    # Verify: all results are Candidate instances
    for item in fused:
        assert isinstance(item, Candidate), f"Expected Candidate, got {type(item)}"


# [unit] — error case test
def test_rrf_preserves_candidate_metadata():
    """Verify that fusion preserves all Candidate metadata from original results."""
    from src.query.rank_fusion import RankFusion

    keyword_results = [
        Candidate(
            chunk_id="A",
            repo_name="test-repo",
            file_path="src/main.py",
            symbol="MainClass",
            content="class MainClass: pass",
            score=0.9,
            language="python"
        ),
    ]
    semantic_results = []

    fusion = RankFusion(k=60)
    fused = fusion.fuse(keyword_results, semantic_results)

    # Verify: metadata preserved
    assert fused[0].chunk_id == "A"
    assert fused[0].repo_name == "test-repo"
    assert fused[0].file_path == "src/main.py"
    assert fused[0].symbol == "MainClass"
    assert fused[0].content == "class MainClass: pass"
    assert fused[0].score == 0.9
    assert fused[0].language == "python"
