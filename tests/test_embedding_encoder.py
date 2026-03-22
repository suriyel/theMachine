"""Tests for EmbeddingEncoder — Feature #7 Embedding Generation.

Test layers:
- [unit] Tests use a mock httpx response to avoid real API calls.
- [integration] Real test calls DashScope API (marked @pytest.mark.real).

Categories covered:
- Happy path: T1, T2, T4, T5, T18
- Error: T9, T12, T13, T19
- Boundary: T15, T20
- Security: N/A — internal indexing component with no user-facing input
"""

import json

import httpx
import numpy as np
import pytest
from unittest.mock import MagicMock, patch

from src.indexing.embedding_encoder import EmbeddingEncoder
from src.indexing.exceptions import EmbeddingModelError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_api_response(n: int, dim: int = 1024) -> httpx.Response:
    """Create a mock httpx.Response with n embeddings of given dimension."""
    data = [
        {"index": i, "embedding": np.random.rand(dim).tolist()}
        for i in range(n)
    ]
    body = json.dumps({
        "model": "text-embedding-v3",
        "data": data,
        "usage": {"prompt_tokens": n * 5, "total_tokens": n * 5},
    }).encode()
    request = httpx.Request("POST", "https://test.example.com/v1/embeddings")
    return httpx.Response(status_code=200, content=body, headers={
        "content-type": "application/json",
    }, request=request)


@pytest.fixture
def encoder():
    """EmbeddingEncoder with test API key."""
    return EmbeddingEncoder(
        model_name="text-embedding-v3",
        api_key="test-key-123",
        base_url="https://test.example.com/v1",
    )


# ---------------------------------------------------------------------------
# T1: Happy path — encode_batch returns correct shape for 10 texts
# [unit]
# ---------------------------------------------------------------------------

def test_encode_batch_returns_correct_count_and_dimensions(encoder):
    """VS-1: Given 10 code chunks, encode_documents produces 10 vectors of 1024 dims."""
    texts = [f"def function_{i}(): pass" for i in range(10)]

    with patch("src.indexing.embedding_encoder.httpx.post") as mock_post:
        # Will be called in batches of 6 (6 + 4)
        mock_post.side_effect = [
            _make_api_response(6),
            _make_api_response(4),
        ]
        result = encoder.encode_batch(texts)

    assert len(result) == 10, f"Expected 10 vectors, got {len(result)}"
    for i, vec in enumerate(result):
        assert vec.shape == (1024,), f"Vector {i} has shape {vec.shape}, expected (1024,)"
        assert vec.dtype == np.float32, f"Vector {i} has dtype {vec.dtype}, expected float32"


# ---------------------------------------------------------------------------
# T2: Happy path — encode_query applies prefix and returns single vector
# [unit]
# ---------------------------------------------------------------------------

def test_encode_query_prepends_prefix_and_returns_1024_dim(encoder):
    """VS-2: Given query 'how to configure timeout', returns 1024-dim vector with prefix."""
    query = "how to configure timeout"

    with patch("src.indexing.embedding_encoder.httpx.post") as mock_post:
        mock_post.return_value = _make_api_response(1)
        result = encoder.encode_query(query)

    assert result.shape == (1024,), f"Expected (1024,), got {result.shape}"
    assert result.dtype == np.float32

    # Verify the API was called with the prefix prepended
    call_args = mock_post.call_args
    payload = call_args[1]["json"]
    assert len(payload["input"]) == 1
    assert payload["input"][0].startswith("Represent this code search query: ")
    assert query in payload["input"][0]


# ---------------------------------------------------------------------------
# T4: Happy path — large batch (10000 texts) all encoded via batching
# [unit]
# ---------------------------------------------------------------------------

def test_encode_batch_large_batch_10000(encoder):
    """FR-005 AC-2: Given 10,000 chunks, all vectors produced via batched API calls."""
    texts = [f"code chunk {i}" for i in range(10000)]

    with patch("src.indexing.embedding_encoder.httpx.post") as mock_post:
        # 10000 / 6 = 1667 batches (last batch has 4)
        def make_response(*args, **kwargs):
            n = len(kwargs.get("json", {}).get("input", []))
            return _make_api_response(n)
        mock_post.side_effect = make_response
        result = encoder.encode_batch(texts)

    assert len(result) == 10000, f"Expected 10000 vectors, got {len(result)}"
    assert result[0].shape == (1024,)
    assert result[9999].shape == (1024,)


