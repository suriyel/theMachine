"""Tests for Feature #6 Code Chunking — RuleExtractor.

# [no integration test] — pure computation feature, no external I/O
# tree-sitter is a local library (not an external service)
"""

import pytest

from src.indexing.rule_extractor import RuleExtractor, RuleChunk
from src.indexing.content_extractor import ContentType, ExtractedFile


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rule_extractor():
    return RuleExtractor()


def _make_rule(path: str, content: str) -> ExtractedFile:
    return ExtractedFile(path=path, content_type=ContentType.RULE, content=content, size=len(content))


# ---------------------------------------------------------------------------
# Source snippets
# ---------------------------------------------------------------------------

CLAUDE_MD_CONTENT = """\
# CLAUDE.md

## Project Rules

- Always use type hints in Python code
- Run tests before committing

## Code Style

- Use black for formatting
- Max line length: 100
"""

CONTRIBUTING_MD_CONTENT = """\
# Contributing

## Getting Started

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## Code Review

All PRs require at least one approval.
"""

EDITORCONFIG_CONTENT = """\
root = true

[*]
indent_style = space
indent_size = 4
end_of_line = lf
charset = utf-8
trim_trailing_whitespace = true
insert_final_newline = true

[*.md]
trim_trailing_whitespace = false
"""

CURSOR_RULE_CONTENT = """\
# My Custom Rule

## Instructions

- Use functional programming patterns
- Prefer immutability
- Document all public APIs
"""

EMPTY_RULE_CONTENT = ""


# ---------------------------------------------------------------------------
# T12 — happy path — CLAUDE.md → rule_type="agent_rules"
# ---------------------------------------------------------------------------

class TestT12ClaudeMd:
    # [unit]
    def test_rule_type_is_agent_rules(self, rule_extractor):
        f = _make_rule("CLAUDE.md", CLAUDE_MD_CONTENT)
        chunks = rule_extractor.extract_rules(f, repo_id="repo-12", branch="main")
        assert len(chunks) >= 1
        for c in chunks:
            assert c.rule_type == "agent_rules"

    # [unit]
    def test_content_preserved(self, rule_extractor):
        f = _make_rule("CLAUDE.md", CLAUDE_MD_CONTENT)
        chunks = rule_extractor.extract_rules(f, repo_id="repo-12", branch="main")
        all_content = " ".join(c.content for c in chunks)
        assert "type hints" in all_content

    # [unit]
    def test_file_path_set(self, rule_extractor):
        f = _make_rule("CLAUDE.md", CLAUDE_MD_CONTENT)
        chunks = rule_extractor.extract_rules(f, repo_id="repo-12", branch="main")
        for c in chunks:
            assert c.file_path == "CLAUDE.md"

    # [unit]
    def test_repo_id_set(self, rule_extractor):
        f = _make_rule("CLAUDE.md", CLAUDE_MD_CONTENT)
        chunks = rule_extractor.extract_rules(f, repo_id="repo-12", branch="main")
        for c in chunks:
            assert c.repo_id == "repo-12"


# ---------------------------------------------------------------------------
# T13 — happy path — CONTRIBUTING.md → rule_type="contribution_guide"
# ---------------------------------------------------------------------------

class TestT13ContributingMd:
    # [unit]
    def test_rule_type_is_contribution_guide(self, rule_extractor):
        f = _make_rule("CONTRIBUTING.md", CONTRIBUTING_MD_CONTENT)
        chunks = rule_extractor.extract_rules(f, repo_id="repo-13", branch="main")
        assert len(chunks) >= 1
        for c in chunks:
            assert c.rule_type == "contribution_guide"

    # [unit]
    def test_content_preserved(self, rule_extractor):
        f = _make_rule("CONTRIBUTING.md", CONTRIBUTING_MD_CONTENT)
        chunks = rule_extractor.extract_rules(f, repo_id="repo-13", branch="main")
        all_content = " ".join(c.content for c in chunks)
        assert "Fork the repository" in all_content


# ---------------------------------------------------------------------------
# T14 — happy path — .editorconfig → rule_type="editor_config"
# ---------------------------------------------------------------------------

