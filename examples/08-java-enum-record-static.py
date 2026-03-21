#!/usr/bin/env python3
"""Example: Java enum, record, and static initializer chunking.

Demonstrates that enum declarations produce L2 chunks, record declarations
produce L2 chunks, and static initializer blocks produce L3 chunks.
"""

from src.indexing.chunker import Chunker
from src.indexing.content_extractor import ContentType, ExtractedFile

JAVA_CODE = '''\
public enum Color {
    RED, GREEN, BLUE;

    public String display() {
        return name().toLowerCase();
    }
}

public record Point(int x, int y) {
    public double distance() {
        return Math.sqrt(x * x + y * y);
    }
}

public class AppConfig {
    static {
        System.out.println("init");
    }

    public void run() {}
}
'''


def main():
    chunker = Chunker()
    f = ExtractedFile(
        path="src/App.java",
        content_type=ContentType.CODE,
        content=JAVA_CODE,
        size=len(JAVA_CODE),
    )
    chunks = chunker.chunk(f, repo_id="example-repo", branch="main")

    for chunk in chunks:
        print(f"[{chunk.chunk_type:8s}] symbol={chunk.symbol!r:20s} "
              f"parent_class={chunk.parent_class!r:12s} "
              f"lines={chunk.line_start}-{chunk.line_end}")


if __name__ == "__main__":
    main()
