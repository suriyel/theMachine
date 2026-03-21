"""Example: Context Response Builder (Feature #12).

Demonstrates building a dual-list query response from reranked ScoredChunks,
including content truncation and optional repository rules.
"""

from src.query.response_builder import ResponseBuilder
from src.query.scored_chunk import ScoredChunk


def main() -> None:
    builder = ResponseBuilder(max_content_length=2000)

    # Simulate reranked results: 2 code chunks + 1 doc chunk
    chunks = [
        ScoredChunk(
            chunk_id="chunk-001",
            content_type="code",
            repo_id="my-org/my-app",
            file_path="src/auth/jwt.py",
            content="def validate_token(token: str, secret: str) -> Claims:\n"
            "    payload = jwt.decode(token, secret, algorithms=['HS256'])\n"
            "    return Claims.from_dict(payload)",
            score=0.95,
            language="python",
            chunk_type="function",
            symbol="validate_token",
            signature="def validate_token(token: str, secret: str) -> Claims",
            doc_comment="Validate JWT and return decoded claims.",
            line_start=45,
            line_end=48,
        ),
        ScoredChunk(
            chunk_id="chunk-002",
            content_type="code",
            repo_id="my-org/my-app",
            file_path="src/auth/middleware.py",
            content="class AuthMiddleware:\n    async def __call__(self, request, call_next):\n"
            "        token = request.headers.get('Authorization')\n"
            "        if not token:\n            raise HTTPException(401)",
            score=0.88,
            language="python",
            chunk_type="class",
            symbol="AuthMiddleware",
            signature="class AuthMiddleware",
            line_start=10,
            line_end=25,
        ),
        ScoredChunk(
            chunk_id="chunk-003",
            content_type="doc",
            repo_id="my-org/my-app",
            file_path="docs/auth.md",
            content="JWT tokens are validated on every API request. "
            "The token must include `user_id` and `roles` claims.",
            score=0.82,
            breadcrumb="docs/auth.md > Authentication > JWT Validation",
        ),
    ]

    # Optional: repository rules
    rules = [
        ScoredChunk(
            chunk_id="rule-001",
            content_type="rule",
            repo_id="my-org/my-app",
            file_path=".claude/rules",
            content="Always use async database sessions",
            score=0.0,
            chunk_type="agent_rules",
        ),
        ScoredChunk(
            chunk_id="rule-002",
            content_type="rule",
            repo_id="my-org/my-app",
            file_path="CONTRIBUTING.md",
            content="All PRs must include tests",
            score=0.0,
            chunk_type="contribution_guide",
        ),
    ]

    # Build the response
    response = builder.build(
        chunks=chunks,
        query="how to authenticate users",
        query_type="nl",
        repo="my-org/my-app",
        rules=rules,
    )

    # Display results
    print(f"Query: {response.query}")
    print(f"Query Type: {response.query_type}")
    print(f"Repository: {response.repo}")
    print(f"\n--- Code Results ({len(response.code_results)}) ---")
    for cr in response.code_results:
        print(f"  [{cr.language}] {cr.symbol} ({cr.file_path}:{cr.lines})")
        print(f"    Score: {cr.relevance_score:.2f} | Truncated: {cr.truncated}")
        print(f"    Content: {cr.content[:80]}...")

    print(f"\n--- Doc Results ({len(response.doc_results)}) ---")
    for dr in response.doc_results:
        print(f"  {dr.breadcrumb or dr.file_path}")
        print(f"    Score: {dr.relevance_score:.2f} | Truncated: {dr.truncated}")
        print(f"    Content: {dr.content[:80]}...")

    if response.rules:
        print("\n--- Rules ---")
        print(f"  Agent rules: {response.rules.agent_rules}")
        print(f"  Contribution guide: {response.rules.contribution_guide}")
        print(f"  Linter config: {response.rules.linter_config}")

    # Demonstrate truncation
    print("\n--- Truncation Demo ---")
    long_chunk = ScoredChunk(
        chunk_id="chunk-long",
        content_type="code",
        repo_id="my-org/my-app",
        file_path="src/big_file.py",
        content="x" * 2500,
        score=0.70,
        language="python",
        chunk_type="function",
        symbol="big_function",
    )
    truncated_response = builder.build(
        [long_chunk], query="big function", query_type="symbol"
    )
    tr = truncated_response.code_results[0]
    print(f"  Original length: 2500")
    print(f"  Truncated length: {len(tr.content)} (2000 + '...')")
    print(f"  Truncated flag: {tr.truncated}")
    print(f"  Ends with '...': {tr.content.endswith('...')}")


if __name__ == "__main__":
    main()
