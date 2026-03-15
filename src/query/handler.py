"""Query Handler module - orchestrates the full retrieval pipeline.

This module provides the QueryHandler class which:
1. Validates query input
2. Executes keyword and semantic retrieval in parallel
3. Fuses results using Reciprocal Rank Fusion
4. Applies neural reranking (if >= 2 candidates)
5. Builds final response with top-k results
"""

import asyncio
import time
from typing import Any, Optional

from src.query.retriever import Candidate
from src.query.models import QueryRequest, QueryResponse


class QueryHandler:
    """Orchestrates the full query retrieval pipeline.

    Takes a QueryRequest and returns a QueryResponse with context results.
    The pipeline consists of:
    1. Input validation
    2. Parallel keyword + semantic retrieval
    3. Rank fusion (RRF)
    4. Neural reranking (if >= 2 candidates)
    5. Response building
    """

    def __init__(
        self,
        keyword_retriever: Any,
        semantic_retriever: Any,
        rank_fusion: Any,
        reranker: Any,
        response_builder: Any,
        semantic_threshold: float = 0.6,
        rrf_k: int = 60,
    ):
        """Initialize QueryHandler with dependencies.

        Args:
            keyword_retriever: KeywordRetriever instance for BM25 search
            semantic_retriever: SemanticRetriever instance for vector search
            rank_fusion: RankFusion instance for result merging
            reranker: NeuralReranker instance for reranking
            response_builder: ContextResponseBuilder instance for response formatting
            semantic_threshold: Minimum similarity threshold for semantic results
            rrf_k: RRF k parameter for rank fusion
        """
        self._keyword_retriever = keyword_retriever
        self._semantic_retriever = semantic_retriever
        self._rank_fusion = rank_fusion
        self._reranker = reranker
        self._response_builder = response_builder
        self._semantic_threshold = semantic_threshold
        self._rrf_k = rrf_k

    def _validate_query(self, query: str) -> None:
        """Validate that query is not empty or whitespace-only.

        Args:
            query: The query string to validate

        Raises:
            ValueError: If query is empty or whitespace-only
        """
        if not query or not query.strip():
            raise ValueError("query must not be empty")

    def _build_filters(self, request: QueryRequest) -> dict:
        """Build filters dict from request.

        Args:
            request: The query request

        Returns:
            Dictionary with optional repo_filter and language_filter
        """
        filters = {}
        if request.repo:
            filters["repo_filter"] = request.repo
        if request.language:
            filters["language_filter"] = request.language
        return filters

    async def handle(self, request: QueryRequest) -> QueryResponse:
        """Handle a query request and return context results.

        Args:
            request: QueryRequest with query text and optional filters

        Returns:
            QueryResponse with results and timing

        Raises:
            ValueError: If query is empty or whitespace-only
        """
        # Validate query input
        self._validate_query(request.query)

        # Start timing
        start_time = time.perf_counter()

        # Build filters from request
        filters = self._build_filters(request)

        # Execute keyword and semantic retrieval in parallel
        keyword_task = self._keyword_retriever.retrieve(request.query, filters)
        semantic_task = self._semantic_retriever.retrieve(request.query, filters)

        keyword_results, semantic_results = await asyncio.gather(
            keyword_task, semantic_task
        )

        # Apply rank fusion
        fused_results = self._rank_fusion.fuse(keyword_results, semantic_results)

        # Apply neural reranking if >= 2 candidates
        if len(fused_results) >= 2:
            reranked_results = self._reranker.rerank(request.query, fused_results)
        else:
            reranked_results = fused_results

        # Build final response
        # Update response builder's top_k based on request
        original_top_k = self._response_builder._top_k
        if hasattr(self._response_builder, '_top_k'):
            # Update top_k for this request
            self._response_builder._top_k = request.top_k

        results = self._response_builder.build(reranked_results)

        # Restore original top_k
        if hasattr(self._response_builder, '_top_k'):
            self._response_builder._top_k = original_top_k

        # Calculate query time
        query_time_ms = (time.perf_counter() - start_time) * 1000

        return QueryResponse(
            results=results,
            query_time_ms=query_time_ms,
        )
