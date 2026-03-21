#!/usr/bin/env python3
"""Example: TypeScript enum, namespace, and decorator chunking.

Demonstrates Feature #37 — detecting enum declarations as L2 chunks,
unwrapping namespace/module blocks to find classes and functions,
and handling decorator-wrapped classes.
"""

from src.indexing.chunker import Chunker
from src.indexing.content_extractor import ContentType, ExtractedFile

TS_CODE = """\
enum Status { Active, Inactive, Pending }

namespace Utils {
  class StringHelper {
    capitalize(s: string): string { return s.toUpperCase(); }
  }

  function trim(s: string): string { return s.trim(); }
}

@Injectable()
class UserService {
  getUser(id: number) { return { id }; }
}
"""


def main():
    chunker = Chunker()
    file = ExtractedFile(
        path="src/app.ts",
        content_type=ContentType.CODE,
        content=TS_CODE,
        size=len(TS_CODE),
    )
    chunks = chunker.chunk(file, repo_id="demo-repo", branch="main")

    print("=== L2 Class Chunks ===")
    for c in chunks:
        if c.chunk_type == "class":
            print(f"  {c.symbol} (lines {c.line_start}-{c.line_end})")

    print("\n=== L3 Function Chunks ===")
    for c in chunks:
        if c.chunk_type == "function":
            parent = f" [parent: {c.parent_class}]" if c.parent_class else ""
            print(f"  {c.symbol}{parent} (lines {c.line_start}-{c.line_end})")

    print(f"\nTotal chunks: {len(chunks)}")


if __name__ == "__main__":
    main()
