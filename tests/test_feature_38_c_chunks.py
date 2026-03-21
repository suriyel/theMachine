"""Tests for Feature #38: C typedef struct + function prototypes + enum.

Feature: #38
feature-38

# tree-sitter is a local library (not an external service)
# The @pytest.mark.real test below uses a real-world C header snippet
# from the Redis project (public domain) to verify end-to-end C chunk detection.
"""

import pytest

from src.indexing.chunker import Chunker, CodeChunk
from src.indexing.content_extractor import ContentType, ExtractedFile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def chunker():
    return Chunker()


def _make_file(
    path: str, content: str, content_type: ContentType = ContentType.CODE
) -> ExtractedFile:
    return ExtractedFile(
        path=path, content_type=content_type, content=content, size=len(content)
    )


def _class_chunks(chunks: list[CodeChunk]) -> list[CodeChunk]:
    return [c for c in chunks if c.chunk_type == "class"]


def _func_chunks(chunks: list[CodeChunk]) -> list[CodeChunk]:
    return [c for c in chunks if c.chunk_type == "function"]


# ---------------------------------------------------------------------------
# Source snippets
# ---------------------------------------------------------------------------

C_TYPEDEF_STRUCT = """\
typedef struct {
    int x;
    int y;
} Point;
"""

C_ENUM = """\
enum Color {
    RED,
    GREEN,
    BLUE
};
"""

C_FIVE_PROTOTYPES = """\
#include <stdio.h>

int add(int a, int b);
int subtract(int a, int b);
int multiply(int a, int b);
int divide(int a, int b);
void print_result(int result);
"""

C_TYPEDEF_STRUCT_WITH_TAG = """\
typedef struct Point {
    int x;
    int y;
} MyPoint;
"""

C_HEADER_WITH_IFNDEF = """\
#ifndef MYHEADER_H
#define MYHEADER_H

typedef struct {
    int x;
    int y;
} Vec2;

int dot(Vec2 a, Vec2 b);
int length(Vec2 v);

#endif
"""

C_COMBINED = """\
#include <stdlib.h>

typedef struct {
    char *name;
    int age;
} Person;

enum Status {
    OK,
    ERROR,
    PENDING
};

int create_person(const char *name, int age);
void destroy_person(Person *p);

int process(Person *p);
"""

C_FUNCTION_DEFINITION = """\
#include <stdio.h>

int add(int a, int b) {
    return a + b;
}
"""


# ---------------------------------------------------------------------------
# T38-01: typedef struct → L2 chunk with symbol='Point'
# ---------------------------------------------------------------------------


class TestT38_01_TypedefStruct:
    def test_typedef_struct_produces_l2_chunk(self, chunker):
        file = _make_file("types.c", C_TYPEDEF_STRUCT)
        chunks = chunker.chunk(file, "repo1", "main")
        class_chunks = _class_chunks(chunks)
        assert len(class_chunks) == 1, (
            f"Expected 1 L2 class chunk for typedef struct, got {len(class_chunks)}: "
            f"{[c.symbol for c in class_chunks]}"
        )

    def test_typedef_struct_symbol_is_typedef_name(self, chunker):
        file = _make_file("types.c", C_TYPEDEF_STRUCT)
        chunks = chunker.chunk(file, "repo1", "main")
        class_chunks = _class_chunks(chunks)
        assert any(c.symbol == "Point" for c in class_chunks), (
            f"Expected symbol='Point', got: {[c.symbol for c in class_chunks]}"
        )

    def test_typedef_struct_chunk_type_is_class(self, chunker):
        file = _make_file("types.c", C_TYPEDEF_STRUCT)
        chunks = chunker.chunk(file, "repo1", "main")
        class_chunks = _class_chunks(chunks)
        point_chunk = next((c for c in class_chunks if c.symbol == "Point"), None)
        assert point_chunk is not None
        assert point_chunk.chunk_type == "class"


# ---------------------------------------------------------------------------
# T38-02: enum_specifier → L2 chunk with symbol='Color'
# ---------------------------------------------------------------------------


class TestT38_02_Enum:
    def test_enum_produces_l2_chunk(self, chunker):
        file = _make_file("colors.c", C_ENUM)
        chunks = chunker.chunk(file, "repo1", "main")
        class_chunks = _class_chunks(chunks)
        assert len(class_chunks) == 1, (
            f"Expected 1 L2 class chunk for enum, got {len(class_chunks)}: "
            f"{[c.symbol for c in class_chunks]}"
        )

    def test_enum_symbol_is_tag_name(self, chunker):
        file = _make_file("colors.c", C_ENUM)
        chunks = chunker.chunk(file, "repo1", "main")
        class_chunks = _class_chunks(chunks)
        assert any(c.symbol == "Color" for c in class_chunks), (
            f"Expected symbol='Color', got: {[c.symbol for c in class_chunks]}"
        )

    def test_enum_chunk_type_is_class(self, chunker):
        file = _make_file("colors.c", C_ENUM)
        chunks = chunker.chunk(file, "repo1", "main")
        class_chunks = _class_chunks(chunks)
        color_chunk = next((c for c in class_chunks if c.symbol == "Color"), None)
        assert color_chunk is not None
        assert color_chunk.chunk_type == "class"


