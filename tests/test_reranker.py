"""Tests for Reranker — Neural Reranking via API (Feature #11).

Security: N/A — internal utility with no user-facing input.
"""

from __future__ import annotations

import logging
from unittest.mock import patch

import pytest

from src.query.scored_chunk import ScoredChunk


def _make_chunks(n: int, *, score_start: float = 0.5) -> list[ScoredChunk]:
    """Create n ScoredChunk instances with distinct IDs and content."""
    return [
        ScoredChunk(
            chunk_id=f"chunk-{i}",
            content_type="code",
            repo_id="repo-1",
            file_path=f"src/file_{i}.py",
            content=f"def function_{i}(): pass  # unique content {i}",
            score=score_start + i * 0.01,
            language="python",
            chunk_type="function",
            symbol=f"function_{i}",
        )
        for i in range(n)
    ]


def _mock_api_response(results: list[dict]) -> dict:
    """Build a DashScope-style API response."""
    return {
        "output": {"results": results},
        "usage": {"total_tokens": 100},
        "request_id": "test-request-id",
    }


# ---------- Happy Path Tests ----------


# [unit] — mock API, verify reranking logic
def test_rerank_candidates_returns_top6_rescored():
    """T1: Fused candidates → rerank returns top-6 re-scored via API."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(10)
    # API returns top-6 sorted by relevance_score descending
    api_results = [
        {"index": 9, "relevance_score": 0.95},
        {"index": 7, "relevance_score": 0.90},
        {"index": 5, "relevance_score": 0.85},
        {"index": 3, "relevance_score": 0.80},
        {"index": 1, "relevance_score": 0.75},
        {"index": 0, "relevance_score": 0.70},
    ]

    with patch("src.query.reranker.httpx.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = _mock_api_response(api_results)

        reranker = Reranker(
            model_name="qwen3-rerank",
            api_key="test-key",
            base_url="https://example.com/v1",
        )
        result = reranker.rerank("spring webclient timeout", candidates, top_k=6)

    assert len(result) == 6
    assert result[0].chunk_id == "chunk-9"
    assert result[0].score == pytest.approx(0.95)
    assert result[5].chunk_id == "chunk-0"
    assert result[5].score == pytest.approx(0.70)


# [unit] — verify scores are replaced with API scores
def test_rerank_scores_replaced():
    """T9: Returned chunk scores must be API relevance scores, not originals."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(3, score_start=100.0)  # original scores are high
    api_results = [
        {"index": 2, "relevance_score": 0.8},
        {"index": 1, "relevance_score": 0.5},
        {"index": 0, "relevance_score": 0.3},
    ]

    with patch("src.query.reranker.httpx.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = _mock_api_response(api_results)

        reranker = Reranker(api_key="test-key", base_url="https://example.com/v1")
        result = reranker.rerank("query", candidates, top_k=3)

    for chunk in result:
        assert chunk.score < 1.0, f"Score {chunk.score} looks like original, not API score"
    assert result[0].score == pytest.approx(0.8)


# [unit] — verify descending sort order
def test_rerank_descending_order():
    """T11: Results must be sorted descending by relevance score."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(5)
    # Return in non-sorted order from API
    api_results = [
        {"index": 0, "relevance_score": 0.3},
        {"index": 1, "relevance_score": 0.9},
        {"index": 2, "relevance_score": 0.1},
        {"index": 3, "relevance_score": 0.7},
        {"index": 4, "relevance_score": 0.5},
    ]

    with patch("src.query.reranker.httpx.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = _mock_api_response(api_results)

        reranker = Reranker(api_key="test-key", base_url="https://example.com/v1")
        result = reranker.rerank("query", candidates, top_k=5)

    for i in range(len(result) - 1):
        assert result[i].score >= result[i + 1].score


# [unit] — verify API request payload
def test_rerank_sends_correct_payload():
    """Verify the API is called with correct model, query, documents, top_n."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(3)
    api_results = [
        {"index": 0, "relevance_score": 0.9},
        {"index": 1, "relevance_score": 0.8},
        {"index": 2, "relevance_score": 0.7},
    ]

    with patch("src.query.reranker.httpx.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = _mock_api_response(api_results)

        reranker = Reranker(
            model_name="my-model",
            api_key="test-key",
            base_url="https://example.com/v1",
        )
        reranker.rerank("test query", candidates, top_k=2)

    call_kwargs = mock_post.call_args
    payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
    assert payload["model"] == "my-model"
    assert payload["input"]["query"] == "test query"
    assert len(payload["input"]["documents"]) == 3
    assert payload["parameters"]["top_n"] == 2


# ---------- Boundary Tests ----------


# [unit] — fewer candidates than top_k
def test_rerank_fewer_than_topk():
    """T3: 2 candidates with top_k=6 → returns all 2, no error."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(2)
    api_results = [
        {"index": 0, "relevance_score": 0.8},
        {"index": 1, "relevance_score": 0.3},
    ]

    with patch("src.query.reranker.httpx.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = _mock_api_response(api_results)

        reranker = Reranker(api_key="test-key", base_url="https://example.com/v1")
        result = reranker.rerank("query", candidates, top_k=6)

    assert len(result) == 2
    assert result[0].score == pytest.approx(0.8)
    assert result[1].score == pytest.approx(0.3)


# [unit] — single candidate
def test_rerank_single_candidate():
    """T4: 1 candidate → returns 1 chunk re-scored."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(1)
    api_results = [{"index": 0, "relevance_score": 0.95}]

    with patch("src.query.reranker.httpx.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = _mock_api_response(api_results)

        reranker = Reranker(api_key="test-key", base_url="https://example.com/v1")
        result = reranker.rerank("query", candidates, top_k=6)

    assert len(result) == 1
    assert result[0].score == pytest.approx(0.95)


# [unit] — empty candidates
def test_rerank_empty_candidates():
    """T5: Empty candidate list → returns []."""
    from src.query.reranker import Reranker

    reranker = Reranker(api_key="test-key", base_url="https://example.com/v1")
    result = reranker.rerank("query", [], top_k=6)
    assert result == []


# [unit] — top_k=1
def test_rerank_topk_one():
    """T8: top_k=1 with 5 candidates → returns exactly 1."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(5)
    api_results = [{"index": 3, "relevance_score": 0.99}]

    with patch("src.query.reranker.httpx.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = _mock_api_response(api_results)

        reranker = Reranker(api_key="test-key", base_url="https://example.com/v1")
        result = reranker.rerank("query", candidates, top_k=1)

    assert len(result) == 1
    assert result[0].chunk_id == "chunk-3"
    assert result[0].score == 0.99


# [unit] — threshold filtering
def test_rerank_threshold_filters_low_scores():
    """Candidates below threshold are excluded from results."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(5)
    api_results = [
        {"index": 0, "relevance_score": 0.9},
        {"index": 1, "relevance_score": 0.5},
        {"index": 2, "relevance_score": 0.2},  # below threshold
        {"index": 3, "relevance_score": 0.1},  # below threshold
        {"index": 4, "relevance_score": 0.05},  # below threshold
    ]

    with patch("src.query.reranker.httpx.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = _mock_api_response(api_results)

        reranker = Reranker(
            api_key="test-key",
            base_url="https://example.com/v1",
            threshold=0.3,
        )
        result = reranker.rerank("query", candidates, top_k=5)

    assert len(result) == 2
    assert result[0].score == pytest.approx(0.9)
    assert result[1].score == pytest.approx(0.5)


# [unit] — all below threshold → fallback
def test_rerank_all_below_threshold_fallback(caplog):
    """All candidates below threshold → fallback to fusion order."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(3, score_start=1.0)
    api_results = [
        {"index": 0, "relevance_score": 0.1},
        {"index": 1, "relevance_score": 0.05},
        {"index": 2, "relevance_score": 0.01},
    ]

    with patch("src.query.reranker.httpx.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = _mock_api_response(api_results)

        reranker = Reranker(
            api_key="test-key",
            base_url="https://example.com/v1",
            threshold=0.5,
        )
        with caplog.at_level(logging.WARNING):
            result = reranker.rerank("query", candidates, top_k=3)

    assert len(result) == 3
    assert result[0].chunk_id == "chunk-0"  # original order
    assert result[0].score == pytest.approx(1.0)  # original score
    assert any("threshold" in msg.lower() or "fallback" in msg.lower()
               for msg in caplog.messages)


# ---------- Error / Fallback Tests ----------


# [unit] — API key missing → fallback
def test_rerank_no_api_key_fallback(caplog, monkeypatch):
    """T6: No API key → rerank returns fusion-order candidates, logs warning."""
    from src.query.reranker import Reranker

    monkeypatch.delenv("RERANKER_API_KEY", raising=False)

    with caplog.at_level(logging.WARNING):
        reranker = Reranker(api_key="", base_url="https://example.com/v1")

    candidates = _make_chunks(10, score_start=1.0)
    with caplog.at_level(logging.WARNING):
        result = reranker.rerank("query", candidates, top_k=6)

    assert len(result) == 6
    assert result[0].chunk_id == "chunk-0"
    assert result[5].chunk_id == "chunk-5"
    assert result[0].score == pytest.approx(1.0)
    assert any("not configured" in msg.lower() or "not set" in msg.lower()
               for msg in caplog.messages)


# [unit] — API call failure → fallback
def test_rerank_api_failure_fallback(caplog):
    """T7: API call raises exception → fallback to fusion order, warning logged."""
    from src.query.reranker import Reranker

    with patch("src.query.reranker.httpx.post") as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")

        reranker = Reranker(api_key="test-key", base_url="https://example.com/v1")

    candidates = _make_chunks(5, score_start=2.0)
    with caplog.at_level(logging.WARNING):
        result = reranker.rerank("query", candidates, top_k=3)

    assert len(result) == 3
    assert result[0].chunk_id == "chunk-0"
    assert result[0].score == pytest.approx(2.0)
    assert any("failed" in msg.lower() or "fallback" in msg.lower()
               for msg in caplog.messages)


# [unit] — HTTP 500 → fallback
def test_rerank_http_error_fallback(caplog):
    """API returns HTTP 500 → fallback to fusion order."""
    from src.query.reranker import Reranker

    with patch("src.query.reranker.httpx.post") as mock_post:
        response = mock_post.return_value
        response.status_code = 500
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=None, response=response
        )

        reranker = Reranker(api_key="test-key", base_url="https://example.com/v1")

    candidates = _make_chunks(4, score_start=1.0)
    with caplog.at_level(logging.WARNING):
        result = reranker.rerank("query", candidates, top_k=2)

    assert len(result) == 2
    assert result[0].chunk_id == "chunk-0"
    assert result[0].score == pytest.approx(1.0)


# [unit] — OpenAI-compatible response format
def test_rerank_openai_compatible_format():
    """Handles OpenAI-compatible response format (results at top level)."""
    from src.query.reranker import Reranker

    candidates = _make_chunks(3)
    # OpenAI-compatible format: {"results": [...]} without "output" wrapper
    openai_response = {
        "results": [
            {"index": 2, "relevance_score": 0.9},
            {"index": 0, "relevance_score": 0.7},
            {"index": 1, "relevance_score": 0.5},
        ]
    }

    with patch("src.query.reranker.httpx.post") as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None
        mock_post.return_value.json.return_value = openai_response

        reranker = Reranker(api_key="test-key", base_url="https://example.com/v1")
        result = reranker.rerank("query", candidates, top_k=3)

    assert len(result) == 3
    assert result[0].chunk_id == "chunk-2"
    assert result[0].score == pytest.approx(0.9)


# ---------- Real Integration Tests ----------


import httpx  # noqa: E402 — needed for test_rerank_api_failure_fallback above


@pytest.mark.real
def test_reranker_real_api():
    """[integration] — calls real DashScope reranker API, verifies scoring."""
    import os
    from src.query.reranker import Reranker

    api_key = os.environ.get("RERANKER_API_KEY", "")
    if not api_key:
        pytest.skip("RERANKER_API_KEY not set")

    reranker = Reranker(
        model_name=os.environ.get("RERANKER_MODEL", "qwen3-rerank"),
        api_key=api_key,
        base_url=os.environ.get(
            "RERANKER_BASE_URL",
            "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank",
        ),
    )

    candidates = [
        ScoredChunk(
            chunk_id="c1", content_type="code", repo_id="r1",
            file_path="src/timeout.py", score=0.5,
            content="def configure_timeout(client, timeout_ms): client.timeout = timeout_ms",
            language="python", chunk_type="function", symbol="configure_timeout",
        ),
        ScoredChunk(
            chunk_id="c2", content_type="code", repo_id="r1",
            file_path="src/utils.py", score=0.4,
            content="def sort_list(items): return sorted(items)",
            language="python", chunk_type="function", symbol="sort_list",
        ),
        ScoredChunk(
            chunk_id="c3", content_type="code", repo_id="r1",
            file_path="src/webclient.py", score=0.3,
            content="class WebClient:\n    def __init__(self, base_url, timeout=30):\n        self.timeout = timeout",
            language="python", chunk_type="class", symbol="WebClient",
        ),
    ]

    result = reranker.rerank("webclient timeout configuration", candidates, top_k=3)

    # Should return results with real relevance scores
    assert len(result) >= 1
    assert len(result) <= 3
    # Scores should be real floats from the API
    for chunk in result:
        assert isinstance(chunk.score, float)
        assert 0.0 <= chunk.score <= 1.0
    # Results should be sorted descending
    for i in range(len(result) - 1):
        assert result[i].score >= result[i + 1].score
    # The most relevant result should be timeout or webclient related
    assert result[0].chunk_id in ("c1", "c3")


@pytest.mark.real
def test_reranker_real_api_few_candidates():
    """[integration] — real API with fewer candidates than top_k."""
    import os
    from src.query.reranker import Reranker

    api_key = os.environ.get("RERANKER_API_KEY", "")
    if not api_key:
        pytest.skip("RERANKER_API_KEY not set")

    reranker = Reranker(
        model_name=os.environ.get("RERANKER_MODEL", "qwen3-rerank"),
        api_key=api_key,
        base_url=os.environ.get(
            "RERANKER_BASE_URL",
            "https://dashscope.aliyuncs.com/api/v1/services/rerank/text-rerank/text-rerank",
        ),
    )

    candidates = [
        ScoredChunk(
            chunk_id="c1", content_type="code", repo_id="r1",
            file_path="src/main.py", score=0.5,
            content="def main(): print('hello')",
            language="python", chunk_type="function", symbol="main",
        ),
    ]

    result = reranker.rerank("hello world", candidates, top_k=6)
    assert len(result) == 1
    assert isinstance(result[0].score, float)
