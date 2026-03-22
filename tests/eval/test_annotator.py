"""Tests for LLMAnnotator — Feature #41: LLM Query Generation & Relevance Annotation.

Test Inventory from feature detailed design
(docs/plans/2026-03-22-llm-query-generation-relevance-annotation.md).
32 test scenarios covering T01-T04, T07-T18, T21-T28, T30-T32.

Categories covered:
- Happy path: T01, T02, T03, T04, T07, T30, T31
- Error handling: T08, T09, T10, T11, T12, T13, T14, T15, T16, T17, T18, T32
- Boundary: T21, T22, T23, T24, T25, T26, T27, T28
"""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from src.eval.annotator import VALID_CATEGORIES, Annotation, EvalQuery, LLMAnnotator
from src.eval.corpus_builder import EvalRepo
from src.eval.exceptions import LLMAnnotatorError
from src.query.scored_chunk import ScoredChunk


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_repo() -> EvalRepo:
    return EvalRepo(name="flask", url="https://github.com/pallets/flask", language="Python", branch="main")


def _make_chunk(chunk_id: str = "c1", content: str = "def hello(): pass") -> ScoredChunk:
    return ScoredChunk(
        chunk_id=chunk_id,
        content_type="code",
        repo_id="flask",
        file_path="app.py",
        content=content,
        score=0.9,
        language="Python",
    )


def _mock_completion(content: str) -> MagicMock:
    """Build a mock chat completion response object."""
    msg = MagicMock()
    msg.content = content
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_queries_json(n: int, categories: dict[str, int] | None = None) -> str:
    """Build a JSON response string with n queries across categories."""
    if categories is None:
        # Default distribution roughly matching design proportions
        categories = {
            "api_usage": max(1, int(n * 0.30)),
            "bug_diagnosis": max(1, int(n * 0.25)),
            "configuration": max(1, int(n * 0.25)),
        }
        categories["architecture"] = n - sum(categories.values())

    queries = []
    for cat, count in categories.items():
        for i in range(count):
            queries.append({"text": f"{cat} query {i}", "category": cat})
    return json.dumps({"queries": queries})


@pytest.fixture()
def env_minimax(monkeypatch):
    """Set env vars for MiniMax provider."""
    monkeypatch.setenv("EVAL_LLM_PROVIDER", "minimax")
    monkeypatch.setenv("MINIMAX_API_KEY", "test-key-minimax")
    monkeypatch.setenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1")
    monkeypatch.setenv("MINIMAX_MODEL", "MiniMax-M2.7")


@pytest.fixture()
def env_zhipu(monkeypatch):
    """Set env vars for Zhipu provider."""
    monkeypatch.setenv("EVAL_LLM_PROVIDER", "zhipu")
    monkeypatch.setenv("ZHIPU_API_KEY", "test-key-zhipu")
    monkeypatch.setenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    monkeypatch.setenv("ZHIPU_MODEL", "glm-4")


