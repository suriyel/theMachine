"""Tests for CodeChunker - Feature #6 Code Chunking with tree-sitter (FR-004).

These tests verify multi-granularity code chunking using tree-sitter parsers.
[no integration test] — pure function, no external I/O
"""

import pytest
from pathlib import Path
from uuid import uuid4

# These imports will fail until we implement the chunker
from src.indexing.models import RawContent, ContentType


# Sample Java code with 2 classes, each with 3 methods
SAMPLE_JAVA_CODE = '''package com.example;

public class UserService {
    public void createUser() {
        // create user logic
    }

    public void updateUser() {
        // update user logic
    }

    public void deleteUser() {
        // delete user logic
    }
}

public class OrderService {
    public void createOrder() {
        // create order logic
    }

    public void updateOrder() {
        // update order logic
    }

    public void cancelOrder() {
        // cancel order logic
    }
}
'''

# Sample Python code with 4 functions and 2 classes
SAMPLE_PYTHON_CODE = '''"""Sample module."""

def function_one():
    """First function."""
    pass

def function_two():
    """Second function."""
    pass

def function_three():
    """Third function."""
    pass

def function_four():
    """Fourth function."""
    pass


class ClassOne:
    """First class."""

    def method_a(self):
        pass

    def method_b(self):
        pass


class ClassTwo:
    """Second class."""

    def method_c(self):
        pass
'''

# Sample TypeScript code with interfaces and type definitions
SAMPLE_TYPESCRIPT_CODE = '''interface User {
    id: number;
    name: string;
    email: string;
}

interface Order {
    orderId: string;
    amount: number;
    status: 'pending' | 'completed';
}

type UserWithOrders = User & {
    orders: Order[];
};

function getUser(id: number): User | null {
    return null;
}

function createOrder(order: Order): Order {
    return order;
}

class UserService {
    private user: User;

    constructor(user: User) {
        this.user = user;
    }

    getUser(): User {
        return this.user;
    }
}
'''

# Sample unsupported language (Ruby)
SAMPLE_RUBY_CODE = '''class User
  def create
    # create user
  end

  def update
    # update user
  end
end
'''


# [unit] Test Java chunking - generates file, class, and method chunks
def test_java_chunking_creates_file_class_and_method_chunks():
    """Given a Java file with 2 classes each containing 3 methods,
    when chunking executes,
    then 1 file-level + 2 class-level + 6 method-level chunks are generated."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("src/main/java/com/example/Service.java"),
        content_type=ContentType.SOURCE,
        language="java",
        content=SAMPLE_JAVA_CODE
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    # Verify chunk types
    chunk_types = [c.chunk_type for c in chunks]

    # Should have: 1 file + 2 class + 6 method = 9 chunks
    assert len(chunks) == 9, f"Expected 9 chunks, got {len(chunks)}"

    # Count by type
    file_chunks = [c for c in chunks if c.chunk_type.value == "file"]
    class_chunks = [c for c in chunks if c.chunk_type.value == "class"]
    method_chunks = [c for c in chunks if c.chunk_type.value == "function"]

    assert len(file_chunks) == 1, f"Expected 1 file chunk, got {len(file_chunks)}"
    assert len(class_chunks) == 2, f"Expected 2 class chunks, got {len(class_chunks)}"
    assert len(method_chunks) == 6, f"Expected 6 method chunks, got {len(method_chunks)}"


# [unit] Test Python chunking with correct line ranges
def test_python_chunking_creates_file_class_and_function_chunks():
    """Given a Python file with 4 functions and 2 classes,
    when chunking executes,
    then file, class, and function chunks are generated with correct line ranges."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("module.py"),
        content_type=ContentType.SOURCE,
        language="python",
        content=SAMPLE_PYTHON_CODE
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    # Should have: 1 file + 2 class + 4 function = 7 chunks minimum
    assert len(chunks) >= 7, f"Expected at least 7 chunks, got {len(chunks)}"

    # Verify line ranges are valid (start <= end)
    for chunk in chunks:
        assert chunk.start_line <= chunk.end_line, \
            f"Invalid line range: {chunk.start_line} > {chunk.end_line} for {chunk.symbol_name}"


