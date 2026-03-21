"""Example: Embedding Generation — Feature #7.

Demonstrates EmbeddingEncoder and IndexWriter usage for code chunk embedding
and index writing. Uses a mock model to avoid downloading the real CodeSage-large
model (~1.3GB).
"""

import numpy as np
from unittest.mock import MagicMock, patch


def main():
    # --- EmbeddingEncoder demo ---
    print("=== EmbeddingEncoder Demo ===\n")

    # Mock the SentenceTransformer to avoid downloading the real model
    mock_model = MagicMock()
    mock_model.encode = MagicMock(
        side_effect=lambda texts, **kwargs: np.random.rand(len(texts), 1024).astype(
            np.float32
        )
    )

    with patch(
        "src.indexing.embedding_encoder.SentenceTransformer", return_value=mock_model
    ):
        from src.indexing.embedding_encoder import EmbeddingEncoder

        encoder = EmbeddingEncoder(model_name="mock-model")

    # Encode batch of code chunks
    code_texts = [
        "def hello(): print('Hello, world!')",
        "class Config: timeout = 30",
        "import os\nos.getenv('API_KEY')",
    ]
    vectors = encoder.encode_batch(code_texts)
    print(f"Encoded {len(vectors)} code chunks:")
    for i, vec in enumerate(vectors):
        print(f"  Chunk {i}: shape={vec.shape}, dtype={vec.dtype}, norm={np.linalg.norm(vec):.4f}")

    # Encode a query with instruction prefix
    query = "how to configure timeout"
    query_vec = encoder.encode_query(query)
    print(f"\nQuery vector: shape={query_vec.shape}, dtype={query_vec.dtype}")
    print(f"  (query prefix 'Represent this code search query: ' was prepended)")

    # Encode batch with is_query=True
    queries = ["find auth middleware", "database connection pool"]
    query_vecs = encoder.encode_batch(queries, is_query=True)
    print(f"\nBatch query encoding: {len(query_vecs)} queries, each {query_vecs[0].shape}")

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

    print("\nDone! In production, replace mock-model with 'Salesforce/codesage-large'.")


if __name__ == "__main__":
    main()