# ---------------------------------------------------------------------------
# T38-03: 5 function prototypes in .h file → 5 L3 chunks
# ---------------------------------------------------------------------------


class TestT38_03_FunctionPrototypes:
    def test_five_prototypes_produce_five_l3_chunks(self, chunker):
        file = _make_file("math.h", C_FIVE_PROTOTYPES)
        chunks = chunker.chunk(file, "repo1", "main")
        func_chunks = _func_chunks(chunks)
        assert len(func_chunks) == 5, (
            f"Expected 5 L3 function chunks for 5 prototypes, got {len(func_chunks)}: "
            f"{[c.symbol for c in func_chunks]}"
        )

    def test_prototype_symbols_correct(self, chunker):
        file = _make_file("math.h", C_FIVE_PROTOTYPES)
        chunks = chunker.chunk(file, "repo1", "main")
        func_chunks = _func_chunks(chunks)
        symbols = {c.symbol for c in func_chunks}
        assert "add" in symbols
        assert "subtract" in symbols
        assert "multiply" in symbols
        assert "divide" in symbols
        assert "print_result" in symbols

    def test_prototype_chunk_type_is_function(self, chunker):
        file = _make_file("math.h", C_FIVE_PROTOTYPES)
        chunks = chunker.chunk(file, "repo1", "main")
        func_chunks = _func_chunks(chunks)
        for chunk in func_chunks:
            assert chunk.chunk_type == "function", (
                f"Prototype chunk {chunk.symbol!r} has type={chunk.chunk_type!r}, expected 'function'"
            )

    def test_prototype_content_is_declaration_text(self, chunker):
        file = _make_file("math.h", C_FIVE_PROTOTYPES)
        chunks = chunker.chunk(file, "repo1", "main")
        func_chunks = _func_chunks(chunks)
        add_chunk = next((c for c in func_chunks if c.symbol == "add"), None)
        assert add_chunk is not None
        # Content should contain the declaration text
        assert "add" in add_chunk.content
        assert "int" in add_chunk.content


# ---------------------------------------------------------------------------
# T38-04: typedef struct inside #ifndef guard → L2 chunk detected
# ---------------------------------------------------------------------------


class TestT38_04_TypedefStructInsideIfndef:
    def test_typedef_inside_ifndef_produces_l2_chunk(self, chunker):
        file = _make_file("vec2.h", C_HEADER_WITH_IFNDEF)
        chunks = chunker.chunk(file, "repo1", "main")
        class_chunks = _class_chunks(chunks)
        assert any(c.symbol == "Vec2" for c in class_chunks), (
            f"Expected symbol='Vec2' inside #ifndef guard, got: "
            f"{[c.symbol for c in class_chunks]}"
        )


# ---------------------------------------------------------------------------
# T38-05: function prototypes inside #ifndef guard → L3 chunks detected
# ---------------------------------------------------------------------------


class TestT38_05_PrototypesInsideIfndef:
    def test_prototypes_inside_ifndef_produce_l3_chunks(self, chunker):
        file = _make_file("vec2.h", C_HEADER_WITH_IFNDEF)
        chunks = chunker.chunk(file, "repo1", "main")
        func_chunks = _func_chunks(chunks)
        assert len(func_chunks) == 2, (
            f"Expected 2 L3 function chunks inside #ifndef, got {len(func_chunks)}: "
            f"{[c.symbol for c in func_chunks]}"
        )

    def test_prototype_symbols_inside_ifndef(self, chunker):
        file = _make_file("vec2.h", C_HEADER_WITH_IFNDEF)
        chunks = chunker.chunk(file, "repo1", "main")
        func_chunks = _func_chunks(chunks)
        symbols = {c.symbol for c in func_chunks}
        assert "dot" in symbols
        assert "length" in symbols


# ---------------------------------------------------------------------------
# T38-06: combined typedef + enum + prototypes
# ---------------------------------------------------------------------------


class TestT38_06_Combined:
    def test_combined_class_chunks(self, chunker):
        file = _make_file("combined.c", C_COMBINED)
        chunks = chunker.chunk(file, "repo1", "main")
        class_chunks = _class_chunks(chunks)
        symbols = {c.symbol for c in class_chunks}
        assert "Person" in symbols, f"Expected 'Person' in class chunks, got: {symbols}"
        assert "Status" in symbols, f"Expected 'Status' in class chunks, got: {symbols}"

    def test_combined_function_chunks(self, chunker):
        file = _make_file("combined.c", C_COMBINED)
        chunks = chunker.chunk(file, "repo1", "main")
        func_chunks = _func_chunks(chunks)
        symbols = {c.symbol for c in func_chunks}
        assert "create_person" in symbols, (
            f"Expected 'create_person' in func chunks, got: {symbols}"
        )
        assert "destroy_person" in symbols, (
            f"Expected 'destroy_person' in func chunks, got: {symbols}"
        )
        assert "process" in symbols, (
            f"Expected 'process' in func chunks, got: {symbols}"
        )

    def test_combined_total_chunk_count(self, chunker):
        file = _make_file("combined.c", C_COMBINED)
        chunks = chunker.chunk(file, "repo1", "main")
        # 1 file + 2 class (Person, Status) + 3 function (create_person, destroy_person, process)
        assert len(chunks) >= 6, (
            f"Expected at least 6 chunks total, got {len(chunks)}: "
            f"{[(c.chunk_type, c.symbol) for c in chunks]}"
        )


