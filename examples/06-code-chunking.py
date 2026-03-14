"""Example: Code Chunking - Feature #6 FR-004

This example demonstrates how to use the CodeChunker to segment source code
into multi-granularity chunks using tree-sitter parsers.

Run: python examples/06-code-chunking.py
"""

import tempfile
from pathlib import Path

from src.indexing.chunker import CodeChunker
from src.indexing.models import RawContent, ContentType


def main():
    """Demonstrate code chunking."""
    print("=" * 60)
    print("Code Chunking Example - Feature #6 FR-004")
    print("=" * 60)

    chunker = CodeChunker()

    # Example 1: Java code with multiple classes and methods
    print("\n--- Example 1: Java Multi-Granularity ---")
    java_code = '''package com.example;

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

    raw_content = RawContent(
        repo_id="test-repo-001",
        file_path=Path("src/main/java/com/example/Service.java"),
        content_type=ContentType.SOURCE,
        language="java",
        content=java_code
    )

    chunks = chunker.chunk(raw_content)
    print(f"Generated {len(chunks)} chunks:\n")

    for chunk in chunks:
        print(f"  {chunk.chunk_type.value}: {chunk.symbol_name or 'file-level'} "
              f"(lines {chunk.start_line}-{chunk.end_line})")

    # Example 2: Python code
    print("\n--- Example 2: Python Code ---")
    python_code = '''"""Sample module."""


def function_one():
    """First function."""
    pass


def function_two():
    """Second function."""
    pass


class MyClass:
    """First class."""

    def method_a(self):
        pass

    def method_b(self):
        pass
'''

    raw_content = RawContent(
        repo_id="test-repo-001",
        file_path=Path("module.py"),
        content_type=ContentType.SOURCE,
        language="python",
        content=python_code
    )

    chunks = chunker.chunk(raw_content)
    print(f"Generated {len(chunks)} chunks:\n")

    for chunk in chunks:
        print(f"  {chunk.chunk_type.value}: {chunk.symbol_name or 'file-level'} "
              f"(lines {chunk.start_line}-{chunk.end_line})")

    # Example 3: TypeScript with interfaces
    print("\n--- Example 3: TypeScript with Types ---")
    typescript_code = '''interface User {
    id: number;
    name: string;
}

type UserWithOrders = User & {
    orders: string[];
};

function getUser(id: number): User | null {
    return null;
}
'''

    raw_content = RawContent(
        repo_id="test-repo-001",
        file_path=Path("types.ts"),
        content_type=ContentType.SOURCE,
        language="typescript",
        content=typescript_code
    )

    chunks = chunker.chunk(raw_content)
    print(f"Generated {len(chunks)} chunks:\n")

    for chunk in chunks:
        print(f"  {chunk.chunk_type.value}: {chunk.symbol_name or 'file-level'} "
              f"(lines {chunk.start_line}-{chunk.end_line})")

    # Example 4: Unsupported language (Ruby)
    print("\n--- Example 4: Unsupported Language (Fallback) ---")
    ruby_code = '''class User
  def create
    # create user
  end

  def update
    # update user
  end
end
'''

    raw_content = RawContent(
        repo_id="test-repo-001",
        file_path=Path("user.rb"),
        content_type=ContentType.SOURCE,
        language="ruby",
        content=ruby_code
    )

    chunks = chunker.chunk(raw_content)
    print(f"Generated {len(chunks)} chunk (fallback to file-level):\n")

    for chunk in chunks:
        print(f"  {chunk.chunk_type.value}: {chunk.symbol_name or 'file-level'} "
              f"(lines {chunk.start_line}-{chunk.end_line})")

    print("\n" + "=" * 60)
    print("Code chunking complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
