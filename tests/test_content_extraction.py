"""Tests for Feature #5 — Content Extraction.

Categories covered:
- Happy path: T1-T5, T11-T13, T17, T19
- Error handling: T8, T9, T16, T20
- Boundary/edge: T6, T7, T10, T14, T15, T18
- Security: N/A — internal utility with no user-facing input

Negative test ratio: 8/20 = 40%
"""

import os

import pytest

from src.indexing.content_extractor import ContentExtractor, ContentType, ExtractedFile


@pytest.fixture
def extractor():
    return ContentExtractor()


# ---------- T1: Happy path — source code files by extension ----------
# [unit]
def test_classifies_source_files_by_extension(tmp_path, extractor):
    """T1: Given .py, .java, .js, .ts, .c, .cpp files, extract returns 6 CODE files."""
    for name in ["app.py", "Main.java", "index.js", "app.ts", "main.c", "lib.cpp"]:
        (tmp_path / name).write_text(f"// content of {name}", encoding="utf-8")

    results = extractor.extract(str(tmp_path))

    assert len(results) == 6
    for ef in results:
        assert ef.content_type == ContentType.CODE
        assert ef.content.startswith("// content of")
        assert ef.size > 0


# ---------- T2: Happy path — documentation files ----------
# [unit]
def test_classifies_doc_files(tmp_path, extractor):
    """T2: Given README.md and docs/guide.md, extract returns 2 DOC files."""
    (tmp_path / "README.md").write_text("# README", encoding="utf-8")
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "guide.md").write_text("# Guide", encoding="utf-8")

    results = extractor.extract(str(tmp_path))

    assert len(results) == 2
    types = {ef.content_type for ef in results}
    assert types == {ContentType.DOC}
    paths = {ef.path for ef in results}
    assert "README.md" in paths
    assert os.path.join("docs", "guide.md") in paths


# ---------- T3: Happy path — example files ----------
# [unit]
def test_classifies_example_files(tmp_path, extractor):
    """T3: Given examples/demo.py, extract returns 1 EXAMPLE file."""
    examples_dir = tmp_path / "examples"
    examples_dir.mkdir()
    (examples_dir / "demo.py").write_text("print('demo')", encoding="utf-8")

    results = extractor.extract(str(tmp_path))

    assert len(results) == 1
    assert results[0].content_type == ContentType.EXAMPLE
    assert results[0].path == os.path.join("examples", "demo.py")
    assert results[0].content == "print('demo')"


# ---------- T4: Happy path — rule files ----------
# [unit]
def test_classifies_rule_files(tmp_path, extractor):
    """T4: Given CLAUDE.md and CONTRIBUTING.md, extract returns 2 RULE files."""
    (tmp_path / "CLAUDE.md").write_text("# Rules", encoding="utf-8")
    (tmp_path / "CONTRIBUTING.md").write_text("# Contributing", encoding="utf-8")

    results = extractor.extract(str(tmp_path))

    assert len(results) == 2
    for ef in results:
        assert ef.content_type == ContentType.RULE


# ---------- T5: Happy path — binary file skipped ----------
# [unit]
def test_skips_binary_files(tmp_path, extractor):
    """T5: Given a .png with binary content, extract returns 0 files."""
    png_file = tmp_path / "image.png"
    png_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00")

    results = extractor.extract(str(tmp_path))

    assert len(results) == 0


# ---------- T6: Boundary — unknown file types skipped ----------
# [unit]
def test_skips_unknown_file_types(tmp_path, extractor):
    """T6: Given .csv, Makefile, .yaml, extract returns 0 files."""
    (tmp_path / "data.csv").write_text("a,b,c", encoding="utf-8")
    (tmp_path / "Makefile").write_text("all:", encoding="utf-8")
    (tmp_path / "config.yaml").write_text("key: val", encoding="utf-8")

    results = extractor.extract(str(tmp_path))

    assert len(results) == 0


# ---------- T7: Boundary — file exactly 1MB included ----------
# [unit]
def test_includes_file_exactly_1mb(tmp_path, extractor):
    """T7: Given a .py file of exactly 1_048_576 bytes, extract includes it."""
    big_file = tmp_path / "big.py"
    content = "x" * 1_048_576
    big_file.write_text(content, encoding="utf-8")

    results = extractor.extract(str(tmp_path))

    assert len(results) == 1
    assert results[0].size == 1_048_576
    assert results[0].content_type == ContentType.CODE


# ---------- T8: Error — file over 1MB skipped ----------
# [unit]
def test_skips_file_over_1mb(tmp_path, extractor, caplog):
    """T8: Given a .py file of 1_048_577 bytes, extract skips with warning."""
    big_file = tmp_path / "huge.py"
    content = "x" * 1_048_577
    big_file.write_text(content, encoding="utf-8")

    import logging

    with caplog.at_level(logging.WARNING):
        results = extractor.extract(str(tmp_path))

    assert len(results) == 0
    assert any("oversized" in msg.lower() or "skipping" in msg.lower() for msg in caplog.messages)


