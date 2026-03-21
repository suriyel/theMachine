"""ScoredChunk — unified scored result from retrieval."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ScoredChunk:
    """A chunk scored by a retrieval method (BM25, vector, or reranker)."""

    chunk_id: str
    content_type: str  # "code" | "doc"
    repo_id: str
    file_path: str
    content: str
    score: float

    # Code-specific (None for doc chunks)
    language: str | None = None
    chunk_type: str | None = None
    symbol: str | None = None
    signature: str | None = None
    doc_comment: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    parent_class: str | None = None

    # Doc-specific (None for code chunks)
    breadcrumb: str | None = None
    heading_level: int | None = None
