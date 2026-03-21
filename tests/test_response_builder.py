"""Tests for Context Response Builder (Feature #12).

Categories:
  - Happy path: T01-T05, T16
  - Boundary: T06-T13, T17
  - Error: T14-T15
  - Security: N/A — internal utility with no user-facing input

# [no integration test] — pure function, no external I/O
"""

from __future__ import annotations

import pytest

from src.query.scored_chunk import ScoredChunk


def _code_chunk(
    chunk_id: str = "c1",
    content: str = "def hello(): pass",
    symbol: str = "hello",
    score: float = 0.95,
    **kwargs,
) -> ScoredChunk:
    """Helper to create a code ScoredChunk."""
    defaults = dict(
        chunk_id=chunk_id,
        content_type="code",
        repo_id="my-org/my-app",
        file_path="src/main.py",
        content=content,
        score=score,
        language="python",
        chunk_type="function",
        symbol=symbol,
        signature="def hello(): pass",
        doc_comment="A greeting function.",
        line_start=1,
        line_end=10,
    )
    defaults.update(kwargs)
    return ScoredChunk(**defaults)


def _doc_chunk(
    chunk_id: str = "d1",
    content: str = "This is documentation.",
    score: float = 0.88,
    **kwargs,
) -> ScoredChunk:
    """Helper to create a doc ScoredChunk."""
    defaults = dict(
        chunk_id=chunk_id,
        content_type="doc",
        repo_id="my-org/my-app",
        file_path="docs/guide.md",
        content=content,
        score=score,
        breadcrumb="docs/guide.md > Auth > JWT",
    )
    defaults.update(kwargs)
    return ScoredChunk(**defaults)


def _example_chunk(
    chunk_id: str = "e1",
    content: str = "# Example usage\nprint('hello')",
    score: float = 0.75,
) -> ScoredChunk:
    """Helper to create an example ScoredChunk (goes to docResults)."""
    return ScoredChunk(
        chunk_id=chunk_id,
        content_type="example",
        repo_id="my-org/my-app",
        file_path="examples/auth.py",
        content=content,
        score=score,
        chunk_type="example",
    )


def _rule_chunk(
    chunk_id: str = "r1",
    chunk_type: str = "agent_rules",
    content: str = "Always use async sessions",
) -> ScoredChunk:
    """Helper to create a rule ScoredChunk."""
    return ScoredChunk(
        chunk_id=chunk_id,
        content_type="rule",
        repo_id="my-org/my-app",
        file_path=".claude/rules",
        content=content,
        score=0.0,
        chunk_type=chunk_type,
    )


# --- T01: Happy path — 6 chunks split into 3 code + 3 doc ---

# [unit]
def test_build_splits_6_chunks_into_code_and_doc_results():
    """VS-1: 6 reranked results (3 code, 2 doc, 1 example) → 3 codeResults + 3 docResults."""
    from src.query.response_builder import ResponseBuilder

    builder = ResponseBuilder()
    chunks = [
        _code_chunk(chunk_id="c1", symbol="func_a", score=0.95),
        _code_chunk(chunk_id="c2", symbol="func_b", score=0.90),
        _code_chunk(chunk_id="c3", symbol="func_c", score=0.85),
        _doc_chunk(chunk_id="d1", score=0.80),
        _doc_chunk(chunk_id="d2", content="More docs.", score=0.70),
        _example_chunk(chunk_id="e1", score=0.60),
    ]
    response = builder.build(chunks, query="auth", query_type="nl", repo="my-org/my-app")

    assert len(response.code_results) == 3
    assert len(response.doc_results) == 3

    # Verify code results are the code chunks
    code_symbols = [r.symbol for r in response.code_results]
    assert code_symbols == ["func_a", "func_b", "func_c"]

    # Verify doc results include both doc and example chunks
    doc_paths = [r.file_path for r in response.doc_results]
    assert "docs/guide.md" in doc_paths
    assert "examples/auth.py" in doc_paths


# --- T02: Happy path — code result fields fully populated ---

