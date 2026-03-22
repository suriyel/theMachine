#!/usr/bin/env python3
"""Example: C++ namespace + template unwrapping (Feature #39)

Demonstrates how the Chunker unwraps C++ namespace and template constructs:
- namespace_definition → recurse into declaration_list body
- Nested namespaces → recursive unwrapping
- C++17 namespace a::b::c syntax
- template<typename T> class → L2 chunk (single-level unwrap)
- template<typename T> function → L3 chunk
- Namespace + template combined
"""

from src.indexing.chunker import Chunker
from src.indexing.content_extractor import ExtractedFile

CPP_SOURCE = """\
#include <vector>

namespace mylib {
  namespace detail {
    template<typename T>
    class SmallVector {
    public:
      void push_back(const T& val) {}
      void pop_back() {}
    private:
      T data_[64];
    };
  }

  template<typename K, typename V>
  V lookup(const K& key) { return V(); }

  class Config {
  public:
    void load(const char* path) {}
  };
}
"""


def main():
    chunker = Chunker()
    f = ExtractedFile(
        path="src/mylib.hpp",
        content=CPP_SOURCE,
        content_type="code",
        size=len(CPP_SOURCE),
    )
    chunks = chunker.chunk(f, repo_id="example-39", branch="main")

    print(f"Total chunks: {len(chunks)}\n")

    for c in chunks:
        indent = "  " if c.chunk_type != "file" else ""
        parent = f" (parent: {c.parent_class})" if c.parent_class else ""
        print(f"{indent}[{c.chunk_type:8s}] {c.symbol or '(file)'}{parent}")
        if c.chunk_type == "file":
            print(f"  top_level_symbols: {c.top_level_symbols}")
            print()

    # Verify expected chunks
    classes = [c for c in chunks if c.chunk_type == "class"]
    funcs = [c for c in chunks if c.chunk_type == "function"]

    class_names = {c.symbol for c in classes}
    func_names = {c.symbol for c in funcs}

    assert "SmallVector" in class_names, "SmallVector L2 missing"
    assert "Config" in class_names, "Config L2 missing"
    assert "push_back" in func_names, "push_back L3 missing"
    assert "pop_back" in func_names, "pop_back L3 missing"
    assert "lookup" in func_names, "lookup L3 missing"
    assert "load" in func_names, "load L3 missing"

    print("\nAll assertions passed!")


if __name__ == "__main__":
    main()
