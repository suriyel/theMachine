"""QueryHandler — orchestrates the hybrid retrieval pipeline for NL and symbol queries."""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import replace

from src.query.exceptions import RetrievalError
from src.query.response_models import QueryResponse
from src.query.scored_chunk import ScoredChunk
from src.shared.exceptions import ValidationError

log = logging.getLogger(__name__)

# Compiled regex for identifier extraction (camelCase, PascalCase, snake_case, dot.sep)
_IDENTIFIER_RE = re.compile(
    r"\b([a-zA-Z]\w*(?:\.[a-zA-Z]\w*)+)\b"           # dot-separated (must be first — longest match)
    r"|\b([A-Z][a-z]+(?:[A-Z][a-z0-9]+)+)\b"          # PascalCase
    r"|\b([a-z]+[A-Z][a-zA-Z0-9]*)\b"                 # camelCase
    r"|\b([a-z][a-z0-9]*(?:_[a-z][a-z0-9]*)+)\b"      # snake_case
)


class QueryHandler:
    """Orchestrates the full hybrid retrieval pipeline."""

    def __init__(
        self,
        retriever,
        rank_fusion,
        reranker,
        response_builder,
        search_timeout: float = 0.2,
        pipeline_timeout: float = 1.0,
    ) -> None:
        self._retriever = retriever
        self._rank_fusion = rank_fusion
        self._reranker = reranker
        self._response_builder = response_builder
        self._search_timeout = search_timeout
        self._pipeline_timeout = pipeline_timeout

    async def handle_nl_query(
        self,
        query: str,
        repo: str,
        languages: list[str] | None = None,
    ) -> QueryResponse:
        """Execute the full NL retrieval pipeline.

        Raises:
            ValidationError: If query is empty or exceeds 500 chars.
            RetrievalError: If all 4 primary retrieval paths fail.
        """
        # Step 1: Validate
        if not query or not query.strip():
            raise ValidationError("query must not be empty")
        if len(query) > 500:
            raise ValidationError("query exceeds 500 character limit")

        # Step 2: Extract identifiers for symbol boost
        identifiers = self._extract_identifiers(query)

        # Wrap entire pipeline in pipeline_timeout
        try:
            response = await asyncio.wait_for(
                self._run_pipeline(query, repo, languages, identifiers),
                timeout=self._pipeline_timeout,
            )
        except asyncio.TimeoutError:
            log.warning("Pipeline exceeded %ss timeout, returning degraded empty response", self._pipeline_timeout)
            response = self._response_builder.build([], query, "nl", repo)
            response.degraded = True

        return response

    async def _run_pipeline(
        self,
        query: str,
        repo: str,
        languages: list[str] | None,
        identifiers: list[str],
    ) -> QueryResponse:
        """Execute the retrieval pipeline (gather, fuse, rerank, build)."""
        # Step 3: Build retrieval tasks with individual timeouts
        tasks = [
            asyncio.wait_for(
                self._retriever.bm25_code_search(query, repo, languages=languages, top_k=200),
                timeout=self._search_timeout,
            ),
            asyncio.wait_for(
                self._retriever.vector_code_search(query, repo, languages=languages, top_k=200),
                timeout=self._search_timeout,
            ),
            asyncio.wait_for(
                self._retriever.bm25_doc_search(query, repo, top_k=100),
                timeout=self._search_timeout,
            ),
            asyncio.wait_for(
                self._retriever.vector_doc_search(query, repo, top_k=100),
                timeout=self._search_timeout,
            ),
        ]

        if identifiers:
            tasks.append(
                asyncio.wait_for(
                    self._symbol_boost_search(identifiers, repo),
                    timeout=self._search_timeout,
                )
            )

        # Step 4: Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Step 5: Separate successes from failures for 4 primary searches
        primary_results = results[:4]
        successful_lists: list[list[ScoredChunk]] = []
        degraded = False

        for i, result in enumerate(primary_results):
            if isinstance(result, BaseException):
                log.warning("Retrieval path %d failed: %s", i, result)
                degraded = True
            else:
                successful_lists.append(result)

        # Step 6: Check at least one primary succeeded
        if not successful_lists:
            raise RetrievalError("all retrieval paths failed")

        # Step 7: Handle symbol boost (5th element)
        if identifiers and len(results) > 4 and not isinstance(results[4], BaseException):
            boosted = self._apply_boost_weight(results[4], weight=0.3)
            successful_lists.append(boosted)

        # Step 8: Fuse
        fused = self._rank_fusion.fuse(*successful_lists, top_k=50)

        # Step 9: Rerank
        reranked = self._reranker.rerank(query, fused, top_k=6)

        # Step 10: Build response
        response = self._response_builder.build(reranked, query, "nl", repo)

        # Step 11: Mark degraded
        if degraded:
            response.degraded = True

        return response

    # Compiled patterns for symbol detection (no spaces already confirmed)
    _CAMEL_RE = re.compile(r"^[a-z]+[A-Z]")       # starts lower, has upper
    _PASCAL_RE = re.compile(r"^[A-Z][a-z]+[A-Z]")  # starts Upper, has another Upper
    _SNAKE_RE = re.compile(r"^[a-z][a-z0-9]*_[a-z]")  # lower_lower pattern

    def detect_query_type(self, query: str) -> str:
        """Detect whether query is a symbol or natural language.

        Symbol patterns: dots, ::, #, camelCase, PascalCase, snake_case (all without spaces).
        """
        # Spaces → natural language
        if " " in query:
            return "nl"

        # Explicit separator characters
        if "." in query:
            return "symbol"
        if "::" in query:
            return "symbol"
        if "#" in query:
            return "symbol"

        # Naming convention patterns (no spaces confirmed above)
        if self._CAMEL_RE.search(query):
            return "symbol"
        if self._PASCAL_RE.search(query):
            return "symbol"
        if self._SNAKE_RE.search(query):
            return "symbol"

        return "nl"

    async def handle_symbol_query(
        self,
        query: str,
        repo: str,
    ) -> QueryResponse:
        """Execute the symbol query pipeline: ES term → fuzzy → NL fallback.

        Raises:
            ValidationError: If query is empty or exceeds 200 chars.
            RetrievalError: If all retrieval paths fail.
        """
        # Step 1: Validate
        if not query or not query.strip():
            raise ValidationError("query must not be empty")
        if len(query) > 200:
            raise ValidationError("query exceeds 200 character limit")

        # Step 2: ES term query (exact match on symbol.raw)
        term_body = {
            "query": {
                "bool": {
                    "must": [{"term": {"symbol.raw": query}}],
                    "filter": [{"term": {"repo_id": repo}}],
                }
            }
        }
        term_hits = await self._retriever._execute_search(
            self._retriever._code_index, term_body, 200
        )

        if term_hits:
            chunks = self._retriever._parse_code_hits(term_hits)
            reranked = self._reranker.rerank(query, chunks, top_k=6)
            return self._response_builder.build(reranked, query, "symbol", repo)

        # Step 3: ES fuzzy query (fuzziness=AUTO)
        fuzzy_body = {
            "query": {
                "bool": {
                    "must": [
                        {"match": {"symbol": {"query": query, "fuzziness": "AUTO"}}}
                    ],
                    "filter": [{"term": {"repo_id": repo}}],
                }
            }
        }
        fuzzy_hits = await self._retriever._execute_search(
            self._retriever._code_index, fuzzy_body, 200
        )

        if fuzzy_hits:
            chunks = self._retriever._parse_code_hits(fuzzy_hits)
            reranked = self._reranker.rerank(query, chunks, top_k=6)
            return self._response_builder.build(reranked, query, "symbol", repo)

        # Step 4: NL fallback
        return await self.handle_nl_query(query, repo)

    def _extract_identifiers(self, query: str) -> list[str]:
        """Extract code identifiers from an NL query."""
        matches = _IDENTIFIER_RE.findall(query)
        seen: set[str] = set()
        identifiers: list[str] = []
        for group in matches:
            for m in group:
                if m and m not in seen:
                    seen.add(m)
                    identifiers.append(m)
        return identifiers

    async def _symbol_boost_search(
        self, identifiers: list[str], repo: str
    ) -> list[ScoredChunk]:
        """Fire parallel ES term queries on symbol.raw for each identifier."""
        tasks = [
            self._retriever._execute_search(
                self._retriever._code_index,
                {
                    "query": {
                        "bool": {
                            "must": [{"term": {"symbol.raw": ident}}],
                            "filter": [{"term": {"repo_id": repo}}],
                        }
                    }
                },
                10,
            )
            for ident in identifiers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        chunks: list[ScoredChunk] = []
        for result in results:
            if not isinstance(result, BaseException):
                chunks.extend(self._retriever._parse_code_hits(result))
        return chunks

    def _apply_boost_weight(
        self, chunks: list[ScoredChunk], weight: float
    ) -> list[ScoredChunk]:
        """Scale chunk scores by weight factor."""
        return [replace(c, score=c.score * weight) for c in chunks]