# [unit]
def test_code_result_has_all_required_fields():
    """VS-1, FR-010 AC1: Each code result has all required fields."""
    from src.query.response_builder import ResponseBuilder

    builder = ResponseBuilder()
    chunk = _code_chunk(
        chunk_id="c1",
        content="def greet(): return 'hi'",
        symbol="greet",
        score=0.95,
        line_start=10,
        line_end=20,
        signature="def greet() -> str",
        doc_comment="Greet the user.",
        language="python",
        chunk_type="function",
    )
    response = builder.build([chunk], query="greet", query_type="symbol", repo="my-org/my-app")

    assert len(response.code_results) == 1
    cr = response.code_results[0]
    assert cr.file_path == "src/main.py"
    assert cr.lines == [10, 20]
    assert cr.symbol == "greet"
    assert cr.chunk_type == "function"
    assert cr.language == "python"
    assert cr.signature == "def greet() -> str"
    assert cr.doc_comment == "Greet the user."
    assert cr.content == "def greet(): return 'hi'"
    assert cr.relevance_score == 0.95
    assert cr.truncated is False


# --- T03: Happy path — doc result with null symbol ---

# [unit]
def test_doc_result_has_breadcrumb_and_no_symbol():
    """FR-010 AC2: Doc chunks have breadcrumb, no symbol field."""
    from src.query.response_builder import ResponseBuilder

    builder = ResponseBuilder()
    chunk = _doc_chunk(chunk_id="d1", content="JWT docs.", score=0.88)
    response = builder.build([chunk], query="jwt", query_type="nl")

    assert len(response.doc_results) == 1
    dr = response.doc_results[0]
    assert dr.file_path == "docs/guide.md"
    assert dr.breadcrumb == "docs/guide.md > Auth > JWT"
    assert dr.content == "JWT docs."
    assert dr.relevance_score == 0.88
    assert dr.truncated is False
    # Doc results should not have symbol field
    assert not hasattr(dr, "symbol")


# --- T04: Happy path — content truncation at 2001 chars ---

# [unit]
def test_content_truncated_at_2001_chars():
    """VS-2, FR-010 AC3: Content >2000 chars is truncated with '...'."""
    from src.query.response_builder import ResponseBuilder

    builder = ResponseBuilder()
    long_content = "x" * 2001
    chunk = _code_chunk(chunk_id="c1", content=long_content, score=0.9)
    response = builder.build([chunk], query="test", query_type="nl")

    cr = response.code_results[0]
    assert len(cr.content) == 2003  # 2000 + "..."
    assert cr.content == "x" * 2000 + "..."
    assert cr.truncated is True


# --- T05: Happy path — rules section populated ---

# [unit]
def test_rules_section_populated_with_categories():
    """VS-3: Rules section includes categorized rule content."""
    from src.query.response_builder import ResponseBuilder

    builder = ResponseBuilder()
    rules = [
        _rule_chunk("r1", "agent_rules", "Use async sessions"),
        _rule_chunk("r2", "contribution_guide", "All PRs need tests"),
        _rule_chunk("r3", "linter_config", "ruff: line-length=120"),
    ]
    response = builder.build(
        [], query="test", query_type="nl", repo="my-org/my-app", rules=rules
    )

    assert response.rules is not None
    assert "Use async sessions" in response.rules.agent_rules
    assert "All PRs need tests" in response.rules.contribution_guide
    assert "ruff: line-length=120" in response.rules.linter_config


# --- T06: Boundary — empty chunks list ---

# [unit]
def test_empty_chunks_returns_empty_results():
    """Boundary: Empty chunks → empty codeResults + docResults."""
    from src.query.response_builder import ResponseBuilder

    builder = ResponseBuilder()
    response = builder.build([], query="test", query_type="nl")

    assert response.code_results == []
    assert response.doc_results == []
    assert response.rules is None


# --- T07: Boundary — content exactly 2000 chars (no truncation) ---

# [unit]
def test_content_exactly_2000_chars_not_truncated():
    """Boundary: Content at exactly 2000 chars → no truncation."""
    from src.query.response_builder import ResponseBuilder

    builder = ResponseBuilder()
    content = "a" * 2000
    chunk = _code_chunk(chunk_id="c1", content=content, score=0.9)
    response = builder.build([chunk], query="test", query_type="nl")

    cr = response.code_results[0]
    assert cr.content == content
    assert len(cr.content) == 2000
    assert cr.truncated is False


# --- T08: Boundary — content exactly 2001 chars (truncated) ---

# [unit]
def test_content_exactly_2001_chars_truncated():
    """Boundary: Content at 2001 chars → truncated to 2000 + '...'."""
    from src.query.response_builder import ResponseBuilder

    builder = ResponseBuilder()
    content = "b" * 2001
    chunk = _code_chunk(chunk_id="c1", content=content, score=0.9)
    response = builder.build([chunk], query="test", query_type="nl")

    cr = response.code_results[0]
    assert cr.content == "b" * 2000 + "..."
    assert len(cr.content) == 2003
    assert cr.truncated is True


