"""Tests for CodeHighlighter (Feature #19 — Web UI Search Page).

# [no integration test]
"""

from __future__ import annotations

import pytest

from src.query.highlighter import CodeHighlighter


@pytest.fixture
def highlighter():
    return CodeHighlighter()


# T18: highlight("code", "unknownlang") returns HTML without exception
def test_highlight_unknown_language(highlighter):
    result = highlighter.highlight("code", "unknownlang")
    assert isinstance(result, str)
    assert "code" in result
    # Should not raise — falls back to plain text


# T19: highlight("", "python") returns HTML without crash
def test_highlight_empty_code(highlighter):
    result = highlighter.highlight("", "python")
    assert isinstance(result, str)
    # Should produce some HTML wrapper even for empty string


# T20: highlight("code", None) returns plain-text HTML
def test_highlight_none_language(highlighter):
    result = highlighter.highlight("code", None)
    assert isinstance(result, str)
    assert "code" in result


# T21: highlight("code", "") returns plain-text HTML
def test_highlight_empty_language(highlighter):
    result = highlighter.highlight("code", "")
    assert isinstance(result, str)
    assert "code" in result


# T28: highlight with language="python" returns HTML with Pygments token spans
def test_syntax_highlight_python_tokens(highlighter):
    code = "def hello():\n    return 42"
    result = highlighter.highlight(code, "python")
    assert isinstance(result, str)
    # Should contain span elements from Pygments with inline styles
    assert "<span" in result
    assert "def" in result
    assert "hello" in result
    # Python keyword "def" must have UCD keyword color (#ff7b72 / #FF7B72)
    assert "#ff7b72" in result.lower(), "UCD keyword color #ff7b72 missing — wrong style used?"
    # TextLexer would not produce colored spans for "def", only Python lexer would
    import re
    keyword_spans = re.findall(r'<span style="color: #[Ff][Ff]7[Bb]72">def</span>', result)
    assert len(keyword_spans) > 0, "'def' not in a UCD-colored span — Python lexer not used"
