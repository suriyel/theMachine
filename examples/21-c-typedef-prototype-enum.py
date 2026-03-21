#!/usr/bin/env python3
"""Example: C typedef struct + function prototypes + enum chunking (Feature #38)

Demonstrates how the Chunker detects C-specific constructs:
- typedef struct → L2 class chunk
- function prototypes (no body) → L3 function chunks
- enum declarations → L2 class chunks
- All of the above inside #ifndef header guards
"""

import tree_sitter_c as tsc
import tree_sitter as ts

from src.indexing.chunker import Chunker
from src.indexing.content_extractor import ExtractedFile

C_HEADER = """\
#ifndef POINT_H
#define POINT_H

typedef struct {
    int x;
    int y;
} Point;

enum Color { RED, GREEN, BLUE };

Point* point_create(int x, int y);
void point_destroy(Point* p);
double point_distance(const Point* a, const Point* b);

#endif /* POINT_H */
"""


def main():
    # Parse C code with tree-sitter
    language = ts.Language(tsc.language())
    parser = ts.Parser(language)
    tree = parser.parse(C_HEADER.encode("utf-8"))

    file = ExtractedFile(path="include/point.h", content=C_HEADER, file_type="code")
    chunker = Chunker()

    # L1 file chunk
    file_chunk = chunker.extract_file_chunk(tree, file, "demo-repo", "main", "c")
    print(f"L1 File: {file_chunk.file_path}")
    print(f"  Symbols: {file_chunk.top_level_symbols}")
    print()

    # L2 class chunks (typedef struct + enum)
    class_chunks = chunker.extract_class_chunks(tree, file, "demo-repo", "main", "c")
    print(f"L2 Class chunks ({len(class_chunks)}):")
    for ch in class_chunks:
        print(f"  - symbol={ch.symbol!r}, type={ch.chunk_type}")

    print()

    # L3 function chunks (prototypes)
    func_chunks = chunker.extract_function_chunks(tree, file, "demo-repo", "main", "c")
    print(f"L3 Function chunks ({len(func_chunks)}):")
    for ch in func_chunks:
        print(f"  - symbol={ch.symbol!r}, content={ch.content.strip()!r}")


if __name__ == "__main__":
    main()