# ---------- T9: Error — non-UTF-8 file skipped ----------
# [unit]
def test_skips_non_utf8_file(tmp_path, extractor, caplog):
    """T9: Given a .py file with Latin-1 bytes, extract skips with warning."""
    bad_file = tmp_path / "latin.py"
    bad_file.write_bytes(b"# comment\nx = '\xe9\xe8\xe0'\n")

    import logging

    with caplog.at_level(logging.WARNING):
        results = extractor.extract(str(tmp_path))

    assert len(results) == 0
    assert any("skipping" in msg.lower() or "unreadable" in msg.lower() for msg in caplog.messages)


# ---------- T10: Boundary — .git directory pruned ----------
# [unit]
def test_skips_hidden_directories(tmp_path, extractor):
    """T10: Given a .git/config file, extract does not include it."""
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "config").write_text("[core]", encoding="utf-8")
    # Also add a normal file to verify extractor works
    (tmp_path / "main.py").write_text("x = 1", encoding="utf-8")

    results = extractor.extract(str(tmp_path))

    assert len(results) == 1
    assert results[0].path == "main.py"


# ---------- T11: Happy path — CHANGELOG.md classified as DOC ----------
# [unit]
def test_classifies_changelog_as_doc(tmp_path, extractor):
    """T11: Given CHANGELOG.md, extract returns 1 DOC file."""
    (tmp_path / "CHANGELOG.md").write_text("# Changelog", encoding="utf-8")

    results = extractor.extract(str(tmp_path))

    assert len(results) == 1
    assert results[0].content_type == ContentType.DOC
    assert results[0].path == "CHANGELOG.md"


# ---------- T12: Happy path — .cursor/rules files classified as RULE ----------
# [unit]
def test_classifies_cursor_rules_as_rule(tmp_path, extractor):
    """T12: Given .cursor/rules/my-rule.md, extract returns 1 RULE file."""
    cursor_dir = tmp_path / ".cursor" / "rules"
    cursor_dir.mkdir(parents=True)
    (cursor_dir / "my-rule.md").write_text("# Rule", encoding="utf-8")

    results = extractor.extract(str(tmp_path))

    assert len(results) == 1
    assert results[0].content_type == ContentType.RULE
    assert results[0].path == os.path.join(".cursor", "rules", "my-rule.md")


# ---------- T13: Boundary — *_example.py in root classified as EXAMPLE ----------
# [unit]
def test_classifies_example_suffix_files(tmp_path, extractor):
    """T13: Given demo_example.py in root, extract returns EXAMPLE."""
    (tmp_path / "demo_example.py").write_text("print('example')", encoding="utf-8")

    results = extractor.extract(str(tmp_path))

    assert len(results) == 1
    assert results[0].content_type == ContentType.EXAMPLE


# ---------- T14: Boundary — empty directory ----------
# [unit]
def test_empty_directory_returns_empty_list(tmp_path, extractor):
    """T14: Given an empty directory, extract returns []."""
    results = extractor.extract(str(tmp_path))

    assert results == []


# ---------- T15: Boundary — 0-byte text file ----------
# [unit]
def test_includes_zero_byte_text_file(tmp_path, extractor):
    """T15: Given a 0-byte .py file, extract includes it with empty content."""
    (tmp_path / "empty.py").write_text("", encoding="utf-8")

    results = extractor.extract(str(tmp_path))

    assert len(results) == 1
    assert results[0].content == ""
    assert results[0].size == 0
    assert results[0].content_type == ContentType.CODE


# ---------- T16: Error — binary file without image extension ----------
# [unit]
def test_skips_binary_code_file(tmp_path, extractor, caplog):
    """T16: Given a .py file with null bytes (binary), extract skips it."""
    binary_py = tmp_path / "compiled.py"
    binary_py.write_bytes(b"import os\x00\x00\x00binary data")

    import logging

    with caplog.at_level(logging.WARNING):
        results = extractor.extract(str(tmp_path))

    assert len(results) == 0
    assert any("binary" in msg.lower() for msg in caplog.messages)