# --- T09: Boundary — empty content string ---

# [unit]
def test_empty_content_string_preserved():
    """Boundary: Empty content → preserved as empty, not truncated."""
    from src.query.response_builder import ResponseBuilder

    builder = ResponseBuilder()
    chunk = _code_chunk(chunk_id="c1", content="", score=0.9)
    response = builder.build([chunk], query="test", query_type="nl")

    cr = response.code_results[0]
    assert cr.content == ""
    assert cr.truncated is False


# --- T10: Boundary — rules=None ---

# [unit]
def test_rules_none_omitted_from_response():
    """Boundary: rules=None → no rules section."""
    from src.query.response_builder import ResponseBuilder

    builder = ResponseBuilder()
    response = builder.build(
        [_code_chunk()], query="test", query_type="nl", rules=None
    )

    assert response.rules is None


# --- T11: Boundary — rules=[] (empty list) ---

# [unit]
def test_rules_empty_list_omitted_from_response():
    """Boundary: rules=[] → no rules section."""
    from src.query.response_builder import ResponseBuilder

    builder = ResponseBuilder()
    response = builder.build(
        [_code_chunk()], query="test", query_type="nl", rules=[]
    )

    assert response.rules is None


# --- T12: Boundary — chunk with line_start=None, line_end=None ---

# [unit]
def test_chunk_with_none_line_numbers():
    """Boundary: line_start/end=None → lines field is None."""
    from src.query.response_builder import ResponseBuilder

    builder = ResponseBuilder()
    chunk = _code_chunk(chunk_id="c1", line_start=None, line_end=None)
    response = builder.build([chunk], query="test", query_type="nl")

    cr = response.code_results[0]
    assert cr.lines is None


# --- T13: Boundary — code chunk with symbol=None ---

# [unit]
def test_code_chunk_with_none_symbol():
    """Boundary: Code chunk with symbol=None → symbol is None."""
    from src.query.response_builder import ResponseBuilder

    builder = ResponseBuilder()
    chunk = _code_chunk(chunk_id="c1", symbol=None)
    response = builder.build([chunk], query="test", query_type="nl")

    cr = response.code_results[0]
    assert cr.symbol is None


# --- T14: Error — all doc chunks, zero code ---

# [unit]
def test_all_doc_chunks_no_code():
    """Error: All doc chunks → codeResults=[], docResults populated."""
    from src.query.response_builder import ResponseBuilder

    builder = ResponseBuilder()
    chunks = [
        _doc_chunk(chunk_id="d1", score=0.9),
        _doc_chunk(chunk_id="d2", content="More.", score=0.8),
    ]
    response = builder.build(chunks, query="test", query_type="nl")

    assert response.code_results == []
    assert len(response.doc_results) == 2


# --- T15: Error — all code chunks, zero doc ---

# [unit]
def test_all_code_chunks_no_doc():
    """Error: All code chunks → docResults=[], codeResults populated."""
    from src.query.response_builder import ResponseBuilder

    builder = ResponseBuilder()
    chunks = [
        _code_chunk(chunk_id="c1", score=0.9),
        _code_chunk(chunk_id="c2", symbol="bar", score=0.8),
    ]
    response = builder.build(chunks, query="test", query_type="nl")

    assert len(response.code_results) == 2
    assert response.doc_results == []


# --- T16: Happy path — response metadata fields ---

# [unit]
def test_response_metadata_fields():
    """VS-1: QueryResponse has query, query_type, repo at top level."""
    from src.query.response_builder import ResponseBuilder

    builder = ResponseBuilder()
    response = builder.build(
        [_code_chunk()],
        query="how to auth",
        query_type="nl",
        repo="my-org/my-app",
    )

    assert response.query == "how to auth"
    assert response.query_type == "nl"
    assert response.repo == "my-org/my-app"


# --- T17: Boundary — rule chunk with unknown type ---

# [unit]
def test_rule_chunk_unknown_type_defaults_to_agent_rules():
    """Boundary: Unknown rule chunk_type → defaults to agent_rules bucket."""
    from src.query.response_builder import ResponseBuilder

    builder = ResponseBuilder()
    rules = [_rule_chunk("r1", "unknown_type", "Some rule content")]
    response = builder.build(
        [], query="test", query_type="nl", repo="my-org/my-app", rules=rules
    )

    assert response.rules is not None
    assert "Some rule content" in response.rules.agent_rules
    assert response.rules.contribution_guide == []
    assert response.rules.linter_config == []
