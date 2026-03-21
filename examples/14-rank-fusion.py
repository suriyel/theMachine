#!/usr/bin/env python3
"""Example: Reciprocal Rank Fusion (RRF) — Feature #10.

Demonstrates merging BM25 and vector search results using RRF,
showing how overlapping candidates receive boosted scores.
"""

from src.query.rank_fusion import RankFusion
from src.query.scored_chunk import ScoredChunk


def make_chunk(chunk_id: str, content: str, score: float = 0.0) -> ScoredChunk:
    """Create a ScoredChunk for demonstration."""
    return ScoredChunk(
        chunk_id=chunk_id,
        content_type="code",
        repo_id="example-repo",
        file_path="src/example.py",
        content=content,
        score=score,
    )


def main() -> None:
    rrf = RankFusion(k=60)

    # Simulate BM25 results (keyword search)
    bm25_results = [
        make_chunk("chunk-auth", "class AuthService: ..."),
        make_chunk("chunk-user", "class UserService: ..."),
        make_chunk("chunk-token", "def validate_token(): ..."),
    ]

    # Simulate vector results (semantic search)
    # chunk-auth appears in both → will get boosted score
    vector_results = [
        make_chunk("chunk-auth", "class AuthService: ..."),
        make_chunk("chunk-session", "class SessionManager: ..."),
        make_chunk("chunk-middleware", "class AuthMiddleware: ..."),
    ]

    fused = rrf.fuse(bm25_results, vector_results, top_k=5)

    print("=== RRF Fusion Results ===\n")
    for i, chunk in enumerate(fused, 1):
        overlap = "(overlap — boosted)" if chunk.chunk_id == "chunk-auth" else ""
        print(f"  {i}. {chunk.chunk_id:20s}  score={chunk.score:.6f}  {overlap}")

    print(f"\n  Total candidates: {len(fused)}")
    print(f"  Overlapping 'chunk-auth' score: {fused[0].score:.6f}")
    print(f"  Expected: 1/(60+1) + 1/(60+1) = {2.0/61:.6f}")

    # 4-way fusion example
    print("\n=== 4-Way Fusion (code + doc) ===\n")
    bm25_code = [make_chunk("code-1", "func1", 0.9), make_chunk("code-2", "func2", 0.8)]
    vec_code = [make_chunk("code-1", "func1", 0.85)]
    bm25_doc = [
        ScoredChunk(
            chunk_id="doc-1", content_type="doc", repo_id="r",
            file_path="README.md", content="# Setup", score=0.7,
        )
    ]
    vec_doc = [
        ScoredChunk(
            chunk_id="doc-1", content_type="doc", repo_id="r",
            file_path="README.md", content="# Setup", score=0.6,
        )
    ]

    fused_4way = rrf.fuse(bm25_code, vec_code, bm25_doc, vec_doc, top_k=5)
    for i, chunk in enumerate(fused_4way, 1):
        print(f"  {i}. [{chunk.content_type:4s}] {chunk.chunk_id:10s}  score={chunk.score:.6f}")


if __name__ == "__main__":
    main()
