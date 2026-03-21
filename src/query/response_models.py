"""Response models for the Context Response Builder (Feature #12)."""

from __future__ import annotations

from pydantic import BaseModel


class CodeResult(BaseModel):
    """A single code result in the query response."""

    file_path: str
    lines: list[int] | None = None
    symbol: str | None = None
    chunk_type: str | None = None
    language: str | None = None
    signature: str | None = None
    doc_comment: str | None = None
    content: str
    relevance_score: float
    truncated: bool = False


class DocResult(BaseModel):
    """A single documentation result in the query response."""

    file_path: str
    breadcrumb: str | None = None
    content: str
    relevance_score: float
    truncated: bool = False


class RulesSection(BaseModel):
    """Repository rules section in the query response."""

    agent_rules: list[str] = []
    contribution_guide: list[str] = []
    linter_config: list[str] = []


class QueryResponse(BaseModel):
    """Dual-list response: codeResults + docResults + optional rules."""

    query: str
    query_type: str
    repo: str | None = None
    code_results: list[CodeResult] = []
    doc_results: list[DocResult] = []
    rules: RulesSection | None = None