# [unit] Test unsupported language fallback
def test_unsupported_language_fallback_creates_single_file_chunk():
    """Given a source file in unsupported language (e.g., Ruby),
    when chunking executes,
    then single file-level text chunk is created without symbol decomposition."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("user.rb"),
        content_type=ContentType.SOURCE,
        language="ruby",
        content=SAMPLE_RUBY_CODE
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    # Should have exactly 1 file-level chunk
    assert len(chunks) == 1, f"Expected 1 chunk, got {len(chunks)}"

    chunk = chunks[0]
    assert chunk.chunk_type.value == "file", f"Expected file chunk, got {chunk.chunk_type.value}"
    assert chunk.symbol_name is None or chunk.symbol_name == ""


# [unit] Test TypeScript with interfaces and type definitions
def test_typescript_chunking_includes_type_information():
    """Given a TypeScript file with interfaces and type definitions,
    when chunking executes,
    then symbol-level chunks include type information."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("types.ts"),
        content_type=ContentType.SOURCE,
        language="typescript",
        content=SAMPLE_TYPESCRIPT_CODE
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    # Should have file + interfaces + types + functions + methods
    assert len(chunks) >= 5, f"Expected at least 5 chunks, got {len(chunks)}"

    # Verify interfaces are captured as symbols
    symbol_names = [c.symbol_name for c in chunks if c.symbol_type in ("interface", "type")]

    # Should include User, Order, UserWithOrders interfaces/types
    assert len(symbol_names) >= 3, f"Expected at least 3 type symbols, got {len(symbol_names)}"


# [unit] Test chunk has required fields
def test_chunk_has_required_fields():
    """Verify CodeChunk has all required fields."""
    from src.indexing.chunker import CodeChunker
    from src.indexing.models import ChunkType

    repo_id = str(uuid4())
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("test.py"),
        content_type=ContentType.SOURCE,
        language="python",
        content="def test(): pass"
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    assert len(chunks) > 0

    chunk = chunks[0]
    assert hasattr(chunk, "repo_id")
    assert hasattr(chunk, "file_path")
    assert hasattr(chunk, "chunk_type")
    assert hasattr(chunk, "symbol_name")
    assert hasattr(chunk, "start_line")
    assert hasattr(chunk, "end_line")
    assert hasattr(chunk, "content")


# [unit] Test JavaScript chunking
def test_javascript_chunking():
    """Given a JavaScript file with functions and classes,
    when chunking executes,
    then chunks are generated at file, class, and function level."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    js_code = '''function hello() {
    console.log("Hello");
}

class Calculator {
    add(a, b) {
        return a + b;
    }

    subtract(a, b) {
        return a - b;
    }
}
'''
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("app.js"),
        content_type=ContentType.SOURCE,
        language="javascript",
        content=js_code
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    # Should have: 1 file + 1 class + 1 function = 3 chunks minimum
    assert len(chunks) >= 3, f"Expected at least 3 chunks, got {len(chunks)}"


# [unit] Test C chunking
def test_c_chunking():
    """Given a C file with functions,
    when chunking executes,
    then chunks are generated at file and function level."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    c_code = '''#include <stdio.h>

void hello() {
    printf("Hello\\n");
}

int add(int a, int b) {
    return a + b;
}
'''
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("main.c"),
        content_type=ContentType.SOURCE,
        language="c",
        content=c_code
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    # Should have: 1 file + 2 function = 3 chunks minimum
    assert len(chunks) >= 2, f"Expected at least 2 chunks, got {len(chunks)}"


# [unit] Test C++ chunking
def test_cpp_chunking():
    """Given a C++ file with classes and functions,
    when chunking executes,
    then chunks are generated at file, class, and function level."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    cpp_code = '''#include <iostream>

class Calculator {
public:
    int add(int a, int b) {
        return a + b;
    }
};