class TestT14EditorConfig:
    # [unit]
    def test_rule_type_is_editor_config(self, rule_extractor):
        f = _make_rule(".editorconfig", EDITORCONFIG_CONTENT)
        chunks = rule_extractor.extract_rules(f, repo_id="repo-14", branch="main")
        assert len(chunks) >= 1
        for c in chunks:
            assert c.rule_type == "editor_config"

    # [unit]
    def test_content_preserved(self, rule_extractor):
        f = _make_rule(".editorconfig", EDITORCONFIG_CONTENT)
        chunks = rule_extractor.extract_rules(f, repo_id="repo-14", branch="main")
        all_content = " ".join(c.content for c in chunks)
        assert "indent_style" in all_content


# ---------------------------------------------------------------------------
# T15 — happy path — .cursor/rules/my-rule.md → rule_type="agent_rules"
# ---------------------------------------------------------------------------

class TestT15CursorRules:
    # [unit]
    def test_rule_type_is_agent_rules(self, rule_extractor):
        f = _make_rule(".cursor/rules/my-rule.md", CURSOR_RULE_CONTENT)
        chunks = rule_extractor.extract_rules(f, repo_id="repo-15", branch="main")
        assert len(chunks) >= 1
        for c in chunks:
            assert c.rule_type == "agent_rules"

    # [unit]
    def test_content_preserved(self, rule_extractor):
        f = _make_rule(".cursor/rules/my-rule.md", CURSOR_RULE_CONTENT)
        chunks = rule_extractor.extract_rules(f, repo_id="repo-15", branch="main")
        all_content = " ".join(c.content for c in chunks)
        assert "functional programming" in all_content

    # [unit]
    def test_file_path_set(self, rule_extractor):
        f = _make_rule(".cursor/rules/my-rule.md", CURSOR_RULE_CONTENT)
        chunks = rule_extractor.extract_rules(f, repo_id="repo-15", branch="main")
        for c in chunks:
            assert c.file_path == ".cursor/rules/my-rule.md"


# ---------------------------------------------------------------------------
# T32 — error — Empty content → RuleChunk with empty content
# ---------------------------------------------------------------------------

class TestRuleExtractorLinterConfig:
    # [unit]
    def test_linter_config_default(self, rule_extractor):
        """Unknown rule file defaults to linter_config."""
        f = _make_rule("tsconfig.json", '{"strict": true}')
        chunks = rule_extractor.extract_rules(f, repo_id="repo-lc", branch="main")
        assert chunks[0].rule_type == "linter_config"


class TestRuleExtractorParseMethods:
    # [unit]
    def test_parse_claude_md(self, rule_extractor):
        result = rule_extractor.parse_claude_md("## Rules\n\n- Be nice\n\n## Style\n\n- Use black")
        assert len(result) >= 2

    # [unit]
    def test_parse_contributing(self, rule_extractor):
        result = rule_extractor.parse_contributing("## Setup\n\nClone repo\n\n## Review\n\nAll PRs reviewed")
        assert len(result) >= 2

    # [unit]
    def test_parse_cursor_rules(self, rule_extractor):
        result = rule_extractor.parse_cursor_rules("## Rule 1\n\nDo X\n\n## Rule 2\n\nDo Y")
        assert len(result) >= 2

    # [unit]
    def test_parse_empty(self, rule_extractor):
        result = rule_extractor.parse_claude_md("")
        assert result == []


class TestT32EmptyContent:
    # [unit]
    def test_returns_rule_chunk(self, rule_extractor):
        f = _make_rule("CLAUDE.md", EMPTY_RULE_CONTENT)
        chunks = rule_extractor.extract_rules(f, repo_id="repo-32", branch="main")
        assert len(chunks) >= 1

    # [unit]
    def test_empty_content_field(self, rule_extractor):
        f = _make_rule("CLAUDE.md", EMPTY_RULE_CONTENT)
        chunks = rule_extractor.extract_rules(f, repo_id="repo-32", branch="main")
        assert chunks[0].content == ""
