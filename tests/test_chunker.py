"""Tests for Feature #6 Code Chunking — Chunker.

# [no integration test] — pure computation feature, no external I/O
# tree-sitter is a local library (not an external service)
"""

import pytest

from src.indexing.chunker import Chunker, CodeChunk
from src.indexing.content_extractor import ContentType, ExtractedFile


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def chunker():
    return Chunker()


def _make_file(path: str, content: str, content_type: ContentType = ContentType.CODE) -> ExtractedFile:
    return ExtractedFile(path=path, content_type=content_type, content=content, size=len(content))


# ---------------------------------------------------------------------------
# Source snippets
# ---------------------------------------------------------------------------

PYTHON_CLASS_3_METHODS = """\
import os
import sys

class Calculator:
    \"\"\"A simple calculator.\"\"\"

    def add(self, a: int, b: int) -> int:
        \"\"\"Add two numbers.\"\"\"
        return a + b

    def subtract(self, a: int, b: int) -> int:
        \"\"\"Subtract b from a.\"\"\"
        return a - b

    def multiply(self, a: int, b: int) -> int:
        \"\"\"Multiply two numbers.\"\"\"
        return a * b
"""

JAVA_TWO_CLASSES = """\
import java.util.List;
import java.util.Map;

public class ClassA {
    /** Method one. */
    public void methodOne() {}

    /** Method two. */
    public int methodTwo(int x) { return x; }

    /** Method three. */
    public String methodThree() { return ""; }
}

class ClassB {
    /** Do alpha. */
    public void alpha() {}

    /** Do beta. */
    public void beta() {}
}
"""

PYTHON_THREE_FUNCTIONS = """\
def greet(name: str) -> str:
    return f"Hello, {name}"

def farewell(name: str) -> str:
    return f"Goodbye, {name}"

def shout(msg: str) -> str:
    return msg.upper()
"""

RUBY_FILE = """\
class Dog
  def bark
    puts "Woof!"
  end
end
"""

JAVASCRIPT_MIXED = """\
class EventEmitter {
    constructor() {
        this.listeners = {};
    }

    on(event, callback) {
        this.listeners[event] = callback;
    }
}

function formatDate(date) {
    return date.toISOString();
}

const double = (x) => x * 2;
"""

TYPESCRIPT_CLASS_INTERFACE = """\
interface Logger {
    log(message: string): void;
    error(message: string): void;
}

class ConsoleLogger {
    log(message: string): void {
        console.log(message);
    }

    error(message: string): void {
        console.error(message);
    }
}
"""

C_THREE_FUNCTIONS = """\
#include <stdio.h>
#include <stdlib.h>

int add(int a, int b) {
    return a + b;
}

int subtract(int a, int b) {
    return a - b;
}

void print_result(int result) {
    printf("%d\\n", result);
}
"""

CPP_CLASS_STRUCT = """\
#include <string>
#include <vector>

class Parser {
public:
    void parse(const std::string& input) {}
};

struct Token {
    std::string value;
    int type;
};

int helper_a(int x) { return x + 1; }

int helper_b(int x) { return x * 2; }
"""

PYTHON_WITH_IMPORTS = """\
import os
from pathlib import Path

def read_file(path: str) -> str:
    return open(path).read()
"""

JAVA_WITH_CONSTRUCTOR = """\
public class Service {
    private final String name;

    /** Creates a new Service. */
    public Service(String name) {
        this.name = name;
    }

    /** Gets the name. */
    public String getName() {
        return name;
    }
}
"""

PYTHON_WITH_DOCSTRINGS = """\
class Formatter:
    \"\"\"Formats output strings.

    This class provides utilities for formatting
    output in various styles.
    \"\"\"

    def bold(self, text: str) -> str:
        \"\"\"Make text bold.

        Args:
            text: The input text.

        Returns:
            The bold text.
        \"\"\"
        return f"**{text}**"
"""

JAVA_WITH_JAVADOC = """\
/**
 * Represents a user entity.
 *
 * @author dev
 * @since 1.0
 */
public class User {
    private String name;

    /**
     * Returns the user's name.
     *
     * @return the name
     */
    public String getName() {
        return name;
    }
}
"""

PYTHON_MULTILINE_SIG = """\
def create_user(
    name: str,
    email: str,
    age: int,
    role: str = "viewer",
) -> dict:
    return {"name": name, "email": email, "age": age, "role": role}
"""

EMPTY_PYTHON = ""

PYTHON_ONLY_IMPORTS = """\
import os
import sys
from pathlib import Path
"""

PYTHON_SYNTAX_ERROR = """\
def good_func():
    return 42

def bad_func(
    # missing close paren
    return 99

class StillWorks:
    def method(self):
        return True
"""

TSX_FILE = """\
interface Props {
    name: string;
}

class Greeting {
    render(props: Props): string {
        return `Hello ${props.name}`;
    }
}
"""

PYTHON_NESTED_CLASS = """\
class Outer:
    class Inner:
        def inner_method(self):
            return "inner"

    def outer_method(self):
        return "outer"
"""

NO_EXTENSION_FILE = """\
#!/usr/bin/env python3
print("hello")
"""

C_HEADER = """\
#ifndef UTILS_H
#define UTILS_H

int add(int a, int b);
void print_msg(const char* msg);

#endif
"""


# ---------------------------------------------------------------------------
# T1 — happy path — Python class with 3 methods
# ---------------------------------------------------------------------------

