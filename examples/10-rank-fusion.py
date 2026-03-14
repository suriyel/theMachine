"""Example: Rank Fusion (Feature #10)

Demonstrates Reciprocal Rank Fusion (RRF) for merging keyword and semantic search results.

This example shows how to use the RankFusion class to combine
results from keyword (BM25) and semantic (vector) retrieval.
"""
from src.query.rank_fusion import RankFusion
from src.query.retriever import Candidate


def main():
    """Run rank fusion examples."""

    # Create RankFusion instance with default k=60
    fusion = RankFusion(k=60)

    # Example 1: Overlapping results
    # Keyword returns [A, B, C], Semantic returns [B, D, E]
    # B appears in both lists and should rank higher
    print("=== Example 1: Overlapping Results ===")
    keyword_results = [
        Candidate(chunk_id="A", repo_name="repo", file_path="a.py", symbol=None, content="Content A", score=0.9),
        Candidate(chunk_id="B", repo_name="repo", file_path="b.py", symbol=None, content="Content B", score=0.8),
        Candidate(chunk_id="C", repo_name="repo", file_path="c.py", symbol=None, content="Content C", score=0.7),
    ]
    semantic_results = [
        Candidate(chunk_id="B", repo_name="repo", file_path="b.py", symbol=None, content="Content B", score=0.95),
        Candidate(chunk_id="D", repo_name="repo", file_path="d.py", symbol=None, content="Content D", score=0.85),
        Candidate(chunk_id="E", repo_name="repo", file_path="e.py", symbol=None, content="Content E", score=0.75),
    ]

    fused = fusion.fuse(keyword_results, semantic_results)
    print(f"Keyword: [A, B, C]")
    print(f"Semantic: [B, D, E]")
    print(f"Fused: {[c.chunk_id for c in fused]}")
    print(f"B benefits from appearing in both lists!\n")

    # Example 2: Empty keyword results
    print("=== Example 2: Empty Keyword Results ===")
    keyword_empty = []
    semantic_only = [
        Candidate(chunk_id="X", repo_name="repo", file_path="x.py", symbol=None, content="Content X", score=0.9),
        Candidate(chunk_id="Y", repo_name="repo", file_path="y.py", symbol=None, content="Content Y", score=0.8),
    ]

    fused = fusion.fuse(keyword_empty, semantic_only)
    print(f"Keyword: []")
    print(f"Semantic: [X, Y]")
    print(f"Fused: {[c.chunk_id for c in fused]}")
    print(f"Returns semantic results unchanged!\n")

    # Example 3: Empty semantic results
    print("=== Example 3: Empty Semantic Results ===")
    keyword_only = [
        Candidate(chunk_id="P", repo_name="repo", file_path="p.py", symbol=None, content="Content P", score=0.9),
        Candidate(chunk_id="Q", repo_name="repo", file_path="q.py", symbol=None, content="Content Q", score=0.8),
    ]
    semantic_empty = []

    fused = fusion.fuse(keyword_only, semantic_empty)
    print(f"Keyword: [P, Q]")
    print(f"Semantic: []")
    print(f"Fused: {[c.chunk_id for c in fused]}")
    print(f"Returns keyword results unchanged!\n")

    # Example 4: Both empty
    print("=== Example 4: Both Empty ===")
    fused = fusion.fuse([], [])
    print(f"Keyword: []")
    print(f"Semantic: []")
    print(f"Fused: {fused}")
    print(f"Returns empty list!\n")

    # Example 5: Different k values
    print("=== Example 5: Different k Values ===")
    k60_fusion = RankFusion(k=60)
    k10_fusion = RankFusion(k=10)

    kw = [Candidate(chunk_id="A", repo_name="repo", file_path="a.py", symbol=None, content="A", score=0.9)]
    sem = [Candidate(chunk_id="B", repo_name="repo", file_path="b.py", symbol=None, content="B", score=0.9)]

    r60 = k60_fusion.fuse(kw, sem)
    r10 = k10_fusion.fuse(kw, sem)
    print(f"k=60: {r60[0].chunk_id}, k=10: {r10[0].chunk_id}")
    print(f"Smaller k makes rank differences more significant\n")

    print("Done!")


if __name__ == "__main__":
    main()
