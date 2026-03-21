"""Example: Embedding Generation — Feature #7.

Demonstrates EmbeddingEncoder using DashScope text-embedding-v3 API.
Requires EMBEDDING_API_KEY environment variable to be set.
"""

import numpy as np


def main():
    from src.indexing.embedding_encoder import EmbeddingEncoder

    print("=== EmbeddingEncoder Demo (DashScope text-embedding-v3) ===\n")

    encoder = EmbeddingEncoder()

    # Encode batch of code chunks
    code_texts = [
        "def hello(): print('Hello, world!')",
        "class Config: timeout = 30",
        "import os\nos.getenv('API_KEY')",
    ]
    vectors = encoder.encode_batch(code_texts)
    print(f"Encoded {len(vectors)} code chunks:")
    for i, vec in enumerate(vectors):
        print(f"  Chunk {i}: shape={vec.shape}, dtype={vec.dtype}, "
              f"norm={np.linalg.norm(vec):.4f}, first3={vec[:3]}")

    # Encode a query with instruction prefix
    query = "how to configure timeout"
    query_vec = encoder.encode_query(query)
    print(f"\nQuery vector: shape={query_vec.shape}, dtype={query_vec.dtype}")
    print(f"  (query prefix 'Represent this code search query: ' was prepended)")
    print(f"  first3={query_vec[:3]}")

    # Compute cosine similarity between query and code chunks
    print("\nCosine similarity (query vs chunks):")
    for i, vec in enumerate(vectors):
        sim = np.dot(query_vec, vec) / (np.linalg.norm(query_vec) * np.linalg.norm(vec))
        print(f"  Chunk {i}: {sim:.4f}")

    # --- Error handling demo ---
    print("\n=== Error Handling Demo ===\n")

    try:
        encoder.encode_batch([])
    except ValueError as e:
        print(f"Empty batch error (expected): {e}")

    try:
        encoder.encode_query("")
    except ValueError as e:
        print(f"Empty query error (expected): {e}")

    print("\nDone!")


if __name__ == "__main__":
    main()