# ---------------------------------------------------------------------------
# T38-07: function_definition still works (regression)
# ---------------------------------------------------------------------------


class TestT38_07_FunctionDefinitionRegression:
    def test_function_definition_still_produces_l3_chunk(self, chunker):
        file = _make_file("add.c", C_FUNCTION_DEFINITION)
        chunks = chunker.chunk(file, "repo1", "main")
        func_chunks = _func_chunks(chunks)
        assert len(func_chunks) == 1, (
            f"Expected 1 L3 function chunk for function_definition, got {len(func_chunks)}"
        )
        assert func_chunks[0].symbol == "add"

    def test_function_definition_not_duplicated(self, chunker):
        """A function_definition should not also be treated as a prototype."""
        file = _make_file("add.c", C_FUNCTION_DEFINITION)
        chunks = chunker.chunk(file, "repo1", "main")
        func_chunks = _func_chunks(chunks)
        # Should be exactly 1, not 2
        assert len(func_chunks) == 1


# ---------------------------------------------------------------------------
# T38-08: typedef struct — symbol uses typedef alias, not struct tag
# ---------------------------------------------------------------------------


class TestT38_08_TypedefAliasNotStructTag:
    def test_typedef_alias_used_as_symbol(self, chunker):
        """When typedef has different alias from struct tag, use alias."""
        file = _make_file("point.c", C_TYPEDEF_STRUCT_WITH_TAG)
        chunks = chunker.chunk(file, "repo1", "main")
        class_chunks = _class_chunks(chunks)
        symbols = {c.symbol for c in class_chunks}
        assert "MyPoint" in symbols, (
            f"Expected typedef alias 'MyPoint' as symbol, got: {symbols}"
        )

    def test_struct_tag_not_used_as_symbol(self, chunker):
        """The struct tag 'Point' should not become the symbol when typedef alias differs."""
        file = _make_file("point.c", C_TYPEDEF_STRUCT_WITH_TAG)
        chunks = chunker.chunk(file, "repo1", "main")
        class_chunks = _class_chunks(chunks)
        symbols = {c.symbol for c in class_chunks}
        # 'Point' (struct tag) should NOT be the symbol; 'MyPoint' (typedef alias) should
        # We allow at most one class chunk with symbol='MyPoint'
        assert len(class_chunks) == 1, (
            f"Expected exactly 1 class chunk, got {len(class_chunks)}: {symbols}"
        )
        assert class_chunks[0].symbol == "MyPoint"


# ---------------------------------------------------------------------------
# Real test: verifies feature #38 on a real-world C header (Redis adlist.h)
# feature-38
# ---------------------------------------------------------------------------

# Verbatim excerpt from redis/redis src/adlist.h (BSD licensed)
REDIS_ADLIST_EXCERPT = """\
#ifndef __ADLIST_H__
#define __ADLIST_H__

typedef struct listNode {
    struct listNode *prev;
    struct listNode *next;
    void *value;
} listNode;

typedef struct listIter {
    listNode *next;
    int direction;
} listIter;

/* Functions implemented as macros */
#define listLength(l) ((l)->len)

int listAddNodeHead(void *value);
int listAddNodeTail(void *value);

#endif /* __ADLIST_H__ */
"""


@pytest.mark.real
def test_real_redis_adlist_h_typedef_structs(chunker):
    """feature-38: Real-world Redis adlist.h typedef structs → L2 class chunks."""
    file = _make_file("src/adlist.h", REDIS_ADLIST_EXCERPT)
    chunks = chunker.chunk(file, "redis", "unstable")
    class_chunks = _class_chunks(chunks)
    symbols = {c.symbol for c in class_chunks}
    assert "listNode" in symbols, (
        f"feature-38: Expected 'listNode' L2 chunk from Redis adlist.h, got: {symbols}"
    )
    assert "listIter" in symbols, (
        f"feature-38: Expected 'listIter' L2 chunk from Redis adlist.h, got: {symbols}"
    )


@pytest.mark.real
def test_real_redis_adlist_h_function_prototypes(chunker):
    """feature-38: Real-world Redis adlist.h prototypes → L3 function chunks."""
    file = _make_file("src/adlist.h", REDIS_ADLIST_EXCERPT)
    chunks = chunker.chunk(file, "redis", "unstable")
    func_chunks = _func_chunks(chunks)
    symbols = {c.symbol for c in func_chunks}
    assert "listAddNodeHead" in symbols, (
        f"feature-38: Expected 'listAddNodeHead' L3 chunk from Redis adlist.h, got: {symbols}"
    )
    assert "listAddNodeTail" in symbols, (
        f"feature-38: Expected 'listAddNodeTail' L3 chunk from Redis adlist.h, got: {symbols}"
    )