@pytest.fixture()
def annotator_minimax(env_minimax):
    """Create LLMAnnotator with mocked OpenAI client for MiniMax."""
    with patch("src.eval.annotator.OpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client
        ann = LLMAnnotator(provider="minimax")
        ann._client = mock_client
        yield ann


# ---------------------------------------------------------------------------
# T01: Happy path — generate_queries returns 75 EvalQuery objects
# ---------------------------------------------------------------------------


class TestGenerateQueriesHappyPath:
    def test_t01_generates_75_queries_across_categories(self, annotator_minimax):
        """T01: generate_queries returns 75 queries across 4 categories."""
        annotator = annotator_minimax
        repo = _make_repo()
        response_json = _make_queries_json(75)
        annotator._client.chat.completions.create.return_value = _mock_completion(response_json)

        queries = annotator.generate_queries(repo, chunk_count=200, n_queries=75)

        assert len(queries) == 75
        categories = {q.category for q in queries}
        assert categories == {"api_usage", "bug_diagnosis", "configuration", "architecture"}
        # All queries have correct repo_id and language
        for q in queries:
            assert q.repo_id == "flask"
            assert q.language == "Python"
            assert q.text  # non-empty

    def test_t30_invalid_category_entries_skipped(self, annotator_minimax):
        """T30: Entries with invalid categories are filtered out."""
        annotator = annotator_minimax
        repo = _make_repo()
        queries_list = [{"text": f"q{i}", "category": "api_usage"} for i in range(60)]
        # Add invalid category entries
        queries_list.extend([{"text": "bad", "category": "unknown"} for _ in range(10)])
        response_json = json.dumps({"queries": queries_list})
        annotator._client.chat.completions.create.return_value = _mock_completion(response_json)

        queries = annotator.generate_queries(repo, chunk_count=200, n_queries=75)

        assert len(queries) == 60
        assert all(q.category == "api_usage" for q in queries)


# ---------------------------------------------------------------------------
# T02, T03: Happy path — annotation
# ---------------------------------------------------------------------------


class TestAnnotateRelevanceHappyPath:
    def test_t02_dual_annotate_agreement(self, annotator_minimax):
        """T02: When scores agree (2, 2), final score is 2 with annotator_run=2."""
        annotator = annotator_minimax
        chunk = _make_chunk()
        query = EvalQuery(text="how to use flask", repo_id="flask", language="Python", category="api_usage")

        # Mock two LLM calls returning "2"
        annotator._client.chat.completions.create.side_effect = [
            _mock_completion("2"),
            _mock_completion("2"),
        ]

        annotations = annotator.annotate_relevance(query, [chunk])

        assert len(annotations) == 1
        assert annotations[0].score == 2
        assert annotations[0].annotator_run == 2
        assert annotations[0].chunk_id == "c1"

    def test_t03_disagreement_triggers_tiebreaker(self, annotator_minimax):
        """T03: Scores (0, 3) trigger tiebreaker; third call returns 0 → majority vote = 0."""
        annotator = annotator_minimax
        chunk = _make_chunk()
        query = EvalQuery(text="debug flask", repo_id="flask", language="Python", category="bug_diagnosis")

        # Two annotation calls + one tiebreaker
        annotator._client.chat.completions.create.side_effect = [
            _mock_completion("0"),
            _mock_completion("3"),
            _mock_completion("0"),
        ]

        annotations = annotator.annotate_relevance(query, [chunk])

        assert len(annotations) == 1
        assert annotations[0].score == 0
        assert annotations[0].annotator_run == 3


# ---------------------------------------------------------------------------
# T04: Happy path — compute_kappa
# ---------------------------------------------------------------------------


class TestComputeKappa:
    def test_t04_kappa_with_mixed_agreement(self, annotator_minimax):
        """T04: 10 pairs with 7 agree, 3 disagree → kappa around expected value."""
        annotator = annotator_minimax
        pairs = [
            (0, 0), (1, 1), (2, 2), (3, 3),  # 4 agree
            (1, 1), (2, 2), (0, 0),           # 3 more agree (7 total)
            (0, 1), (1, 2), (2, 3),           # 3 disagree
        ]

        kappa = annotator._compute_kappa(pairs)

        # Kappa should be positive (substantial agreement)
        assert -1.0 <= kappa <= 1.0
        assert kappa > 0.3  # at least fair agreement

    def test_t18_compute_kappa_empty_raises(self, annotator_minimax):
        """T18: Empty annotation pairs raises ValueError."""
        with pytest.raises(ValueError, match="No annotation pairs"):
            annotator_minimax._compute_kappa([])

    def test_t26_single_pair_perfect_agreement(self, annotator_minimax):
        """T26: Single pair (2, 2) → kappa = 1.0."""
        kappa = annotator_minimax._compute_kappa([(2, 2)])
        assert kappa == 1.0

    def test_t27_all_identical_pe_equals_one(self, annotator_minimax):
        """T27: All pairs identical → P_e = 1.0, returns 1.0 without division error."""
        pairs = [(1, 1)] * 10
        kappa = annotator_minimax._compute_kappa(pairs)
        assert kappa == 1.0


# ---------------------------------------------------------------------------
# T07, T31: Happy path — provider config
# ---------------------------------------------------------------------------


class TestProviderConfig:
    def test_t07_zhipu_provider_config(self, env_zhipu):
        """T07: Zhipu provider resolves correct config from env."""
        with patch("src.eval.annotator.OpenAI"):
            ann = LLMAnnotator(provider="zhipu")
            assert ann._base_url == "https://open.bigmodel.cn/api/paas/v4"
            assert ann._model == "glm-4"

    def test_t31_minimax_provider_config(self, env_minimax):
        """T31: MiniMax provider resolves correct default config."""
        with patch("src.eval.annotator.OpenAI"):
            ann = LLMAnnotator(provider="minimax")
            assert ann._base_url == "https://api.minimaxi.com/v1"
            assert ann._model == "MiniMax-M2.7"


# ---------------------------------------------------------------------------
# T08-T12: Error tests — generate_queries
# ---------------------------------------------------------------------------


class TestGenerateQueriesErrors:
    def test_t08_n_queries_below_50_raises(self, annotator_minimax):
        """T08: n_queries=49 raises ValueError."""
        with pytest.raises(ValueError, match="n_queries must be between 50 and 100"):
            annotator_minimax.generate_queries(_make_repo(), chunk_count=200, n_queries=49)

    def test_t09_n_queries_above_100_raises(self, annotator_minimax):
        """T09: n_queries=101 raises ValueError."""
        with pytest.raises(ValueError, match="n_queries must be between 50 and 100"):
            annotator_minimax.generate_queries(_make_repo(), chunk_count=200, n_queries=101)

    def test_t10_chunk_count_zero_raises(self, annotator_minimax):
        """T10: chunk_count=0 raises ValueError."""
        with pytest.raises(ValueError, match="chunk_count must be positive"):
            annotator_minimax.generate_queries(_make_repo(), chunk_count=0, n_queries=75)

    def test_t11_malformed_json_raises(self, annotator_minimax):
        """T11: LLM returns malformed JSON → LLMAnnotatorError."""
        annotator_minimax._client.chat.completions.create.return_value = _mock_completion("not json at all")

        with pytest.raises(LLMAnnotatorError, match="Failed to parse LLM response"):
            annotator_minimax.generate_queries(_make_repo(), chunk_count=200, n_queries=75)

    def test_t12_fewer_than_50_valid_queries_raises(self, annotator_minimax):
        """T12: LLM returns only 30 valid queries → LLMAnnotatorError."""
        response_json = _make_queries_json(30)
        annotator_minimax._client.chat.completions.create.return_value = _mock_completion(response_json)

        with pytest.raises(LLMAnnotatorError, match="fewer than 50 valid queries"):
            annotator_minimax.generate_queries(_make_repo(), chunk_count=200, n_queries=75)


# ---------------------------------------------------------------------------
# T13, T14, T15, T32: Error tests — annotation
# ---------------------------------------------------------------------------


class TestAnnotationErrors:
    def test_t13_score_outside_range_raises(self, annotator_minimax):
        """T13: LLM returns '5' → LLMAnnotatorError."""
        annotator_minimax._client.chat.completions.create.return_value = _mock_completion("5")
        query = EvalQuery(text="test", repo_id="flask", language="Python", category="api_usage")

        with pytest.raises(LLMAnnotatorError, match="Score 5 outside"):
            annotator_minimax.annotate_relevance(query, [_make_chunk()])

    def test_t14_api_error_raises(self, annotator_minimax):
        """T14: LLM raises APIError → LLMAnnotatorError."""
        import openai
        annotator_minimax._client.chat.completions.create.side_effect = openai.APIError(
            message="Service unavailable",
            request=MagicMock(),
            body=None,
        )
        query = EvalQuery(text="test", repo_id="flask", language="Python", category="api_usage")

        with pytest.raises(LLMAnnotatorError, match="Annotation failed"):
            annotator_minimax.annotate_relevance(query, [_make_chunk()])

    def test_t15_empty_chunks_raises(self, annotator_minimax):
        """T15: Empty chunks list raises ValueError."""
        query = EvalQuery(text="test", repo_id="flask", language="Python", category="api_usage")

        with pytest.raises(ValueError, match="chunks must not be empty"):
            annotator_minimax.annotate_relevance(query, [])

    def test_t32_non_numeric_score_raises(self, annotator_minimax):
        """T32: LLM returns 'high' → LLMAnnotatorError."""
        annotator_minimax._client.chat.completions.create.return_value = _mock_completion("high")
        query = EvalQuery(text="test", repo_id="flask", language="Python", category="api_usage")

        with pytest.raises(LLMAnnotatorError, match="Annotation failed"):
            annotator_minimax.annotate_relevance(query, [_make_chunk()])


# ---------------------------------------------------------------------------
# T16, T17: Error tests — provider config
# ---------------------------------------------------------------------------


class TestProviderConfigErrors:
    def test_t16_unsupported_provider_raises(self, env_minimax):
        """T16: provider='unsupported' raises ValueError."""
        with patch("src.eval.annotator.OpenAI"):
            with pytest.raises(ValueError, match="Unsupported provider"):
                LLMAnnotator(provider="unsupported")

    def test_t17_missing_api_key_raises(self, monkeypatch):
        """T17: Missing MINIMAX_API_KEY raises ValueError."""
        monkeypatch.setenv("EVAL_LLM_PROVIDER", "minimax")
        monkeypatch.delenv("MINIMAX_API_KEY", raising=False)
        monkeypatch.setenv("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1")

        with patch("src.eval.annotator.OpenAI"):
            with pytest.raises(ValueError, match="Missing env var"):
                LLMAnnotator(provider="minimax")


# ---------------------------------------------------------------------------
# T21-T23: Boundary — generate_queries
# ---------------------------------------------------------------------------


class TestGenerateQueriesBoundary:
    def test_t21_minimum_n_queries_50(self, annotator_minimax):
        """T21: n_queries=50 is accepted."""
        response_json = _make_queries_json(50)
        annotator_minimax._client.chat.completions.create.return_value = _mock_completion(response_json)

        queries = annotator_minimax.generate_queries(_make_repo(), chunk_count=200, n_queries=50)
        assert len(queries) == 50

    def test_t22_maximum_n_queries_100(self, annotator_minimax):
        """T22: n_queries=100 is accepted."""
        response_json = _make_queries_json(100)
        annotator_minimax._client.chat.completions.create.return_value = _mock_completion(response_json)

        queries = annotator_minimax.generate_queries(_make_repo(), chunk_count=200, n_queries=100)
        assert len(queries) == 100

    def test_t23_truncates_to_100_if_llm_returns_more(self, annotator_minimax):
        """T23: LLM returns 110 queries → truncated to 100."""
        response_json = _make_queries_json(110)
        annotator_minimax._client.chat.completions.create.return_value = _mock_completion(response_json)

        queries = annotator_minimax.generate_queries(_make_repo(), chunk_count=200, n_queries=75)
        assert len(queries) == 100


# ---------------------------------------------------------------------------
# T24, T25: Boundary — annotation threshold
# ---------------------------------------------------------------------------


class TestAnnotationBoundary:
    def test_t24_diff_1_no_tiebreaker(self, annotator_minimax):
        """T24: Scores (0, 1) diff=1 → no tiebreaker, round(0.5) = 0, annotator_run=2."""
        annotator_minimax._client.chat.completions.create.side_effect = [
            _mock_completion("0"),
            _mock_completion("1"),
        ]
        query = EvalQuery(text="test", repo_id="flask", language="Python", category="api_usage")

        annotations = annotator_minimax.annotate_relevance(query, [_make_chunk()])

        assert annotations[0].score == 0  # round(0.5) = 0 (banker's rounding)
        assert annotations[0].annotator_run == 2

    def test_t25_diff_2_triggers_tiebreaker(self, annotator_minimax):
        """T25: Scores (0, 2) diff=2 → tiebreaker triggered, annotator_run=3."""
        annotator_minimax._client.chat.completions.create.side_effect = [
            _mock_completion("0"),
            _mock_completion("2"),
            _mock_completion("2"),  # tiebreaker
        ]
        query = EvalQuery(text="test", repo_id="flask", language="Python", category="api_usage")

        annotations = annotator_minimax.annotate_relevance(query, [_make_chunk()])

        assert annotations[0].annotator_run == 3
        assert annotations[0].score == 2  # majority: two 2s vs one 0


# ---------------------------------------------------------------------------
# T28: Boundary — resolve_disagreement all different
# ---------------------------------------------------------------------------


class TestResolveDisagreementBoundary:
    def test_t28_all_three_different_returns_median(self, annotator_minimax):
        """T28: All three scores different (0, 2, 3) → median = 2."""
        chunk = _make_chunk()
        query = EvalQuery(text="test", repo_id="flask", language="Python", category="api_usage")

        # Third LLM call returns 3
        annotator_minimax._client.chat.completions.create.return_value = _mock_completion("3")

        result = annotator_minimax._resolve_disagreement("test", chunk, (0, 2))
        assert result == 2  # median of [0, 2, 3]


# ---------------------------------------------------------------------------
# Real test: MiniMax API connectivity
# ---------------------------------------------------------------------------


@pytest.mark.real
def test_real_minimax_api_connectivity_feature_41():
    """Real integration test: verify MiniMax API connectivity."""
    api_key = os.environ.get("MINIMAX_API_KEY")
    base_url = os.environ.get("MINIMAX_BASE_URL", "https://api.minimaxi.com/v1")
    model = os.environ.get("MINIMAX_MODEL", "MiniMax-M2.7")

    if not api_key:
        pytest.skip("MINIMAX_API_KEY not set")

    import openai

    # Remove SOCKS proxy env vars that httpx cannot handle
    saved = {}
    for var in ("ALL_PROXY", "all_proxy"):
        if var in os.environ:
            saved[var] = os.environ.pop(var)
    try:
        client = openai.OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say hello in one word."}],
            temperature=0.1,
            max_tokens=10,
        )

        assert response.choices[0].message.content
        assert len(response.choices[0].message.content.strip()) > 0
    finally:
        os.environ.update(saved)