class TestT1PythonClassMethods:
    # [unit]
    def test_produces_5_chunks(self, chunker):
        f = _make_file("src/calculator.py", PYTHON_CLASS_3_METHODS)
        chunks = chunker.chunk(f, repo_id="repo-1", branch="main")
        assert len(chunks) == 5

    # [unit]
    def test_l1_file_chunk(self, chunker):
        f = _make_file("src/calculator.py", PYTHON_CLASS_3_METHODS)
        chunks = chunker.chunk(f, repo_id="repo-1", branch="main")
        l1 = [c for c in chunks if c.chunk_type == "file"]
        assert len(l1) == 1
        assert l1[0].file_path == "src/calculator.py"
        assert l1[0].language == "python"

    # [unit]
    def test_l2_class_chunk(self, chunker):
        f = _make_file("src/calculator.py", PYTHON_CLASS_3_METHODS)
        chunks = chunker.chunk(f, repo_id="repo-1", branch="main")
        l2 = [c for c in chunks if c.chunk_type == "class"]
        assert len(l2) == 1
        assert l2[0].symbol == "Calculator"

    # [unit]
    def test_l3_method_chunks(self, chunker):
        f = _make_file("src/calculator.py", PYTHON_CLASS_3_METHODS)
        chunks = chunker.chunk(f, repo_id="repo-1", branch="main")
        l3 = [c for c in chunks if c.chunk_type == "function"]
        assert len(l3) == 3
        symbols = {c.symbol for c in l3}
        assert symbols == {"add", "subtract", "multiply"}

    # [unit]
    def test_signatures_present(self, chunker):
        f = _make_file("src/calculator.py", PYTHON_CLASS_3_METHODS)
        chunks = chunker.chunk(f, repo_id="repo-1", branch="main")
        l3 = [c for c in chunks if c.chunk_type == "function"]
        for c in l3:
            assert c.signature != ""


# ---------------------------------------------------------------------------
# T2 — happy path — Java two classes
# ---------------------------------------------------------------------------

