"""Tests for ContextResponseBuilder."""

import pytest

from src.query.retriever import Candidate
from src.query.response_builder import ContextResponseBuilder
from src.query.api.v1.endpoints.query import ContextResult


# [no integration test] — pure function, no external I/O


class TestContextResponseBuilder:
    """Unit tests for ContextResponseBuilder."""

    def test_build_returns_top_3_from_50_candidates(self):
        """Given 50 ranked candidates, when response is built, then exactly 3 results returned."""
        # Create 50 candidates with varying scores
        candidates = [
            Candidate(
                chunk_id=f"chunk_{i}",
                repo_name=f"repo_{i % 5}",
                file_path=f"src/file_{i}.java",
                symbol=f"Symbol{i}" if i % 3 == 0 else None,
                content=f"content {i}",
                score=float(100 - i),  # Higher score for lower index
                language="Java",
            )
            for i in range(50)
        ]

        builder = ContextResponseBuilder(top_k=3)
        results = builder.build(candidates)

        assert len(results) == 3
        # Verify order by score descending
        assert results[0].score >= results[1].score >= results[2].score

    def test_build_returns_empty_list_when_no_candidates(self):
        """Given zero candidates, when response is built, then empty results array returned."""
        builder = ContextResponseBuilder(top_k=3)
        results = builder.build([])

        assert results == []
        assert isinstance(results, list)

    def test_build_orders_results_by_score_descending(self):
        """Given results with varying scores, when response is built, then results ordered by score descending."""
        candidates = [
            Candidate(
                chunk_id="chunk_1",
                repo_name="repo_a",
                file_path="src/File1.java",
                symbol="Symbol1",
                content="content 1",
                score=0.3,
                language="Java",
            ),
            Candidate(
                chunk_id="chunk_2",
                repo_name="repo_b",
                file_path="src/File2.java",
                symbol="Symbol2",
                content="content 2",
                score=0.9,
                language="Java",
            ),
            Candidate(
                chunk_id="chunk_3",
                repo_name="repo_c",
                file_path="src/File3.java",
                symbol="Symbol3",
                content="content 3",
                score=0.6,
                language="Java",
            ),
        ]

        builder = ContextResponseBuilder(top_k=3)
        results = builder.build(candidates)

        assert len(results) == 3
        # Check order by score descending
        assert results[0].score == 0.9
        assert results[1].score == 0.6
        assert results[2].score == 0.3

    def test_build_transforms_candidate_fields_correctly(self):
        """Given candidates with all fields, when response is built, then fields are correctly mapped."""
        candidate = Candidate(
            chunk_id="chunk_1",
            repo_name="spring-framework",
            file_path="src/web/client/RestTemplate.java",
            symbol="RestTemplate",
            content="public class RestTemplate { }",
            score=0.95,
            language="Java",
        )

        builder = ContextResponseBuilder(top_k=3)
        results = builder.build([candidate])

        assert len(results) == 1
        result = results[0]

        assert result.repository == "spring-framework"
        assert result.file_path == "src/web/client/RestTemplate.java"
        assert result.symbol == "RestTemplate"
        assert result.score == 0.95
        assert result.content == "public class RestTemplate { }"

    def test_build_with_less_than_top_k_candidates(self):
        """Given 2 candidates when top_k is 3, when response is built, then 2 results returned."""
        candidates = [
            Candidate(
                chunk_id="chunk_1",
                repo_name="repo_a",
                file_path="src/File1.java",
                symbol="Symbol1",
                content="content 1",
                score=0.8,
                language="Java",
            ),
            Candidate(
                chunk_id="chunk_2",
                repo_name="repo_b",
                file_path="src/File2.java",
                symbol="Symbol2",
                content="content 2",
                score=0.5,
                language="Java",
            ),
        ]

        builder = ContextResponseBuilder(top_k=3)
        results = builder.build(candidates)

        assert len(results) == 2
        assert results[0].score == 0.8
        assert results[1].score == 0.5

    def test_build_handles_none_symbol(self):
        """Given candidate without symbol, when response is built, then symbol is None."""
        candidate = Candidate(
            chunk_id="chunk_1",
            repo_name="repo_a",
            file_path="src/File1.java",
            symbol=None,
            content="content",
            score=0.7,
            language="Java",
        )

        builder = ContextResponseBuilder(top_k=3)
        results = builder.build([candidate])

        assert len(results) == 1
        assert results[0].symbol is None

    def test_build_with_custom_top_k(self):
        """Given custom top_k=5, when response is built, then exactly 5 results returned."""
        candidates = [
            Candidate(
                chunk_id=f"chunk_{i}",
                repo_name=f"repo_{i}",
                file_path=f"src/file_{i}.java",
                symbol=f"Symbol{i}",
                content=f"content {i}",
                score=float(10 - i),
                language="Java",
            )
            for i in range(20)
        ]

        builder = ContextResponseBuilder(top_k=5)
        results = builder.build(candidates)

        assert len(results) == 5

    def test_build_stability_with_same_scores(self):
        """Given candidates with same score, when response is built, then results are stable (deterministic ordering)."""
        candidates = [
            Candidate(
                chunk_id="chunk_c",
                repo_name="repo",
                file_path="src/FileC.java",
                symbol="SymbolC",
                content="content c",
                score=0.5,
                language="Java",
            ),
            Candidate(
                chunk_id="chunk_a",
                repo_name="repo",
                file_path="src/FileA.java",
                symbol="SymbolA",
                content="content a",
                score=0.5,
                language="Java",
            ),
            Candidate(
                chunk_id="chunk_b",
                repo_name="repo",
                file_path="src/FileB.java",
                symbol="SymbolB",
                content="content b",
                score=0.5,
                language="Java",
            ),
        ]

        builder = ContextResponseBuilder(top_k=3)
        results = builder.build(candidates)

        # All results should have the same score (0.5)
        assert all(r.score == 0.5 for r in results)
        # Should be deterministic (same input = same output)
        results2 = builder.build(candidates)
        assert [r.file_path for r in results] == [r.file_path for r in results2]