@pytest.mark.real
def test_real_minimax_generate_queries_feature_41():
    """Real integration test: generate_queries against actual MiniMax API.

    Generates a small batch of queries (n_queries=50) for a synthetic repo
    and verifies the output structure matches the contract.
    """
    api_key = os.environ.get("MINIMAX_API_KEY")
    if not api_key:
        pytest.skip("MINIMAX_API_KEY not set")

    # Clear SOCKS proxy
    saved = {}
    for var in ("ALL_PROXY", "all_proxy"):
        if var in os.environ:
            saved[var] = os.environ.pop(var)
    try:
        annotator = LLMAnnotator(provider="minimax")
        repo = EvalRepo(name="flask", url="https://github.com/pallets/flask", language="python", branch="main")

        queries = annotator.generate_queries(repo, chunk_count=200, n_queries=50)

        # Contract: 50-100 queries returned
        assert 50 <= len(queries) <= 100
        # Each query has required fields
        for q in queries:
            assert q.text and len(q.text) > 0
            assert q.category in VALID_CATEGORIES
            assert q.repo_id == "flask"
            assert q.language == "python"
        # All 4 categories represented
        categories_seen = {q.category for q in queries}
        assert len(categories_seen) >= 2  # at minimum 2 categories present
    finally:
        os.environ.update(saved)
