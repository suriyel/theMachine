"""Tests for EmbeddingEncoder - Feature #7."""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch


# [no integration test] — EmbeddingEncoder is tested via mocks for unit tests
# Real embedding generation requires downloading bge-code-v1 model (~500MB)
# Integration with actual model is verified during ST phase with real services


class TestEmbeddingEncoder:
    """Unit tests for EmbeddingEncoder class."""

    def test_encoder_can_be_instantiated(self):
        """Given EmbeddingEncoder class, when instantiated, then object is created."""
        from src.indexing.embedding_encoder import EmbeddingEncoder

        encoder = EmbeddingEncoder()
        assert encoder is not None

    def test_encoder_with_custom_model(self):
        """Given EmbeddingEncoder with injected model, then uses that model."""
        from src.indexing.embedding_encoder import EmbeddingEncoder

        mock_model = MagicMock()
        encoder = EmbeddingEncoder(model=mock_model)
        assert encoder._model is mock_model

    def test_encode_returns_list_of_vectors(self):
        """Given a list of code chunks, when encode is called, then list of vectors is returned."""
        from src.indexing.embedding_encoder import EmbeddingEncoder

        # Create mock model that returns fixed embeddings
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([
            [0.1] * 1024,
            [0.2] * 1024,
            [0.3] * 1024,
        ])

        encoder = EmbeddingEncoder(model=mock_model)
        chunks = [
            "public class Hello { }",
            "def greet(): return 'hello'",
            "function hello() {}"
        ]
        vectors = encoder.encode(chunks)
        assert isinstance(vectors, list)
        assert len(vectors) == 3

    def test_encode_returns_correct_dimension(self):
        """Given code chunks, when encode is called, then each vector has correct dimension."""
        from src.indexing.embedding_encoder import EmbeddingEncoder

        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1] * 1024])

        encoder = EmbeddingEncoder(model=mock_model)
        chunks = ["public class Hello { }"]
        vectors = encoder.encode(chunks)
        assert len(vectors) == 1
        assert len(vectors[0]) == encoder.dimension

    def test_encode_query_returns_single_vector(self):
        """Given a query string, when encode_query is called, then single vector is returned."""
        from src.indexing.embedding_encoder import EmbeddingEncoder

        mock_model = MagicMock()
        # Return 2D array (single embedding) - need to match the encode return format
        mock_model.encode.return_value = np.array([[0.5] * 1024])

        encoder = EmbeddingEncoder(model=mock_model)
        query = "how to configure spring webclient timeout"
        vector = encoder.encode_query(query)
        assert isinstance(vector, list)
        assert len(vector) == encoder.dimension

    def test_encode_empty_list_returns_empty_list(self):
        """Given empty list, when encode is called, then empty list is returned."""
        from src.indexing.embedding_encoder import EmbeddingEncoder

        encoder = EmbeddingEncoder()
        vectors = encoder.encode([])
        assert vectors == []

    def test_encode_single_chunk_returns_single_vector(self):
        """Given single chunk, when encode is called, then single vector is returned."""
        from src.indexing.embedding_encoder import EmbeddingEncoder

        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1] * 1024])

        encoder = EmbeddingEncoder(model=mock_model)
        vectors = encoder.encode(["def hello(): pass"])
        assert len(vectors) == 1

    def test_dimension_property_returns_1024(self):
        """Given EmbeddingEncoder, when dimension is accessed, then 1024 is returned."""
        from src.indexing.embedding_encoder import EmbeddingEncoder

        encoder = EmbeddingEncoder()
        # bge-code-v1 returns 1024 dimensional vectors
        assert encoder.dimension == 1024

    def test_encode_query_uses_query_prefix(self):
        """Given a query, when encode_query is called, then query is prefixed."""
        from src.indexing.embedding_encoder import EmbeddingEncoder

        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1] * 1024])

        encoder = EmbeddingEncoder(model=mock_model)
        query = "timeout handling"
        encoder.encode_query(query)

        # Check that encode was called with prefixed query
        call_args = mock_model.encode.call_args
        prefixed_query = call_args[0][0]
        assert "Represent this code for semantic search" in prefixed_query

    def test_encode_passes_all_texts_to_model(self):
        """Given multiple texts, when encode is called, then all are passed to model."""
        from src.indexing.embedding_encoder import EmbeddingEncoder

        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[0.1] * 1024] * 5)

        encoder = EmbeddingEncoder(model=mock_model)
        chunks = [f"code chunk {i}" for i in range(5)]
        encoder.encode(chunks)

        # Verify all chunks were passed to model
        call_args = mock_model.encode.call_args
        passed_texts = call_args[0][0]
        assert len(passed_texts) == 5

    def test_model_name_property_returns_correct_value(self):
        """Given EmbeddingEncoder with custom model name, when model_name is accessed, then correct value is returned."""
        from src.indexing.embedding_encoder import EmbeddingEncoder

        encoder = EmbeddingEncoder(model_name="custom-model")
        assert encoder.model_name == "custom-model"

    def test_model_name_property_default(self):
        """Given EmbeddingEncoder with default model, when model_name is accessed, then bge-code-v1 is returned."""
        from src.indexing.embedding_encoder import EmbeddingEncoder

        encoder = EmbeddingEncoder()
        assert encoder.model_name == "BAAI/bge-code-v1"
