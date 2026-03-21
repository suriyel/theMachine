#!/usr/bin/env python3
"""Example: JavaScript prototype-assigned function + require() import chunking.

Demonstrates Feature #36 — detecting prototype-assigned functions
(obj.method = function/arrow) and CommonJS require() imports in JavaScript files.
"""

from src.indexing.chunker import Chunker
from src.indexing.content_extractor import ContentType, ExtractedFile

JS_CODE = """\
var express = require('express');
const path = require('path');
let _ = require('lodash');

class Router {
    get(url) {
        return url;
    }
}

function formatDate(date) {
    return date.toISOString();
}

res.status = function(code) {
    return code;
};

obj.handler = (req, res) => {
    return res.send('OK');
};
"""


def main():
    chunker = Chunker()
    file = ExtractedFile(
        path="src/app.js",
        content_type=ContentType.CODE,
        content=JS_CODE,
        size=len(JS_CODE),
    )
    chunks = chunker.chunk(file, repo_id="demo-repo", branch="main")

    print("=== L1 File Chunk ===")
    l1 = [c for c in chunks if c.chunk_type == "file"][0]
    print(f"  Imports: {l1.imports}")
    print(f"  Top-level symbols: {l1.top_level_symbols}")

    print("\n=== L2 Class Chunks ===")
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
