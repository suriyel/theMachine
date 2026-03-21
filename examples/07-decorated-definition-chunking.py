#!/usr/bin/env python3
"""Example: Python decorated_definition unwrapping in code chunking.

Demonstrates that @decorator-wrapped functions and classes produce proper
L2/L3 chunks with decorator text preserved in content.
"""

from src.indexing.chunker import Chunker
from src.indexing.content_extractor import ContentType, ExtractedFile

PYTHON_CODE = '''\
from dataclasses import dataclass

@dataclass
class Config:
    host: str
    port: int

    def validate(self):
        if not self.host:
            raise ValueError("host required")


@staticmethod
def standalone_helper():
    pass
'''


def main():
    chunker = Chunker()
    f = ExtractedFile(
        path="src/config.py",
        content_type=ContentType.CODE,
        content=PYTHON_CODE,
        size=len(PYTHON_CODE),
    )
    chunks = chunker.chunk(f, repo_id="example-repo", branch="main")

    for chunk in chunks:
        print(f"[{chunk.chunk_type:8s}] symbol={chunk.symbol!r:20s} "
              f"parent_class={chunk.parent_class!r:10s} "
              f"lines={chunk.line_start}-{chunk.line_end}")
        if chunk.chunk_type in ("class", "function"):
            # Show first 2 lines of content to verify decorator preservation
            preview = chunk.content.split("\n")[:2]
            for line in preview:
                print(f"           {line}")
        print()


if __name__ == "__main__":
    main()