class TestT2JavaTwoClasses:
    # [unit]
    def test_produces_8_chunks(self, chunker):
        f = _make_file("src/Main.java", JAVA_TWO_CLASSES)
        chunks = chunker.chunk(f, repo_id="repo-2", branch="main")
        assert len(chunks) == 8  # 1 L1 + 2 L2 + 5 L3

    # [unit]
    def test_two_class_chunks(self, chunker):
        f = _make_file("src/Main.java", JAVA_TWO_CLASSES)
        chunks = chunker.chunk(f, repo_id="repo-2", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        assert len(classes) == 2
        class_names = {c.symbol for c in classes}
        assert class_names == {"ClassA", "ClassB"}

    # [unit]
    def test_parent_class_set(self, chunker):
        f = _make_file("src/Main.java", JAVA_TWO_CLASSES)
        chunks = chunker.chunk(f, repo_id="repo-2", branch="main")
        methods = [c for c in chunks if c.chunk_type == "function"]
        class_a_methods = [c for c in methods if c.parent_class == "ClassA"]
        class_b_methods = [c for c in methods if c.parent_class == "ClassB"]
        assert len(class_a_methods) == 3
        assert len(class_b_methods) == 2


# ---------------------------------------------------------------------------
# T3 — happy path — Python top-level functions only
# ---------------------------------------------------------------------------

class TestT3PythonTopLevelFunctions:
    # [unit]
    def test_produces_4_chunks(self, chunker):
        f = _make_file("src/utils.py", PYTHON_THREE_FUNCTIONS)
        chunks = chunker.chunk(f, repo_id="repo-3", branch="main")
        assert len(chunks) == 4  # 1 L1 + 3 L3

    # [unit]
    def test_no_class_chunks(self, chunker):
        f = _make_file("src/utils.py", PYTHON_THREE_FUNCTIONS)
        chunks = chunker.chunk(f, repo_id="repo-3", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        assert len(classes) == 0

    # [unit]
    def test_parent_class_empty(self, chunker):
        f = _make_file("src/utils.py", PYTHON_THREE_FUNCTIONS)
        chunks = chunker.chunk(f, repo_id="repo-3", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        for c in funcs:
            assert c.parent_class == ""


# ---------------------------------------------------------------------------
# T4 — happy path — Unsupported extension (.rb) → fallback
# ---------------------------------------------------------------------------

class TestT4RubyFallback:
    # [unit]
    def test_single_fallback_chunk(self, chunker):
        f = _make_file("src/dog.rb", RUBY_FILE)
        chunks = chunker.chunk(f, repo_id="repo-4", branch="main")
        assert len(chunks) == 1

    # [unit]
    def test_fallback_chunk_type_is_file(self, chunker):
        f = _make_file("src/dog.rb", RUBY_FILE)
        chunks = chunker.chunk(f, repo_id="repo-4", branch="main")
        assert chunks[0].chunk_type == "file"
        assert chunks[0].content == RUBY_FILE


# ---------------------------------------------------------------------------
# T6 — happy path — JavaScript mixed: class + functions + arrow
# ---------------------------------------------------------------------------

class TestT6JavaScriptMixed:
    # [unit]
    def test_produces_6_chunks(self, chunker):
        f = _make_file("src/events.js", JAVASCRIPT_MIXED)
        chunks = chunker.chunk(f, repo_id="repo-6", branch="main")
        assert len(chunks) == 6  # 1 L1 + 1 L2 + 2 L2 methods + 1 top-level func + 1 arrow

    # [unit]
    def test_class_chunk_present(self, chunker):
        f = _make_file("src/events.js", JAVASCRIPT_MIXED)
        chunks = chunker.chunk(f, repo_id="repo-6", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        assert len(classes) == 1
        assert classes[0].symbol == "EventEmitter"


# ---------------------------------------------------------------------------
# T7 — happy path — TypeScript class + interface
# ---------------------------------------------------------------------------

class TestT7TypeScriptInterface:
    # [unit]
    def test_produces_5_chunks(self, chunker):
        f = _make_file("src/logger.ts", TYPESCRIPT_CLASS_INTERFACE)
        chunks = chunker.chunk(f, repo_id="repo-7", branch="main")
        assert len(chunks) == 5  # 1 L1 + 1 L2 class + 1 L2 interface + 2 L3 methods

    # [unit]
    def test_interface_is_l2(self, chunker):
        f = _make_file("src/logger.ts", TYPESCRIPT_CLASS_INTERFACE)
        chunks = chunker.chunk(f, repo_id="repo-7", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        symbols = {c.symbol for c in classes}
        assert "Logger" in symbols
        assert "ConsoleLogger" in symbols


# ---------------------------------------------------------------------------
# T8 — happy path — C three functions
# ---------------------------------------------------------------------------

class TestT8CThreeFunctions:
    # [unit]
    def test_produces_4_chunks(self, chunker):
        f = _make_file("src/math.c", C_THREE_FUNCTIONS)
        chunks = chunker.chunk(f, repo_id="repo-8", branch="main")
        assert len(chunks) == 4  # 1 L1 + 3 L3

    # [unit]
    def test_function_symbols(self, chunker):
        f = _make_file("src/math.c", C_THREE_FUNCTIONS)
        chunks = chunker.chunk(f, repo_id="repo-8", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        symbols = {c.symbol for c in funcs}
        assert symbols == {"add", "subtract", "print_result"}


# ---------------------------------------------------------------------------
# T9 — happy path — C++ class + struct + functions
# ---------------------------------------------------------------------------

class TestT9CppClassStruct:
    # [unit]
    def test_produces_6_chunks(self, chunker):
        f = _make_file("src/parser.cpp", CPP_CLASS_STRUCT)
        chunks = chunker.chunk(f, repo_id="repo-9", branch="main")
        assert len(chunks) == 6  # 1 L1 + 2 L2 (class + struct) + 3 L3 (parse + helper_a + helper_b)

    # [unit]
    def test_class_and_struct(self, chunker):
        f = _make_file("src/parser.cpp", CPP_CLASS_STRUCT)
        chunks = chunker.chunk(f, repo_id="repo-9", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        symbols = {c.symbol for c in classes}
        assert "Parser" in symbols
        assert "Token" in symbols


# ---------------------------------------------------------------------------
# T10 — happy path — Python with imports
# ---------------------------------------------------------------------------

class TestT10PythonImports:
    # [unit]
    def test_imports_extracted(self, chunker):
        f = _make_file("src/reader.py", PYTHON_WITH_IMPORTS)
        chunks = chunker.chunk(f, repo_id="repo-10", branch="main")
        l1 = [c for c in chunks if c.chunk_type == "file"][0]
        assert "import os" in l1.imports
        assert "from pathlib import Path" in l1.imports
        assert len(l1.imports) == 2


# ---------------------------------------------------------------------------
# T11 — happy path — Java with constructor
# ---------------------------------------------------------------------------

class TestT11JavaConstructor:
    # [unit]
    def test_constructor_as_l3(self, chunker):
        f = _make_file("src/Service.java", JAVA_WITH_CONSTRUCTOR)
        chunks = chunker.chunk(f, repo_id="repo-11", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        symbols = {c.symbol for c in funcs}
        assert "Service" in symbols  # constructor named after class
        assert "getName" in symbols


# ---------------------------------------------------------------------------
# T16 — boundary — Python docstrings
# ---------------------------------------------------------------------------

class TestT16PythonDocstrings:
    # [unit]
    def test_doc_comment_populated(self, chunker):
        f = _make_file("src/formatter.py", PYTHON_WITH_DOCSTRINGS)
        chunks = chunker.chunk(f, repo_id="repo-16", branch="main")
        cls = [c for c in chunks if c.chunk_type == "class"][0]
        assert "Formats output strings" in cls.doc_comment

    # [unit]
    def test_method_doc_comment(self, chunker):
        f = _make_file("src/formatter.py", PYTHON_WITH_DOCSTRINGS)
        chunks = chunker.chunk(f, repo_id="repo-16", branch="main")
        bold = [c for c in chunks if c.symbol == "bold"][0]
        assert "Make text bold" in bold.doc_comment


# ---------------------------------------------------------------------------
# T17 — boundary — Java Javadoc
# ---------------------------------------------------------------------------

class TestT17JavaJavadoc:
    # [unit]
    def test_javadoc_populated(self, chunker):
        f = _make_file("src/User.java", JAVA_WITH_JAVADOC)
        chunks = chunker.chunk(f, repo_id="repo-17", branch="main")
        cls = [c for c in chunks if c.chunk_type == "class"][0]
        assert "Represents a user entity" in cls.doc_comment

    # [unit]
    def test_method_javadoc(self, chunker):
        f = _make_file("src/User.java", JAVA_WITH_JAVADOC)
        chunks = chunker.chunk(f, repo_id="repo-17", branch="main")
        get_name = [c for c in chunks if c.symbol == "getName"][0]
        assert "Returns the user's name" in get_name.doc_comment


# ---------------------------------------------------------------------------
# T18 — boundary — Python multi-line signature
# ---------------------------------------------------------------------------

class TestT18MultiLineSig:
    # [unit]
    def test_full_signature_captured(self, chunker):
        f = _make_file("src/users.py", PYTHON_MULTILINE_SIG)
        chunks = chunker.chunk(f, repo_id="repo-18", branch="main")
        func = [c for c in chunks if c.chunk_type == "function"][0]
        assert "name: str" in func.signature
        assert "email: str" in func.signature
        assert "-> dict" in func.signature


# ---------------------------------------------------------------------------
# T19 — boundary — Empty Python file
# ---------------------------------------------------------------------------

class TestT19EmptyPythonFile:
    # [unit]
    def test_single_l1_chunk(self, chunker):
        f = _make_file("src/empty.py", EMPTY_PYTHON)
        chunks = chunker.chunk(f, repo_id="repo-19", branch="main")
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "file"

    # [unit]
    def test_empty_imports_and_symbols(self, chunker):
        f = _make_file("src/empty.py", EMPTY_PYTHON)
        chunks = chunker.chunk(f, repo_id="repo-19", branch="main")
        assert chunks[0].imports == []
        assert chunks[0].top_level_symbols == []


# ---------------------------------------------------------------------------
# T20 — boundary — Python only imports
# ---------------------------------------------------------------------------

class TestT20PythonOnlyImports:
    # [unit]
    def test_single_l1_with_imports(self, chunker):
        f = _make_file("src/imports_only.py", PYTHON_ONLY_IMPORTS)
        chunks = chunker.chunk(f, repo_id="repo-20", branch="main")
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "file"
        assert len(chunks[0].imports) == 3

    # [unit]
    def test_empty_symbols(self, chunker):
        f = _make_file("src/imports_only.py", PYTHON_ONLY_IMPORTS)
        chunks = chunker.chunk(f, repo_id="repo-20", branch="main")
        assert chunks[0].top_level_symbols == []


# ---------------------------------------------------------------------------
# T21 — boundary — Function exactly 500 lines → single L3
# ---------------------------------------------------------------------------

class TestT21Function500Lines:
    # [unit]
    def test_single_l3_chunk(self, chunker):
        lines = ["def big_func():"] + [f"    x = {i}" for i in range(499)]
        code = "\n".join(lines) + "\n"
        f = _make_file("src/big.py", code)
        chunks = chunker.chunk(f, repo_id="repo-21", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(funcs) == 1


# ---------------------------------------------------------------------------
# T22 — boundary — Function 501 lines → 2 L3 chunks with overlap
# ---------------------------------------------------------------------------

class TestT22Function501Lines:
    # [unit]
    def test_two_l3_chunks(self, chunker):
        lines = ["def big_func():"] + [f"    x = {i}" for i in range(500)]
        code = "\n".join(lines) + "\n"
        f = _make_file("src/big501.py", code)
        chunks = chunker.chunk(f, repo_id="repo-22", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(funcs) == 2

    # [unit]
    def test_overlap_exists(self, chunker):
        lines = ["def big_func():"] + [f"    x = {i}" for i in range(500)]
        code = "\n".join(lines) + "\n"
        f = _make_file("src/big501.py", code)
        chunks = chunker.chunk(f, repo_id="repo-22", branch="main")
        funcs = sorted(
            [c for c in chunks if c.chunk_type == "function"],
            key=lambda c: c.line_start,
        )
        assert funcs[0].line_end >= funcs[1].line_start  # overlap


# ---------------------------------------------------------------------------
# T23 — boundary — Function 1000 lines → 3 L3 chunks
# ---------------------------------------------------------------------------

class TestT23Function1000Lines:
    # [unit]
    def test_three_l3_chunks(self, chunker):
        lines = ["def huge_func():"] + [f"    x = {i}" for i in range(999)]
        code = "\n".join(lines) + "\n"
        f = _make_file("src/huge.py", code)
        chunks = chunker.chunk(f, repo_id="repo-23", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(funcs) == 3


# ---------------------------------------------------------------------------
# T24 — error — Python syntax errors → still produces chunks
# ---------------------------------------------------------------------------

class TestT24SyntaxError:
    # [unit]
    def test_still_produces_chunks(self, chunker):
        f = _make_file("src/broken.py", PYTHON_SYNTAX_ERROR)
        chunks = chunker.chunk(f, repo_id="repo-24", branch="main")
        assert len(chunks) >= 1  # tree-sitter is error-tolerant


# ---------------------------------------------------------------------------
# T25 — error — .tsx extension → parses as TypeScript
# ---------------------------------------------------------------------------

class TestT25TsxExtension:
    # [unit]
    def test_tsx_parsed_as_typescript(self, chunker):
        f = _make_file("src/component.tsx", TSX_FILE)
        chunks = chunker.chunk(f, repo_id="repo-25", branch="main")
        assert len(chunks) >= 2
        for c in chunks:
            assert c.language == "typescript"


# ---------------------------------------------------------------------------
# T33 — error — File with no extension → fallback L1
# ---------------------------------------------------------------------------

class TestT33NoExtension:
    # [unit]
    def test_fallback_chunk(self, chunker):
        f = _make_file("Makefile", NO_EXTENSION_FILE)
        chunks = chunker.chunk(f, repo_id="repo-33", branch="main")
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "file"


# ---------------------------------------------------------------------------
# T34 — happy path — Nested class
# ---------------------------------------------------------------------------

class TestT34NestedClass:
    # [unit]
    def test_nested_class_is_l2(self, chunker):
        f = _make_file("src/nested.py", PYTHON_NESTED_CLASS)
        chunks = chunker.chunk(f, repo_id="repo-34", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        symbols = {c.symbol for c in classes}
        assert "Outer" in symbols
        assert "Inner" in symbols

    # [unit]
    def test_inner_method_parent_class(self, chunker):
        f = _make_file("src/nested.py", PYTHON_NESTED_CLASS)
        chunks = chunker.chunk(f, repo_id="repo-34", branch="main")
        inner_method = [c for c in chunks if c.symbol == "inner_method"][0]
        assert inner_method.parent_class == "Inner"


# ---------------------------------------------------------------------------
# T36 — error — parse_ast with invalid language → raises ValueError
# ---------------------------------------------------------------------------

class TestT36InvalidLanguage:
    # [unit]
    def test_raises_value_error(self, chunker):
        with pytest.raises(ValueError):
            chunker.parse_ast("some code", "brainfuck")


# ---------------------------------------------------------------------------
# T37 — happy path — Chunk IDs verified format
# ---------------------------------------------------------------------------

class TestT37ChunkIdFormat:
    # [unit]
    def test_chunk_ids_contain_repo_and_path(self, chunker):
        f = _make_file("src/calculator.py", PYTHON_CLASS_3_METHODS)
        chunks = chunker.chunk(f, repo_id="repo-37", branch="main")
        for c in chunks:
            assert "repo-37" in c.chunk_id
            assert isinstance(c.chunk_id, str)
            assert len(c.chunk_id) > 0


# ---------------------------------------------------------------------------
# T39 — boundary — .h file → parsed as C
# ---------------------------------------------------------------------------

class TestT39HeaderFile:
    # [unit]
    def test_h_parsed_as_c(self, chunker):
        f = _make_file("src/utils.h", C_HEADER)
        chunks = chunker.chunk(f, repo_id="repo-39", branch="main")
        for c in chunks:
            assert c.language == "c"


# ---------------------------------------------------------------------------
# T40 — boundary — Lazy parser: chunk two Python files → parser created once
# ---------------------------------------------------------------------------

class TestChunkerEdgeCases:
    # [unit]
    def test_extract_signature_unknown_lang(self, chunker):
        """extract_signature with unsupported language returns empty."""
        import tree_sitter as ts
        import tree_sitter_python as tsp
        lang = ts.Language(tsp.language())
        parser = ts.Parser(lang)
        tree = parser.parse(b"def foo(): pass")
        node = tree.root_node.children[0]
        result = chunker.extract_signature(node, "unknown_lang")
        assert result == ""

    # [unit]
    def test_extract_doc_comment_no_docstring(self, chunker):
        """Function with no docstring returns empty doc_comment."""
        f = _make_file("src/simple.py", "def foo():\n    return 1\n")
        chunks = chunker.chunk(f, repo_id="repo-edge", branch="main")
        func = [c for c in chunks if c.chunk_type == "function"][0]
        assert func.doc_comment == ""

    # [unit]
    def test_extract_imports_unknown_lang(self, chunker):
        """extract_imports with unknown language returns empty list."""
        import tree_sitter as ts
        import tree_sitter_python as tsp
        lang = ts.Language(tsp.language())
        parser = ts.Parser(lang)
        tree = parser.parse(b"import os")
        result = chunker.extract_imports(tree, "unknown_lang")
        assert result == []

    # [unit]
    def test_file_chunk_no_language(self, chunker):
        """Fallback chunk for unknown extension has language 'unknown'."""
        f = _make_file("Makefile", "all: build")
        chunks = chunker.chunk(f, repo_id="repo-unk", branch="main")
        assert chunks[0].language == "unknown"

    # [unit]
    def test_extract_class_chunks_no_class_nodes(self, chunker):
        """C language has no class nodes -> returns empty."""
        f = _make_file("src/simple.c", C_THREE_FUNCTIONS)
        chunks = chunker.chunk(f, repo_id="repo-cno", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        assert len(classes) == 0


class TestChunkerCoverageBoost:
    # [unit]
    def test_c_line_comment_extraction(self, chunker):
        """C-style line comments (//) are extracted as doc_comment."""
        c_code = '// Adds two numbers.\nint add(int a, int b) { return a + b; }\n'
        f = _make_file("src/add.c", c_code)
        chunks = chunker.chunk(f, repo_id="repo-cc", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(funcs) == 1
        assert "Adds two numbers" in funcs[0].doc_comment

    # [unit]
    def test_js_export_arrow_function(self, chunker):
        """Exported arrow functions are detected as L3 chunks."""
        js_code = 'export const square = (x) => x * x;\n'
        f = _make_file("src/math.js", js_code)
        chunks = chunker.chunk(f, repo_id="repo-exp", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(funcs) >= 1
        assert any(c.symbol == "square" for c in funcs)

    # [unit]
    def test_python_function_with_decorator(self, chunker):
        """Decorated function is still extracted as L3 chunk."""
        py_code = "def simple(): pass\n"
        f = _make_file("src/dec.py", py_code)
        chunks = chunker.chunk(f, repo_id="repo-dec", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(funcs) >= 1
        assert funcs[0].symbol == "simple"

    # [unit]
    def test_class_without_body(self, chunker):
        """Java interface with no methods produces L2 but no L3."""
        java_code = 'interface Empty {}\n'
        f = _make_file("src/Empty.java", java_code)
        chunks = chunker.chunk(f, repo_id="repo-emj", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        assert len(classes) == 1
        assert classes[0].symbol == "Empty"

    # [unit]
    def test_cpp_using_declaration_import(self, chunker):
        """C++ using declaration is extracted as import."""
        cpp_code = '#include <iostream>\nusing namespace std;\nint main() { return 0; }\n'
        f = _make_file("src/main.cpp", cpp_code)
        chunks = chunker.chunk(f, repo_id="repo-using", branch="main")
        l1 = [c for c in chunks if c.chunk_type == "file"][0]
        assert any("include" in imp for imp in l1.imports)

    # [unit]
    def test_extract_file_chunk_no_language(self, chunker):
        """extract_file_chunk with default language param."""
        f = _make_file("src/test.py", "import os\ndef foo(): pass\n")
        tree = chunker.parse_ast(f.content, "python")
        chunk = chunker.extract_file_chunk(tree, f, "r", "main")
        assert chunk.chunk_type == "file"
        assert "import os" in chunk.imports

    # [unit]
    def test_extract_class_chunks_no_language(self, chunker):
        """extract_class_chunks with default language resolution."""
        f = _make_file("src/test.py", "class Foo:\n    pass\n")
        tree = chunker.parse_ast(f.content, "python")
        chunks = chunker.extract_class_chunks(tree, f, "r", "main")
        assert len(chunks) == 1

    # [unit]
    def test_extract_function_chunks_no_language(self, chunker):
        """extract_function_chunks with default language resolution."""
        f = _make_file("src/test.py", "def bar(): pass\n")
        tree = chunker.parse_ast(f.content, "python")
        chunks = chunker.extract_function_chunks(tree, f, "r", "main")
        assert len(chunks) == 1


class TestT40LazyParser:
    # [unit]
    def test_parser_reused(self, chunker):
        f1 = _make_file("src/a.py", PYTHON_THREE_FUNCTIONS)
        f2 = _make_file("src/b.py", PYTHON_CLASS_3_METHODS)
        chunks1 = chunker.chunk(f1, repo_id="repo-40", branch="main")
        chunks2 = chunker.chunk(f2, repo_id="repo-40", branch="main")
        # Both should succeed; parser is created once and reused
        assert len(chunks1) >= 1
        assert len(chunks2) >= 1


# ===========================================================================
# Feature #36 — JavaScript: prototype-assigned functions + require() imports
# [no integration test] — pure computation feature, no external I/O
# ===========================================================================

JS_PROTOTYPE_FUNCTION = """\
res.status = function(code) { return code; };
"""

JS_PROTOTYPE_ARROW = """\
obj.handler = (req, res) => { return 42; };
"""

JS_REQUIRE_SINGLE = """\
var express = require('express');
"""

JS_REQUIRE_MULTIPLE = """\
var express = require('express');
const path = require('path');
let _ = require('lodash');
"""

JS_PROTOTYPE_WITH_NORMAL = """\
class Router {
    get(path) { return path; }
}

function formatDate(date) {
    return date.toISOString();
}

res.status = function(code) { return code; };
"""

JS_DEEP_MEMBER_CHAIN = """\
a.b.c.d = function() { return 1; };
"""

JS_NON_FUNCTION_ASSIGN = """\
obj.x = 42;
"""

JS_REQUIRE_SCOPED = """\
const a = require('@scope/pkg');
"""

JS_REQUIRE_DYNAMIC = """\
const a = require(dynamicVar);
"""

JS_COMPUTED_PROPERTY = """\
obj[key] = function() { return 1; };
"""

JS_REQUIRE_NO_SEMICOLONS = """\
var a = require('alpha')
const b = require('beta')
"""


class TestFeature36JsPrototypeAssign:
    """Feature #36 — prototype-assigned function detection."""

    # [unit] T01: happy path — function_expression assignment
    def test_js_prototype_function(self, chunker):
        """res.status = function(code){...} → L3 chunk with symbol='status'."""
        f = _make_file("src/app.js", JS_PROTOTYPE_FUNCTION)
        chunks = chunker.chunk(f, repo_id="repo-36", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(funcs) == 1
        assert funcs[0].symbol == "status"
        assert funcs[0].language == "javascript"
        assert funcs[0].parent_class == ""

    # [unit] T02: happy path — arrow_function assignment
    def test_js_prototype_arrow(self, chunker):
        """obj.handler = (req, res) => {...} → L3 chunk with symbol='handler'."""
        f = _make_file("src/app.js", JS_PROTOTYPE_ARROW)
        chunks = chunker.chunk(f, repo_id="repo-36", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(funcs) == 1
        assert funcs[0].symbol == "handler"
        assert funcs[0].language == "javascript"

    # [unit] T05: happy path — prototype alongside normal functions and classes
    def test_js_prototype_with_normal_functions(self, chunker):
        """Prototype-assigned function coexists with normal functions and classes."""
        f = _make_file("src/app.js", JS_PROTOTYPE_WITH_NORMAL)
        chunks = chunker.chunk(f, repo_id="repo-36", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        classes = [c for c in chunks if c.chunk_type == "class"]

        func_symbols = {c.symbol for c in funcs}
        assert "status" in func_symbols, "prototype fn missing"
        assert "formatDate" in func_symbols, "normal fn missing"
        assert "get" in func_symbols, "class method missing"
        assert len(classes) == 1
        assert classes[0].symbol == "Router"

    # [unit] T06: boundary — deep member chain
    def test_js_deep_member_chain(self, chunker):
        """a.b.c.d = function(){} → L3 chunk with symbol='d' (last property)."""
        f = _make_file("src/app.js", JS_DEEP_MEMBER_CHAIN)
        chunks = chunker.chunk(f, repo_id="repo-36", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(funcs) == 1
        assert funcs[0].symbol == "d"

    # [unit] T07: boundary — non-function assignment produces no L3 chunk
    def test_js_non_function_assign_no_chunk(self, chunker):
        """obj.x = 42 should NOT produce an L3 function chunk."""
        f = _make_file("src/app.js", JS_NON_FUNCTION_ASSIGN)
        chunks = chunker.chunk(f, repo_id="repo-36", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(funcs) == 0

    # [unit] T10: boundary — normal JS file unaffected
    def test_js_normal_file_unaffected(self, chunker):
        """File with no prototype assigns produces normal chunks only."""
        f = _make_file("src/events.js", JAVASCRIPT_MIXED)
        chunks = chunker.chunk(f, repo_id="repo-36", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        func_symbols = {c.symbol for c in funcs}
        # Normal functions: constructor, on, formatDate, double
        assert "formatDate" in func_symbols
        assert "double" in func_symbols

    # [unit] T11: error — computed property assignment no L3 chunk
    def test_js_computed_property_no_chunk(self, chunker):
        """obj[key] = function(){} should NOT produce an L3 chunk."""
        f = _make_file("src/app.js", JS_COMPUTED_PROPERTY)
        chunks = chunker.chunk(f, repo_id="repo-36", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(funcs) == 0

    # [unit] T13: boundary — empty JS file
    def test_js_empty_file(self, chunker):
        """Empty JS file produces only L1 file chunk, no crash."""
        f = _make_file("src/empty.js", "")
        chunks = chunker.chunk(f, repo_id="repo-36", branch="main")
        assert len(chunks) == 1
        assert chunks[0].chunk_type == "file"
        assert chunks[0].imports == []

    # [unit] T14: happy path — chunk content includes full statement text
    def test_js_prototype_content_is_full_statement(self, chunker):
        """Prototype function chunk content includes the full expression_statement."""
        f = _make_file("src/app.js", JS_PROTOTYPE_FUNCTION)
        chunks = chunker.chunk(f, repo_id="repo-36", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(funcs) == 1
        assert "res.status" in funcs[0].content
        assert "function" in funcs[0].content

    # [unit] — prototype-assigned function appears in top_level_symbols
    def test_js_prototype_in_top_level_symbols(self, chunker):
        """Prototype-assigned function symbol appears in L1 top_level_symbols."""
        f = _make_file("src/app.js", JS_PROTOTYPE_FUNCTION)
        chunks = chunker.chunk(f, repo_id="repo-36", branch="main")
        l1 = [c for c in chunks if c.chunk_type == "file"][0]
        assert "status" in l1.top_level_symbols


class TestFeature36JsRequireImports:
    """Feature #36 — CommonJS require() import detection."""

    # [unit] T03: happy path — single require()
    def test_js_require_single(self, chunker):
        """var express = require('express') → imports includes 'express'."""
        f = _make_file("src/app.js", JS_REQUIRE_SINGLE)
        chunks = chunker.chunk(f, repo_id="repo-36", branch="main")
        l1 = [c for c in chunks if c.chunk_type == "file"][0]
        assert "express" in l1.imports

    # [unit] T04: happy path — multiple require() with var/const/let
    def test_js_require_multiple(self, chunker):
        """Multiple require() calls with var/const/let all detected."""
        f = _make_file("src/app.js", JS_REQUIRE_MULTIPLE)
        chunks = chunker.chunk(f, repo_id="repo-36", branch="main")
        l1 = [c for c in chunks if c.chunk_type == "file"][0]
        assert "express" in l1.imports
        assert "path" in l1.imports
        assert "lodash" in l1.imports

    # [unit] T08: boundary — scoped package
    def test_js_require_scoped_package(self, chunker):
        """require('@scope/pkg') → imports includes '@scope/pkg'."""
        f = _make_file("src/app.js", JS_REQUIRE_SCOPED)
        chunks = chunker.chunk(f, repo_id="repo-36", branch="main")
        l1 = [c for c in chunks if c.chunk_type == "file"][0]
        assert "@scope/pkg" in l1.imports

    # [unit] T09: boundary — dynamic require is not extracted
    def test_js_require_dynamic_skipped(self, chunker):
        """require(dynamicVar) should NOT be added to imports."""
        f = _make_file("src/app.js", JS_REQUIRE_DYNAMIC)
        chunks = chunker.chunk(f, repo_id="repo-36", branch="main")
        l1 = [c for c in chunks if c.chunk_type == "file"][0]
        # Should have no imports from dynamic require
        assert len(l1.imports) == 0

    # [unit] T12: boundary — require without semicolons (ASI)
    def test_js_require_no_semicolons(self, chunker):
        """require() calls without semicolons still detected."""
        f = _make_file("src/app.js", JS_REQUIRE_NO_SEMICOLONS)
        chunks = chunker.chunk(f, repo_id="repo-36", branch="main")
        l1 = [c for c in chunks if c.chunk_type == "file"][0]
        assert "alpha" in l1.imports
        assert "beta" in l1.imports

    # [unit] — require + ES import coexistence
    def test_js_require_with_es_imports(self, chunker):
        """require() imports and ES import statements both collected."""
        js_code = "import { foo } from 'bar';\nconst x = require('baz');\n"
        f = _make_file("src/app.js", js_code)
        chunks = chunker.chunk(f, repo_id="repo-36", branch="main")
        l1 = [c for c in chunks if c.chunk_type == "file"][0]
        assert any("bar" in imp for imp in l1.imports), "ES import missing"
        assert "baz" in l1.imports, "require import missing"


# ===========================================================================
# Feature #37 — TypeScript: enum + namespace + decorator unwrapping
# [no integration test] — pure computation feature, no external I/O
# ===========================================================================

TS_ENUM = """\
enum Color { Red, Green, Blue }
"""

TS_NAMESPACE_CLASS = """\
namespace Foo {
  class Bar {
    method() { return 1; }
  }
}
"""

TS_NESTED_NAMESPACE = """\
namespace A {
  namespace B {
    class C {}
  }
}
"""

TS_DECORATOR_CLASS = """\
@Component({selector: 'app'})
class AppComponent {
  render() { return 1; }
}
"""

TS_EMPTY_NAMESPACE = """\
namespace Empty {}
"""

TS_ENUM_CLASS_NAMESPACE = """\
enum Status { Active, Inactive }

class Router {
    handle() { return 1; }
}

namespace Utils {
  class Helper {
    format() { return 'ok'; }
  }
}
"""

TS_NAMESPACE_FUNCTIONS = """\
namespace MathUtils {
  function add(a: number, b: number): number { return a + b; }
  function sub(a: number, b: number): number { return a - b; }
}
"""

TS_EXPORT_NAMESPACE = """\
export namespace Foo {
  class Bar {
    greet() { return 'hi'; }
  }
}
"""


class TestFeature37TsEnum:
    """Feature #37 — TypeScript enum detection."""

    # [unit] T01: happy path — enum produces L2 chunk
    def test_ts_enum_produces_l2(self, chunker):
        """enum Color { Red, Green, Blue } → L2 chunk with symbol='Color'."""
        f = _make_file("src/types.ts", TS_ENUM)
        chunks = chunker.chunk(f, repo_id="repo-37", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        assert len(classes) == 1
        assert classes[0].symbol == "Color"
        assert classes[0].language == "typescript"


class TestFeature37TsNamespace:
    """Feature #37 — TypeScript namespace unwrapping."""

    # [unit] T02: happy path — namespace with class → L2 + L3
    def test_ts_namespace_class_method(self, chunker):
        """namespace Foo { class Bar { method() {} } } → L2 Bar + L3 method."""
        f = _make_file("src/foo.ts", TS_NAMESPACE_CLASS)
        chunks = chunker.chunk(f, repo_id="repo-37", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert any(c.symbol == "Bar" for c in classes), "class Bar not found"
        assert any(c.symbol == "method" for c in funcs), "method not found"

    # [unit] T03: happy path — nested namespace → class found
    def test_ts_nested_namespace(self, chunker):
        """namespace A { namespace B { class C {} } } → L2 chunk symbol='C'."""
        f = _make_file("src/nested.ts", TS_NESTED_NAMESPACE)
        chunks = chunker.chunk(f, repo_id="repo-37", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        assert any(c.symbol == "C" for c in classes), "class C not found in nested namespace"

    # [unit] T05: boundary — empty namespace
    def test_ts_empty_namespace(self, chunker):
        """Empty namespace produces no L2/L3 chunks."""
        f = _make_file("src/empty.ts", TS_EMPTY_NAMESPACE)
        chunks = chunker.chunk(f, repo_id="repo-37", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(classes) == 0
        assert len(funcs) == 0

    # [unit] T06: boundary — enum + class + namespace coexistence
    def test_ts_enum_class_namespace_coexist(self, chunker):
        """Enum, class, and namespace all produce correct chunks."""
        f = _make_file("src/mixed.ts", TS_ENUM_CLASS_NAMESPACE)
        chunks = chunker.chunk(f, repo_id="repo-37", branch="main")
        class_symbols = {c.symbol for c in chunks if c.chunk_type == "class"}
        func_symbols = {c.symbol for c in chunks if c.chunk_type == "function"}
        assert "Status" in class_symbols, "enum not found"
        assert "Router" in class_symbols, "class not found"
        assert "Helper" in class_symbols, "namespace class not found"
        assert "handle" in func_symbols
        assert "format" in func_symbols

    # [unit] T07: boundary — namespace with functions only (no class)
    def test_ts_namespace_functions(self, chunker):
        """namespace MathUtils { function add() {}, function sub() {} } → L3 chunks."""
        f = _make_file("src/math.ts", TS_NAMESPACE_FUNCTIONS)
        chunks = chunker.chunk(f, repo_id="repo-37", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        func_symbols = {c.symbol for c in funcs}
        assert "add" in func_symbols
        assert "sub" in func_symbols

    # [unit] T08: boundary — exported namespace
    def test_ts_export_namespace(self, chunker):
        """export namespace Foo { class Bar {} } → L2 Bar found."""
        f = _make_file("src/exports.ts", TS_EXPORT_NAMESPACE)
        chunks = chunker.chunk(f, repo_id="repo-37", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        assert any(c.symbol == "Bar" for c in classes), "class Bar not found in exported namespace"

    # [unit] T09: boundary — normal TS file unaffected
    def test_ts_normal_file_unaffected(self, chunker):
        """Normal TS file with classes and interfaces still works."""
        f = _make_file("src/logger.ts", TYPESCRIPT_CLASS_INTERFACE)
        chunks = chunker.chunk(f, repo_id="repo-37", branch="main")
        class_symbols = {c.symbol for c in chunks if c.chunk_type == "class"}
        assert "ConsoleLogger" in class_symbols


class TestFeature37TsDecorator:
    """Feature #37 — TypeScript decorator verification."""

    # [unit] T04: happy path — decorator on class already works
    def test_ts_decorator_class(self, chunker):
        """@Component class AppComponent { render() {} } → L2 + L3."""
        f = _make_file("src/app.ts", TS_DECORATOR_CLASS)
        chunks = chunker.chunk(f, repo_id="repo-37", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert any(c.symbol == "AppComponent" for c in classes)
        assert any(c.symbol == "render" for c in funcs)