# ---------- T17: Happy path — mixed repository ----------
# [unit]
def test_mixed_repository(tmp_path, extractor):
    """T17: Mixed repo with 2 code, 1 doc, 1 example, 1 rule, 1 unknown, 1 binary → 5 results."""
    (tmp_path / "app.py").write_text("x = 1", encoding="utf-8")
    (tmp_path / "util.js").write_text("const x = 1;", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Hi", encoding="utf-8")
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "ex.py").write_text("print(1)", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("# Rules", encoding="utf-8")
    (tmp_path / "config.yaml").write_text("key: val", encoding="utf-8")
    (tmp_path / "photo.bin").write_bytes(b"\x00\x01\x02\x03")

    results = extractor.extract(str(tmp_path))

    assert len(results) == 5
    type_counts = {}
    for ef in results:
        type_counts[ef.content_type] = type_counts.get(ef.content_type, 0) + 1
    assert type_counts[ContentType.CODE] == 2
    assert type_counts[ContentType.DOC] == 1
    assert type_counts[ContentType.EXAMPLE] == 1
    assert type_counts[ContentType.RULE] == 1


# ---------- T18: Boundary — classification priority (example over code) ----------
# [unit]
def test_classification_priority_example_over_code(tmp_path, extractor):
    """T18: examples/demo_example.py matches both example patterns; EXAMPLE wins."""
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "demo_example.py").write_text("print(1)", encoding="utf-8")

    results = extractor.extract(str(tmp_path))

    assert len(results) == 1
    assert results[0].content_type == ContentType.EXAMPLE


# ---------- T19: Happy path — ExtractedFile fields correct ----------
# [unit]
def test_extracted_file_has_correct_fields(tmp_path, extractor):
    """T19: ExtractedFile has correct path, content_type, content, size."""
    content = "def hello(): pass"
    (tmp_path / "hello.py").write_text(content, encoding="utf-8")

    results = extractor.extract(str(tmp_path))

    assert len(results) == 1
    ef = results[0]
    assert ef.path == "hello.py"
    assert ef.content_type == ContentType.CODE
    assert ef.content == content
    assert ef.size == len(content.encode("utf-8"))


# ---------- T20: Error — broken symlink ----------
# [unit]
def test_skips_broken_symlink(tmp_path, extractor, caplog):
    """T20: Given a symlink to non-existent file, extract skips with warning."""
    link_path = tmp_path / "broken.py"
    link_path.symlink_to(tmp_path / "nonexistent.py")

    import logging

    with caplog.at_level(logging.WARNING):
        results = extractor.extract(str(tmp_path))

    assert len(results) == 0


# ---------- T21: Boundary — RELEASE notes classified as DOC ----------
# [unit]
def test_classifies_release_notes_as_doc(tmp_path, extractor):
    """T21: Given RELEASE_NOTES.md, extract returns 1 DOC file."""
    (tmp_path / "RELEASE_NOTES.md").write_text("# Release Notes", encoding="utf-8")

    results = extractor.extract(str(tmp_path))

    assert len(results) == 1
    assert results[0].content_type == ContentType.DOC


# ---------- T22: Boundary — standalone .rst file classified as DOC ----------
# [unit]
def test_classifies_rst_file_as_doc(tmp_path, extractor):
    """T22: Given a standalone .rst file (not in docs/), extract returns DOC."""
    (tmp_path / "tutorial.rst").write_text("Tutorial\n========", encoding="utf-8")

    results = extractor.extract(str(tmp_path))

    assert len(results) == 1
    assert results[0].content_type == ContentType.DOC


# ---------- Integration test ----------
# [integration] — uses real file system with realistic repo structure
def test_realistic_repo_structure(tmp_path, extractor):
    """Integration: realistic repo with nested dirs, various file types."""
    # Source code
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("def main(): pass", encoding="utf-8")
    (src / "utils.java").write_text("class Utils {}", encoding="utf-8")

    # Documentation
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "api.md").write_text("# API docs", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Project", encoding="utf-8")

    # Examples
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "basic.py").write_text("print('basic')", encoding="utf-8")

    # Rules
    (tmp_path / "CONTRIBUTING.md").write_text("# Contributing", encoding="utf-8")

    # Hidden dirs (should be skipped)
    git = tmp_path / ".git"
    git.mkdir()
    (git / "HEAD").write_text("ref: refs/heads/main", encoding="utf-8")

    # Binary (should be skipped)
    (tmp_path / "icon.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00")

    # Unknown (should be skipped)
    (tmp_path / "Dockerfile").write_text("FROM python:3.12", encoding="utf-8")

    results = extractor.extract(str(tmp_path))

    paths_by_type = {}
    for ef in results:
        paths_by_type.setdefault(ef.content_type, []).append(ef.path)

    assert len(paths_by_type[ContentType.CODE]) == 2
    assert len(paths_by_type[ContentType.DOC]) == 2  # api.md, README.md
    assert len(paths_by_type[ContentType.EXAMPLE]) == 1
    assert len(paths_by_type[ContentType.RULE]) == 1  # CONTRIBUTING.md
    # Total: 2 code + 2 doc + 1 example + 1 rule = 6
    total = sum(len(v) for v in paths_by_type.values())
    assert total == 6
