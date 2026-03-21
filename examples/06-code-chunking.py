"""Example: Code Chunking — Feature #6.

Demonstrates tree-sitter AST-based code chunking, markdown doc chunking,
and rule file extraction.
"""

from src.indexing.chunker import Chunker, CodeChunk
from src.indexing.content_extractor import ContentType, ExtractedFile
from src.indexing.doc_chunker import DocChunker
from src.indexing.rule_extractor import RuleExtractor


def demo_code_chunking() -> None:
    """Chunk a Python file into L1/L2/L3 chunks using tree-sitter."""
    python_code = """\
import os

class FileReader:
    \"\"\"Reads files from disk.\"\"\"

    def read(self, path: str) -> str:
        \"\"\"Read a file and return its content.\"\"\"
        with open(path) as f:
            return f.read()

    def exists(self, path: str) -> bool:
        \"\"\"Check if a file exists.\"\"\"
        return os.path.exists(path)
"""

    file = ExtractedFile(
        path="src/reader.py",
        content_type=ContentType.CODE,
        content=python_code,
        size=len(python_code),
    )

    chunker = Chunker()
    chunks = chunker.chunk(file, repo_id="demo-repo", branch="main")

    print("=== Code Chunking (Python) ===")
    print(f"Total chunks: {len(chunks)}")
    for chunk in chunks:
        print(
            f"  [{chunk.chunk_type:8}] symbol={chunk.symbol or '(file)':15} "
            f"lines={chunk.line_start}-{chunk.line_end}"
        )
    print()


def demo_doc_chunking() -> None:
    """Chunk a markdown file by heading structure."""
    markdown = """\
# Project Guide

Introduction to the project.

## Installation

Run `pip install mypackage` to install.

### Prerequisites

You need Python 3.10+.

## Usage

```python
import mypackage
mypackage.run()
```

## License

MIT License.
"""

    file = ExtractedFile(
        path="README.md",
        content_type=ContentType.DOC,
        content=markdown,
        size=len(markdown),
    )

    doc_chunker = DocChunker()
    chunks = doc_chunker.chunk_markdown(file, repo_id="demo-repo", branch="main")

    print("=== Doc Chunking (Markdown) ===")
    print(f"Total chunks: {len(chunks)}")
    for chunk in chunks:
        print(
            f"  [H{chunk.heading_level}] breadcrumb={chunk.breadcrumb}  "
            f"tokens={chunk.content_tokens}  "
            f"code_blocks={len(chunk.code_examples)}"
        )
    print()


def demo_rule_extraction() -> None:
    """Extract rules from a CLAUDE.md file."""
    claude_md = """\
# CLAUDE.md

## Rules

- Always use type hints
- Run tests before committing
"""

    file = ExtractedFile(
        path="CLAUDE.md",
        content_type=ContentType.RULE,
        content=claude_md,
        size=len(claude_md),
    )

    extractor = RuleExtractor()
    chunks = extractor.extract_rules(file, repo_id="demo-repo", branch="main")

    print("=== Rule Extraction (CLAUDE.md) ===")
    print(f"Total chunks: {len(chunks)}")
    for chunk in chunks:
        print(f"  rule_type={chunk.rule_type}  path={chunk.file_path}")
        print(f"  content preview: {chunk.content[:80]}...")
    print()


if __name__ == "__main__":
    demo_code_chunking()
    demo_doc_chunking()
    demo_rule_extraction()