# ---------------------------------------------------------------------------
# T5: Happy path — is_query=True prepends prefix to all texts
# [unit]
# ---------------------------------------------------------------------------

def test_encode_batch_with_is_query_prepends_prefix(encoder):
    """encode_batch with is_query=True prepends query prefix to every text."""
    texts = ["query one", "query two"]

    with patch("src.indexing.embedding_encoder.httpx.post") as mock_post:
        mock_post.return_value = _make_api_response(2)
        encoder.encode_batch(texts, is_query=True)

    call_args = mock_post.call_args
    payload = call_args[1]["json"]
    prefix = "Represent this code search query: "
    for t in payload["input"]:
        assert t.startswith(prefix), f"Text '{t}' missing query prefix"


# ---------------------------------------------------------------------------
# T9: Error — API returns error status
# [unit]
# ---------------------------------------------------------------------------

def test_encode_batch_api_failure_raises_embedding_model_error(encoder):
    """FR-005 AC-3: API error raises EmbeddingModelError, no partial output."""
    with patch("src.indexing.embedding_encoder.httpx.post") as mock_post:
        request = httpx.Request("POST", "https://test.example.com/v1/embeddings")
        error_resp = httpx.Response(
            status_code=500,
            content=b'{"error": "Internal Server Error"}',
            headers={"content-type": "application/json"},
            request=request,
        )
        mock_post.return_value = error_resp

        with pytest.raises(EmbeddingModelError, match="Model inference failed"):
            encoder.encode_batch(["some code"])


# ---------------------------------------------------------------------------
# T12: Error — encode_batch with empty list raises ValueError
# [unit]
# ---------------------------------------------------------------------------

def test_encode_batch_empty_texts_raises_value_error(encoder):
    """Empty texts list must raise ValueError."""
    with pytest.raises(ValueError, match="texts must be non-empty"):
        encoder.encode_batch([])


# ---------------------------------------------------------------------------
# T13: Error — encode_query with empty string raises ValueError
# [unit]
# ---------------------------------------------------------------------------

def test_encode_query_empty_string_raises_value_error(encoder):
    """Empty query string must raise ValueError."""
    with pytest.raises(ValueError, match="query must be non-empty"):
        encoder.encode_query("")


# ---------------------------------------------------------------------------
# T15: Boundary — single text encodes to list of 1 vector
# [unit]
# ---------------------------------------------------------------------------

def test_encode_batch_single_text_returns_one_vector(encoder):
    """Boundary: single text → list with 1 vector of 1024-dim."""
    with patch("src.indexing.embedding_encoder.httpx.post") as mock_post:
        mock_post.return_value = _make_api_response(1)
        result = encoder.encode_batch(["single chunk"])

    assert len(result) == 1
    assert result[0].shape == (1024,)
    assert result[0].dtype == np.float32


# ---------------------------------------------------------------------------
# T18: Happy path — constructor defaults from env vars
# [unit]
# ---------------------------------------------------------------------------

def test_encoder_init_defaults():
    """Constructor reads from env vars and sets query_prefix correctly."""
    with patch.dict("os.environ", {
        "EMBEDDING_MODEL": "test-model",
        "EMBEDDING_API_KEY": "test-key",
        "EMBEDDING_BASE_URL": "https://test.api.com/v1",
    }):
        enc = EmbeddingEncoder()
    assert enc._model == "test-model"
    assert enc._query_prefix == "Represent this code search query: "
    assert enc._dimensions == 1024
    assert enc._base_url == "https://test.api.com/v1"


# ---------------------------------------------------------------------------
# T19: Error — missing API key raises EmbeddingModelError
# [unit]
# ---------------------------------------------------------------------------

