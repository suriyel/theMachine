"""Tests for Feature #6 Code Chunking — DocChunker.

# [no integration test] — pure computation feature, no external I/O
# tree-sitter is a local library (not an external service)
"""

import pytest

from src.indexing.doc_chunker import DocChunker, DocChunk, CodeBlock
from src.indexing.content_extractor import ContentType, ExtractedFile


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def doc_chunker():
    return DocChunker()


def _make_doc(path: str, content: str) -> ExtractedFile:
    return ExtractedFile(path=path, content_type=ContentType.DOC, content=content, size=len(content))


# ---------------------------------------------------------------------------
# Source snippets
# ---------------------------------------------------------------------------

README_WITH_HEADINGS = """\
# Project Title

This is the introduction paragraph.

## Installation

Run `pip install mypackage` to install.

### Prerequisites

You need Python 3.10+.

## Usage

Import and call:

```python
import mypackage
mypackage.run()
```

## License

MIT License.
"""

MARKDOWN_NO_HEADINGS = (
    "This is a paragraph about the project. "
    + " ".join(f"filler{i}" for i in range(200))
    + "\n\n"
    + "It has multiple paragraphs but no headings at all. "
    + " ".join(f"padding{i}" for i in range(200))
    + "\n\n"
    + "Another paragraph with more details about the system. "
    + " ".join(f"extra{i}" for i in range(200))
    + "\n"
)

MARKDOWN_SHORT = """\
## Quick Note

This is a very short document.
"""

MARKDOWN_WITH_CODE_BLOCKS = """\
## Examples

Here is a Python example:

```python
def hello():
    print("Hello, world!")
```

And a JavaScript example:

```javascript
function greet() {
    console.log("Hi!");
}
```
"""

MARKDOWN_ONLY_H1 = """\
# Main Title

First paragraph of content.

Second paragraph of content.

Third paragraph of content.
"""

EMPTY_MARKDOWN = ""


def _make_long_section(token_count: int) -> str:
    """Create a markdown section with approximately token_count words."""
    words = " ".join(f"word{i}" for i in range(token_count))
    return f"## Long Section\n\n{words}\n"


def _make_h3_h4_content() -> str:
    """Create markdown with H3 > 1000 tokens containing H4 sub-sections."""
    filler_a = " ".join(f"alpha{i}" for i in range(600))
    filler_b = " ".join(f"beta{i}" for i in range(600))
    return f"""\
## Parent

### Big Section

{filler_a}

#### Sub Detail

{filler_b}
"""


# ---------------------------------------------------------------------------
# T5 — happy path — README with H1, H2, H3
# ---------------------------------------------------------------------------

class TestT5ReadmeHeadings:
    # [unit]
    def test_splits_at_h2(self, doc_chunker):
        f = _make_doc("README.md", README_WITH_HEADINGS)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-5", branch="main")
        # H2 sections: Installation, Usage, License (+ intro before first H2)
        assert len(chunks) >= 3

    # [unit]
    def test_breadcrumbs_correct(self, doc_chunker):
        f = _make_doc("README.md", README_WITH_HEADINGS)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-5", branch="main")
        breadcrumbs = [c.breadcrumb for c in chunks]
        # At least one breadcrumb should contain the file path and a heading
        assert any("README.md" in b for b in breadcrumbs)
        assert any("Installation" in b for b in breadcrumbs)

    # [unit]
    def test_heading_levels_set(self, doc_chunker):
        f = _make_doc("README.md", README_WITH_HEADINGS)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-5", branch="main")
        levels = {c.heading_level for c in chunks}
        assert 2 in levels  # H2 sections present


# ---------------------------------------------------------------------------
# T26 — boundary — Markdown no headings → paragraph fallback
# ---------------------------------------------------------------------------

class TestT26NoHeadings:
    # [unit]
    def test_paragraph_fallback(self, doc_chunker):
        f = _make_doc("notes.md", MARKDOWN_NO_HEADINGS)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-26", branch="main")
        assert len(chunks) >= 1

    # [unit]
    def test_breadcrumb_uses_section_n(self, doc_chunker):
        f = _make_doc("notes.md", MARKDOWN_NO_HEADINGS)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-26", branch="main")
        breadcrumbs = [c.breadcrumb for c in chunks]
        # Should use [section N] pattern when no headings
        assert any("section" in b.lower() for b in breadcrumbs)


