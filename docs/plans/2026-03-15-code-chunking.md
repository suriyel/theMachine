# Feature #6 Implementation Plan — Code Chunking with tree-sitter (FR-004)

**Date**: 2026-03-15
**Feature**: Code Chunking with tree-sitter (FR-004)
**Status**: In Progress
**Reference**: Design §4.1, SRS FR-004

## 1. Overview

Implement multi-granularity code chunking using tree-sitter parsers for 6 languages (Java, Python, TypeScript, JavaScript, C, C++). Chunks generated at file-level, class-level, function-level, and symbol-level.

## 2. Design Constraints

- **Architecture**: CodeChunker class delegates to TreeSitterParser
- **Languages**: Java, Python, TypeScript, JavaScript, C, C++
- **Fallback**: Unsupported languages → single file-level text chunk
- **Dependencies**: tree-sitter library, tree-sitter language binaries

## 3. Implementation Tasks

### 3.1 TreeSitterParser Implementation

1. Create `src/indexing/tree_sitter_parser.py`
   - TreeSitterParser class with `parse(source: bytes)` and `query(pattern: str)` methods
   - Language loading per target language
   - Parser selection by file extension mapping

2. Add tree-sitter language dependencies to pyproject.toml:
   - tree-sitter
   - tree-sitter-java
   - tree-sitter-python
   - tree-sitter-typescript
   - tree-sitter-javascript
   - tree-sitter-c
   - tree-sitter-cpp

### 3.2 CodeChunker Implementation

1. Create `src/indexing/chunker.py`
   - CodeChunker class with `chunk(content: RawContent)` method
   - Multi-granularity extraction: file, class, function, symbol
   - `_fallback_file_chunk()` for unsupported languages

2. Implement AST traversal for each language:
   - Java: class declarations, method declarations
   - Python: class definitions, function definitions
   - TypeScript: interfaces, type definitions, function declarations
   - JavaScript: function declarations, class declarations
   - C: function definitions
   - C++: class/struct, function definitions

### 3.3 Data Models

1. Create `src/indexing/models.py`:
   - CodeChunk dataclass: repo_id, file_path, chunk_type (file/class/function/symbol), symbol_name, start_line, end_line, content
   - ChunkType enum

### 3.4 Unit Tests

Write tests for all verification steps:
- Java file with 2 classes × 3 methods → 1 + 2 + 6 = 9 chunks
- Python file with 4 functions + 2 classes → file, class, function chunks with correct line ranges
- Unsupported language (Ruby) → single file-level chunk
- TypeScript with interfaces and type definitions → symbol-level chunks include type info

## 4. Verification Steps Mapping

| Step | Description | Implementation |
|------|-------------|----------------|
| VS-1 | Java 2 classes × 3 methods → 1+2+6 chunks | CodeChunker.chunk() |
| VS-2 | Python 4 functions + 2 classes | CodeChunker.chunk() with Python AST |
| VS-3 | Unsupported language fallback | _fallback_file_chunk() |
| VS-4 | TypeScript interfaces/types | CodeChunker.chunk() with TS parser |

## 5. File List

- `src/indexing/__init__.py`
- `src/indexing/models.py` (CodeChunk, ChunkType)
- `src/indexing/tree_sitter_parser.py` (TreeSitterParser)
- `src/indexing/chunker.py` (CodeChunker)
- `tests/indexing/test_chunker.py` (unit tests)
- `tests/indexing/test_tree_sitter_parser.py` (unit tests)

## 6. Third-Party Dependencies

```
tree-sitter>=0.20.0
tree-sitter-java>=0.20.0
tree-sitter-python>=0.20.0
tree-sitter-typescript>=0.20.0
tree-sitter-javascript>=0.20.0
tree-sitter-c>=0.20.0
tree-sitter-cpp>=0.20.0
```
