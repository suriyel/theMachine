#!/usr/bin/env python3
"""Example: Neural Reranking (Feature #11)

This example demonstrates how to use the NeuralReranker to reorder candidate
results using cross-encoder neural reranking.

Usage:
    python examples/11-neural-reranking.py
"""
from src.query.reranker import NeuralReranker
from src.query.retriever import Candidate


def main():
    # Create sample candidates from keyword/semantic search
    candidates = [
        Candidate(
            chunk_id="chunk-001",
            repo_name="spring-framework",
            file_path="WebClientConfig.java",
            symbol="WebClient.Builder",
            content="public WebClient.Builder responseTimeout(Duration timeout) {...}",
            score=0.5,
            language="java"
        ),
        Candidate(
            chunk_id="chunk-002",
            repo_name="spring-framework",
            file_path="RestTemplateConfig.java",
            symbol="RestTemplate",
            content="public void setConnectTimeout(int timeout) {...}",
            score=0.6,
            language="java"
        ),
        Candidate(
            chunk_id="chunk-003",
            repo_name="spring-framework",
            file_path="HttpClientBuilder.java",
            symbol="RequestConfig",
            content="public RequestConfig.Builder setTimeout(int timeout) {...}",
            score=0.4,
            language="java"
        ),
    ]

    query = "how to configure spring http client timeout"

    # Initialize reranker (loads bge-reranker-v2-m3 model)
    print("Initializing NeuralReranker...")
    reranker = NeuralReranker(model_name="BAAI/bge-reranker-v2-m3")

    # Rerank candidates using neural relevance scoring
    print(f"Query: {query}")
    print(f"Input candidates: {len(candidates)}")
    print("-" * 50)

    reranked = reranker.rerank(query, candidates)

    # Display results
    print("Reranked results:")
    for i, candidate in enumerate(reranked, 1):
        print(f"\n{i}. {candidate.symbol}")
        print(f"   File: {candidate.file_path}")
        print(f"   Score: {candidate.score:.4f}")
        print(f"   Content: {candidate.content[:60]}...")

    # Demonstrate pass-through behavior
    print("\n" + "=" * 50)
    print("Pass-through behavior (< 2 candidates):")

    single_candidate = [candidates[0]]
    reranked_single = reranker.rerank(query, single_candidate)
    print(f"Input: 1 candidate -> Output: {len(reranked_single)} candidate(s)")

    # Demonstrate empty list handling
    print("\nEmpty list handling:")
    empty_result = reranker.rerank(query, [])
    print(f"Input: [] -> Output: {empty_result}")


if __name__ == "__main__":
    main()