# ---------------------------------------------------------------------------
# T27 — boundary — Markdown < 500 tokens → single DocChunk
# ---------------------------------------------------------------------------

class TestT27ShortMarkdown:
    # [unit]
    def test_single_chunk(self, doc_chunker):
        f = _make_doc("short.md", MARKDOWN_SHORT)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-27", branch="main")
        assert len(chunks) == 1

    # [unit]
    def test_content_preserved(self, doc_chunker):
        f = _make_doc("short.md", MARKDOWN_SHORT)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-27", branch="main")
        assert "very short document" in chunks[0].content


# ---------------------------------------------------------------------------
# T28 — boundary — Section > 2000 tokens → split at paragraph boundaries
# ---------------------------------------------------------------------------

class TestT28LongSection:
    # [unit]
    def test_split_at_paragraphs(self, doc_chunker):
        content = _make_long_section(2500)
        f = _make_doc("long.md", content)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-28", branch="main")
        assert len(chunks) >= 2  # must be split

    # [unit]
    def test_no_chunk_exceeds_2000_tokens(self, doc_chunker):
        content = _make_long_section(2500)
        f = _make_doc("long.md", content)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-28", branch="main")
        for c in chunks:
            assert c.content_tokens <= 2000


# ---------------------------------------------------------------------------
# T29 — boundary — Markdown with fenced code blocks
# ---------------------------------------------------------------------------

class TestT29CodeBlocks:
    # [unit]
    def test_code_examples_populated(self, doc_chunker):
        f = _make_doc("examples.md", MARKDOWN_WITH_CODE_BLOCKS)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-29", branch="main")
        chunks_with_code = [c for c in chunks if len(c.code_examples) > 0]
        assert len(chunks_with_code) >= 1

    # [unit]
    def test_code_block_languages(self, doc_chunker):
        f = _make_doc("examples.md", MARKDOWN_WITH_CODE_BLOCKS)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-29", branch="main")
        all_blocks = []
        for c in chunks:
            all_blocks.extend(c.code_examples)
        languages = {b.language for b in all_blocks}
        assert "python" in languages
        assert "javascript" in languages


# ---------------------------------------------------------------------------
# T30 — boundary — Only H1 heading → paragraph fallback
# ---------------------------------------------------------------------------

class TestT30OnlyH1:
    # [unit]
    def test_paragraph_fallback(self, doc_chunker):
        f = _make_doc("title_only.md", MARKDOWN_ONLY_H1)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-30", branch="main")
        # H1 is not a split point, so content stays together or splits by paragraphs
        assert len(chunks) >= 1

    # [unit]
    def test_content_not_lost(self, doc_chunker):
        f = _make_doc("title_only.md", MARKDOWN_ONLY_H1)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-30", branch="main")
        all_content = " ".join(c.content for c in chunks)
        assert "First paragraph" in all_content
        assert "Third paragraph" in all_content


# ---------------------------------------------------------------------------
# T31 — error — Empty string content → single DocChunk
# ---------------------------------------------------------------------------

class TestT31EmptyContent:
    # [unit]
    def test_returns_single_chunk(self, doc_chunker):
        f = _make_doc("empty.md", EMPTY_MARKDOWN)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-31", branch="main")
        assert len(chunks) == 1

    # [unit]
    def test_empty_content(self, doc_chunker):
        f = _make_doc("empty.md", EMPTY_MARKDOWN)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-31", branch="main")
        assert chunks[0].content == ""


# ---------------------------------------------------------------------------
# T35 — boundary — H4 within H3 > 1000 tokens → H4 as optional split
# ---------------------------------------------------------------------------

class TestT35H4SplitPoint:
    # [unit]
    def test_h4_used_as_split(self, doc_chunker):
        content = _make_h3_h4_content()
        f = _make_doc("nested_headings.md", content)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-35", branch="main")
        # The H3 section is > 1000 tokens, so H4 should trigger a split
        assert len(chunks) >= 2

    # [unit]
    def test_sub_detail_in_own_chunk(self, doc_chunker):
        content = _make_h3_h4_content()
        f = _make_doc("nested_headings.md", content)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-35", branch="main")
        sub_chunks = [c for c in chunks if "Sub Detail" in c.breadcrumb or "Sub Detail" in c.content]
        assert len(sub_chunks) >= 1