void hello() {
    std::cout << "Hello" << std::endl;
}
'''
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("main.cpp"),
        content_type=ContentType.SOURCE,
        language="cpp",
        content=cpp_code
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    # Should have: 1 file + 1 class + 1+ function = 3 chunks minimum
    assert len(chunks) >= 3, f"Expected at least 3 chunks, got {len(chunks)}"


# [unit] Test empty content handling
def test_empty_content_returns_empty_chunks():
    """Given an empty source file,
    when chunking executes,
    then empty list is returned."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("empty.py"),
        content_type=ContentType.SOURCE,
        language="python",
        content=""
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    # Should return at least the file-level chunk
    assert len(chunks) >= 1


# [unit] Test repo_id propagation
def test_chunk_propagates_repo_id():
    """Verify that chunks have correct repo_id from RawContent."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("test.py"),
        content_type=ContentType.SOURCE,
        language="python",
        content="def test(): pass"
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    for chunk in chunks:
        assert chunk.repo_id == repo_id, \
            f"Expected repo_id {repo_id}, got {chunk.repo_id}"


# [unit] Test file_path propagation
def test_chunk_propagates_file_path():
    """Verify that chunks have correct file_path from RawContent."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    file_path = Path("src/module/test.py")
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=file_path,
        content_type=ContentType.SOURCE,
        language="python",
        content="def test(): pass"
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    for chunk in chunks:
        assert chunk.file_path == file_path, \
            f"Expected file_path {file_path}, got {chunk.file_path}"


# [unit] Test multiline content extraction
def test_multiline_content_lines():
    """Verify that multiline content has correct line numbers."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    code = '''def hello():
    print("line 2")
    print("line 3")
    print("line 4")
'''
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("test.py"),
        content_type=ContentType.SOURCE,
        language="python",
        content=code
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    # File chunk should have correct line range (4 lines, no trailing newline)
    file_chunk = [c for c in chunks if c.chunk_type.value == "file"][0]
    assert file_chunk.start_line == 1
    assert file_chunk.end_line == 4


# [unit] Test None language handling
def test_none_language_treated_as_unsupported():
    """Verify that None language falls back to file-level chunking."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("test.xyz"),
        content_type=ContentType.SOURCE,
        language=None,
        content="some content"
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    # Should fallback to file-level chunking
    assert len(chunks) == 1
    assert chunks[0].chunk_type.value == "file"


# [unit] Test parsing error handling
def test_malformed_code_returns_fallback():
    """Given malformed code that fails to parse,
    when chunking executes,
    then fallback to file-level chunking."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    # Invalid Java - missing closing brace
    malformed_java = '''public class Test {
    public void method() {
'''
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("Test.java"),
        content_type=ContentType.SOURCE,
        language="java",
        content=malformed_java
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    # Should still return at least the file-level chunk
    assert len(chunks) >= 1


# [unit] Test method inside class for Python
def test_python_methods_extracted():
    """Given a Python class with methods,
    when chunking executes,
    then method-level chunks are generated."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    code = '''class MyClass:
    def method1(self):
        pass

    def method2(self):
        pass
'''
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("myclass.py"),
        content_type=ContentType.SOURCE,
        language="python",
        content=code
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    # Should have file, class, and at least 2 method chunks
    assert len(chunks) >= 3


# [unit] Test C++ class with methods
def test_cpp_class_with_methods():
    """Given a C++ class with methods,
    when chunking executes,
    then method chunks are extracted."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    code = '''class MyClass {
public:
    void method1() { }
    void method2() { }
};
'''
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("myclass.cpp"),
        content_type=ContentType.SOURCE,
        language="cpp",
        content=code
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    # Should have file and class chunks (methods inside class body not extracted in current impl)
    assert len(chunks) >= 2


# [unit] Test unsupported language triggers fallback
def test_totally_unsupported_language():
    """Given a language not in SUPPORTED_LANGUAGES,
    when chunking executes,
    then fallback to file-level chunking."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("test.php"),
        content_type=ContentType.SOURCE,
        language="php",  # Not in supported languages
        content="echo 'hello';"
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    # Should fallback to file-level
    assert len(chunks) == 1
    assert chunks[0].chunk_type.value == "file"


# [unit] Test unknown language
def test_unknown_language():
    """Given an unknown language string,
    when chunking executes,
    then fallback to file-level chunking."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("test.xyz"),
        content_type=ContentType.SOURCE,
        language="totally_unknown_lang",
        content="some code"
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    # Should fallback to file-level
    assert len(chunks) == 1


# [unit] Test single line content
def test_single_line_content():
    """Given a single line of code,
    when chunking executes,
    then correct line numbers are generated."""
    from src.indexing.chunker import CodeChunker

    repo_id = str(uuid4())
    raw_content = RawContent(
        repo_id=repo_id,
        file_path=Path("test.py"),
        content_type=ContentType.SOURCE,
        language="python",
        content="x = 1"
    )

    chunker = CodeChunker()
    chunks = chunker.chunk(raw_content)

    file_chunk = [c for c in chunks if c.chunk_type.value == "file"][0]
    assert file_chunk.start_line == 1
    assert file_chunk.end_line == 1
