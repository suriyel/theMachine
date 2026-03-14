#!/usr/bin/env python
"""Example: Context Response Builder (FR-012)

This example demonstrates how to use the ContextResponseBuilder to transform
ranked search candidates into API response format.

Run: python examples/12-context-response-builder.py
"""

from src.query.response_builder import ContextResponseBuilder
from src.query.retriever import Candidate


def main():
    """Demonstrate ContextResponseBuilder usage."""

    # Create sample candidates (as if returned from keyword+semantic retrieval + rank fusion + reranking)
    candidates = [
        Candidate(
            chunk_id="chunk_001",
            repo_name="spring-framework",
            file_path="src/web/client/RestTemplate.java",
            symbol="RestTemplate",
            content="public class RestTemplate {\n    private HttpClient client;\n}",
            score=0.95,
            language="Java",
        ),
        Candidate(
            chunk_id="chunk_002",
            repo_name="spring-framework",
            file_path="src/web/client/WebClient.java",
            symbol="WebClient",
            content="public class WebClient {\n    private Builder builder;\n}",
            score=0.87,
            language="Java",
        ),
        Candidate(
            chunk_id="chunk_003",
            repo_name="spring-framework",
            file_path="src/http/client/HttpClient.java",
            symbol="HttpClient",
            content="public class HttpClient {\n    private RequestConfig config;\n}",
            score=0.72,
            language="Java",
        ),
        Candidate(
            chunk_id="chunk_004",
            repo_name="spring-framework",
            file_path="src/util/TimeoutUtil.java",
            symbol="TimeoutUtil",
            content="public class TimeoutUtil {\n    public static void setTimeout(int ms) {}\n}",
            score=0.45,
            language="Java",
        ),
        Candidate(
            chunk_id="chunk_005",
            repo_name="spring-framework",
            file_path="src/util/DateUtil.java",
            symbol="DateUtil",
            content="public class DateUtil {\n    public static Date now() { return new Date(); }\n}",
            score=0.23,
            language="Java",
        ),
    ]

    # Create builder with default top_k=3
    builder = ContextResponseBuilder(top_k=3)

    # Build response
    results = builder.build(candidates)

    # Display results
    print("Context Response Builder Example")
    print("=" * 50)
    print(f"Input: {len(candidates)} candidates")
    print(f"Output: {len(results)} results (top_k=3)")
    print()

    for i, result in enumerate(results, 1):
        print(f"Result #{i}:")
        print(f"  Repository: {result.repository}")
        print(f"  File:       {result.file_path}")
        print(f"  Symbol:     {result.symbol}")
        print(f"  Score:      {result.score:.2f}")
        print(f"  Content:    {result.content[:50]}...")
        print()

    # Demonstrate with empty list
    print("-" * 50)
    print("Empty list handling:")
    empty_results = builder.build([])
    print(f"  Input: 0 candidates -> Output: {len(empty_results)} results")

    # Demonstrate with custom top_k
    print("-" * 50)
    print("Custom top_k=5:")
    builder_top5 = ContextResponseBuilder(top_k=5)
    top5_results = builder_top5.build(candidates)
    print(f"  Input: {len(candidates)} candidates -> Output: {len(top5_results)} results")

    print("\n✓ Example completed successfully!")


if __name__ == "__main__":
    main()