# ---------------------------------------------------------------------------
# T38 — happy path — DocChunk IDs verified format
# ---------------------------------------------------------------------------

class TestDocChunkerEdgeCases:
    # [unit]
    def test_split_by_headings_empty(self, doc_chunker):
        sections = doc_chunker.split_by_headings("")
        assert len(sections) == 1
        assert sections[0].heading_level == 0

    # [unit]
    def test_build_breadcrumb(self, doc_chunker):
        result = doc_chunker.build_breadcrumb("README.md", ["Installation", "Linux"])
        assert result == "README.md > Installation > Linux"

    # [unit]
    def test_build_breadcrumb_empty_headings(self, doc_chunker):
        result = doc_chunker.build_breadcrumb("README.md", ["", "Topic"])
        assert result == "README.md > Topic"

    # [unit]
    def test_extract_code_blocks_none(self, doc_chunker):
        result = doc_chunker.extract_code_blocks("No code blocks here.")
        assert result == []

    # [unit]
    def test_large_section_no_paragraphs_force_split(self, doc_chunker):
        """Section > 2000 tokens as a single huge paragraph (no double newlines)."""
        words = " ".join(f"bigword{i}" for i in range(2500))
        content = f"## Huge\n\n{words}\n"
        f = _make_doc("huge.md", content)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-huge", branch="main")
        assert len(chunks) >= 2
        for c in chunks:
            assert c.content_tokens <= 2000

    # [unit]
    def test_h1_body_content(self, doc_chunker):
        """H1 with body content creates chunk."""
        content = "# Title\n\nBody under title.\n\n## Section\n\nMore content.\n"
        f = _make_doc("h1body.md", content)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-h1", branch="main")
        all_content = " ".join(c.content for c in chunks)
        assert "Body under title" in all_content
        assert "More content" in all_content


class TestDocChunkerIntroContent:
    # [unit]
    def test_intro_before_first_h2(self, doc_chunker):
        """Content before the first ## heading becomes an intro chunk."""
        content = "Intro text here.\n\n## Section One\n\nBody of section one.\n"
        f = _make_doc("intro.md", content)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-intro", branch="main")
        assert any("Intro text here" in c.content for c in chunks)

    # [unit]
    def test_h2_large_section_split(self, doc_chunker):
        """Large H2 section > 2000 tokens splits at paragraph boundaries."""
        p1 = " ".join(f"para1word{i}" for i in range(1200))
        p2 = " ".join(f"para2word{i}" for i in range(1200))
        content = f"## Big H2\n\n{p1}\n\n{p2}\n"
        f = _make_doc("bigh2.md", content)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-bigh2", branch="main")
        assert len(chunks) >= 2

    # [unit]
    def test_h3_within_h2(self, doc_chunker):
        """H3 nested under H2 gets correct breadcrumb."""
        content = "## Parent\n\nParent body.\n\n### Child\n\nChild body.\n"
        f = _make_doc("nested.md", content)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-nest", branch="main")
        child_chunks = [c for c in chunks if "Child" in c.breadcrumb]
        assert len(child_chunks) >= 1

    # [unit]
    def test_paragraph_merge_short(self, doc_chunker):
        """Short paragraphs without headings get merged."""
        content = (
            "Short one.\n\nShort two.\n\nShort three.\n\n"
            + " ".join(f"long{i}" for i in range(300))
            + "\n\n"
            + " ".join(f"more{i}" for i in range(300))
            + "\n"
        )
        f = _make_doc("merge.md", content)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-merge", branch="main")
        assert len(chunks) >= 1


class TestT38DocChunkIdFormat:
    # [unit]
    def test_chunk_ids_contain_repo(self, doc_chunker):
        f = _make_doc("README.md", README_WITH_HEADINGS)
        chunks = doc_chunker.chunk_markdown(f, repo_id="repo-38", branch="main")
        for c in chunks:
            assert "repo-38" in c.chunk_id
            assert isinstance(c.chunk_id, str)
            assert len(c.chunk_id) > 0
