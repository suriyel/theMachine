"""ResponseBuilder — assembles dual-list query response from reranked chunks."""

from __future__ import annotations

from src.query.response_models import (
    CodeResult,
    DocResult,
    QueryResponse,
    RulesSection,
)
from src.query.scored_chunk import ScoredChunk


class ResponseBuilder:
    """Builds structured QueryResponse from reranked ScoredChunks.

    Splits chunks by content_type into codeResults and docResults,
    truncates content exceeding max_content_length, and optionally
    attaches repository rules.
    """

    def __init__(self, max_content_length: int = 2000) -> None:
        self._max_content_length = max_content_length

    def build(
        self,
        chunks: list[ScoredChunk],
        query: str,
        query_type: str,
        repo: str | None = None,
        rules: list[ScoredChunk] | None = None,
    ) -> QueryResponse:
        """Assemble a QueryResponse from reranked chunks."""
        code_results = [
            self._build_code_result(c) for c in chunks if c.content_type == "code"
        ]
        doc_results = [
            self._build_doc_result(c) for c in chunks if c.content_type != "code"
        ]

        rules_section = self._build_rules(rules) if rules else None

        return QueryResponse(
            query=query,
            query_type=query_type,
            repo=repo,
            code_results=code_results,
            doc_results=doc_results,
            rules=rules_section,
        )

    def _truncate_content(self, content: str) -> tuple[str, bool]:
        """Truncate content to max_content_length with '...' if needed."""
        if len(content) > self._max_content_length:
            return content[: self._max_content_length] + "...", True
        return content, False

    def _build_code_result(self, chunk: ScoredChunk) -> CodeResult:
        """Build a CodeResult from a code ScoredChunk."""
        truncated_content, is_truncated = self._truncate_content(chunk.content)

        lines = None
        if chunk.line_start is not None and chunk.line_end is not None:
            lines = [chunk.line_start, chunk.line_end]

        return CodeResult(
            file_path=chunk.file_path,
            lines=lines,
            symbol=chunk.symbol,
            chunk_type=chunk.chunk_type,
            language=chunk.language,
            signature=chunk.signature,
            doc_comment=chunk.doc_comment,
            content=truncated_content,
            relevance_score=chunk.score,
            truncated=is_truncated,
        )

    def _build_doc_result(self, chunk: ScoredChunk) -> DocResult:
        """Build a DocResult from a doc/example ScoredChunk."""
        truncated_content, is_truncated = self._truncate_content(chunk.content)

        return DocResult(
            file_path=chunk.file_path,
            breadcrumb=chunk.breadcrumb,
            content=truncated_content,
            relevance_score=chunk.score,
            truncated=is_truncated,
        )

    def _build_rules(self, rules: list[ScoredChunk]) -> RulesSection:
        """Build a RulesSection from rule ScoredChunks."""
        agent_rules: list[str] = []
        contribution_guide: list[str] = []
        linter_config: list[str] = []

        for rule in rules:
            if rule.chunk_type == "contribution_guide":
                contribution_guide.append(rule.content)
            elif rule.chunk_type == "linter_config":
                linter_config.append(rule.content)
            else:
                # Default: agent_rules (includes "agent_rules" and unknown types)
                agent_rules.append(rule.content)

        return RulesSection(
            agent_rules=agent_rules,
            contribution_guide=contribution_guide,
            linter_config=linter_config,
        )
