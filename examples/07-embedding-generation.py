"""Example: Embedding Generation and Index Writing - Feature #7.

This example demonstrates:
1. Generating embeddings for code chunks using bge-code model
2. Writing chunks and embeddings to Elasticsearch
3. Writing vectors to Qdrant
4. Deleting old chunks before re-indexing
"""

from pathlib import Path
from src.indexing.embedding_encoder import EmbeddingEncoder
from src.indexing.index_writer import IndexWriter
from src.indexing.models import CodeChunk, ChunkType


def main():
    # Example 1: Generate embeddings for code chunks
    print("=== Embedding Generation Example ===")

    # Create sample code chunks
    chunks = [
        CodeChunk(
            repo_id="example-repo",
            file_path=Path("src/main.java"),
            language="Java",
            chunk_type=ChunkType.CLASS,
            symbol_name="HelloWorld",
            symbol_type="class",
            start_line=1,
            end_line=10,
            content="public class HelloWorld { public void greet() {} }"
        ),
        CodeChunk(
            repo_id="example-repo",
            file_path=Path("src/utils.py"),
            language="Python",
            chunk_type=ChunkType.FUNCTION,
            symbol_name="helper",
            symbol_type="function",
            start_line=5,
            end_line=10,
            content="def helper(): return 'help'"
        ),
    ]

    # Initialize encoder (uses bge-code-v1 model)
    encoder = EmbeddingEncoder()
    print(f"Model: {encoder.model_name}")
    print(f"Embedding dimension: {encoder.dimension}")

    # Generate embeddings
    texts = [chunk.content for chunk in chunks]
    embeddings = encoder.encode(texts)

    print(f"Generated {len(embeddings)} embeddings")
    print(f"Each embedding has {len(embeddings[0])} dimensions")

    # Example 2: Query encoding
    print("\n=== Query Encoding Example ===")
    query = "how to configure spring webclient timeout"
    query_embedding = encoder.encode_query(query)
    print(f"Query embedding dimension: {len(query_embedding)}")

    # Example 3: Index writing (requires running services)
    print("\n=== Index Writing Example ===")
    print("Note: Requires Elasticsearch and Qdrant running")
    print("1. Initialize IndexWriter")
    print("2. Call write_chunks(chunks, embeddings)")
    print("3. Call delete_by_repo(repo_id) for re-indexing")

    print("\n=== Complete ===")
    print("Embedding generation and index writing ready!")


if __name__ == "__main__":
    main()
