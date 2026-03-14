"""Embedding encoder using sentence-transformers for code embeddings."""

from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


class EmbeddingEncoder:
    """Generates embeddings for code chunks using bge-code model.

    Attributes:
        model_name: Name of the sentence-transformers model (default: BAAI/bge-code-v1)
        dimension: Embedding vector dimension (1024 for bge-code-v1)
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-code-v1",
        model: "SentenceTransformer | None" = None,
    ):
        """Initialize the embedding encoder.

        Args:
            model_name: Name of the sentence-transformers model to use.
            model: Optional pre-loaded model (for testing).
        """
        self._model_name = model_name
        self._model = model
        self._dimension = 1024  # bge-code-v1 dimension

    @property
    def model_name(self) -> str:
        """Get the model name."""
        return self._model_name

    @property
    def dimension(self) -> int:
        """Get the embedding dimension."""
        return self._dimension

    def _get_model(self):
        """Lazy load the model."""
        if self._model is None:
            # Lazy import to allow tests to run without downloading model
            from sentence_transformers import SentenceTransformer
            # Try GPU first, fallback to CPU
            try:
                self._model = SentenceTransformer(self._model_name, device="cuda")
            except Exception:
                self._model = SentenceTransformer(self._model_name, device="cpu")
        return self._model

    def encode(self, texts: List[str]) -> List[List[float]]:
        """Encode a list of text chunks into embeddings.

        Args:
            texts: List of text strings to encode.

        Returns:
            List of embedding vectors (each is a list of floats).
        """
        if not texts:
            return []

        model = self._get_model()
        embeddings = model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def encode_query(self, query: str) -> List[float]:
        """Encode a single query string into an embedding.

        Adds a query prefix specific to bge-code model for better results.

        Args:
            query: Query string to encode.

        Returns:
            Embedding vector as a list of floats.
        """
        # bge-code-v1 uses 'representative' prefix for queries
        prefixed_query = f"Represent this code for semantic search: {query}"
        model = self._get_model()
        embedding = model.encode(prefixed_query, convert_to_numpy=True)
        # Single query returns 2D array, flatten to 1D
        embedding = embedding.flatten()
        return embedding.tolist()