def test_encoder_init_missing_api_key_raises_error():
    """Missing API key should raise EmbeddingModelError."""
    import os

    saved = os.environ.pop("EMBEDDING_API_KEY", None)
    try:
        with pytest.raises(EmbeddingModelError, match="EMBEDDING_API_KEY is required"):
            EmbeddingEncoder(api_key="", model_name="test")
    finally:
        if saved is not None:
            os.environ["EMBEDDING_API_KEY"] = saved


# ---------------------------------------------------------------------------
# T20: Boundary — empty string text element encodes without crash
# [unit]
# ---------------------------------------------------------------------------

def test_encode_batch_empty_string_element_succeeds(encoder):
    """Empty string as text element should encode without crash."""
    with patch("src.indexing.embedding_encoder.httpx.post") as mock_post:
        mock_post.return_value = _make_api_response(1)
        result = encoder.encode_batch([""])

    assert len(result) == 1
    assert result[0].shape == (1024,)


# ---------------------------------------------------------------------------
# T21: Error — API returns wrong number of embeddings
# [unit]
# ---------------------------------------------------------------------------

def test_encode_batch_wrong_count_raises_error(encoder):
    """API returning wrong number of embeddings should raise EmbeddingModelError."""
    with patch("src.indexing.embedding_encoder.httpx.post") as mock_post:
        # Send 3 texts but API returns 2 embeddings
        mock_post.return_value = _make_api_response(2)
        with pytest.raises(EmbeddingModelError, match="expected 3 embeddings, got 2"):
            encoder.encode_batch(["a", "b", "c"])


# ---------------------------------------------------------------------------
# T22: Error — network connection error
# [unit]
# ---------------------------------------------------------------------------

def test_encode_batch_network_error_raises_embedding_model_error(encoder):
    """Network error raises EmbeddingModelError."""
    with patch("src.indexing.embedding_encoder.httpx.post") as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        with pytest.raises(EmbeddingModelError, match="Model inference failed"):
            encoder.encode_batch(["some code"])


# ---------------------------------------------------------------------------
# T23: Happy path — API response sorted by index
# [unit]
# ---------------------------------------------------------------------------

def test_encode_batch_sorts_by_index(encoder):
    """API may return embeddings out of order — encoder must sort by index."""
    data = [
        {"index": 1, "embedding": [0.0] * 1024},
        {"index": 0, "embedding": [1.0] * 1024},
    ]
    body = json.dumps({"model": "test", "data": data, "usage": {}}).encode()
    request = httpx.Request("POST", "https://test.example.com/v1/embeddings")
    resp = httpx.Response(200, content=body, headers={"content-type": "application/json"}, request=request)

    with patch("src.indexing.embedding_encoder.httpx.post", return_value=resp):
        result = encoder.encode_batch(["text_0", "text_1"])

    # Index 0 should have [1.0, ...], index 1 should have [0.0, ...]
    assert result[0][0] == 1.0, "First vector should correspond to index 0"
    assert result[1][0] == 0.0, "Second vector should correspond to index 1"


# ---------------------------------------------------------------------------
# Real test: actual DashScope API encoding produces correct dimensions
# [integration]
# ---------------------------------------------------------------------------

@pytest.mark.real
def test_real_dashscope_embedding_api():
    """Real test: verify DashScope text-embedding-v3 produces 1024-dim vectors.

    feature #7 — Embedding Generation
    """
    import os

    api_key = os.environ.get("EMBEDDING_API_KEY", "")
    if not api_key:
        pytest.skip("EMBEDDING_API_KEY not set")

    encoder = EmbeddingEncoder()
    texts = ["def hello(): pass", "class Foo: pass"]
    vectors = encoder.encode_batch(texts)

    assert len(vectors) == 2, f"Expected 2 vectors, got {len(vectors)}"
    for i, vec in enumerate(vectors):
        assert vec.shape == (1024,), f"Vector {i} shape={vec.shape}, expected (1024,)"
        assert vec.dtype == np.float32, f"Vector {i} dtype={vec.dtype}"

    # Query encoding with prefix
    query_vec = encoder.encode_query("how to configure timeout")
    assert query_vec.shape == (1024,)
    assert query_vec.dtype == np.float32

    # Verify vectors are different (not all zeros or identical)
    assert not np.allclose(vectors[0], vectors[1]), "Vectors should differ for different inputs"
