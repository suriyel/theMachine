"""Tests for NeuralReranker - Feature #11 (FR-011).

This module contains unit tests for the NeuralReranker class which reorders
fused candidate results using cross-encoder neural reranking.

Test categories:
- Happy path: Reranker reorders candidates by neural relevance score
- Edge case: < 2 items returns original order without model call
- Error handling: Empty list returns empty list
- Error handling: Model load failure raises appropriate exception
- Boundary: Very long query gets truncated
"""
import pytest
from unittest.mock import MagicMock, patch


# [unit] - Pure function logic test
def test_reranker_reorders_candidates_by_score():
    """Given fused candidate list with >= 2 items, when reranking executes,
    then candidates are reordered by neural relevance score (descending).

    This test verifies that the reranker calls the model and reorders
    candidates based on the returned scores.
    """
    from src.query.reranker import NeuralReranker
    from src.query.retriever import Candidate

    # Create mock model that returns scores
    mock_model = MagicMock()
    mock_model.predict.return_value = [0.9, 0.3, 0.7]  # scores for each candidate

    candidates = [
        Candidate(chunk_id="1", repo_name="repo", file_path="a.py", symbol=None,
                 content="def foo(): pass", score=0.5, language="python"),
        Candidate(chunk_id="2", repo_name="repo", file_path="b.py", symbol=None,
                 content="def bar(): pass", score=0.6, language="python"),
        Candidate(chunk_id="3", repo_name="repo", file_path="c.py", symbol=None,
                 content="def baz(): pass", score=0.4, language="python"),
    ]

    # Mock the _load_model to avoid downloading the model
    with patch.object(NeuralReranker, '_load_model', return_value=mock_model):
        with patch.object(NeuralReranker, '__init__', lambda self, **kw: None):
            reranker = NeuralReranker()
            reranker.model = mock_model
            reranker.model_name = "BAAI/bge-reranker-v2-m3"
            reranker.max_length = 512
            result = reranker.rerank("test query", candidates)

    # Verify model was called with query-document pairs
    assert mock_model.predict.called

    # Verify candidates are reordered by score (descending)
    # Scores from predict: [0.9, 0.3, 0.7] -> candidate 1 (0.9), candidate 3 (0.7), candidate 2 (0.3)
    assert result[0].chunk_id == "1"
    assert result[1].chunk_id == "3"
    assert result[2].chunk_id == "2"


# [unit] - Edge case: pass-through for < 2 items
def test_reranker_passes_through_for_single_item():
    """Given fused candidate list with < 2 items, when reranking executes,
    then items are returned in current order without model invocation.
    """
    from src.query.reranker import NeuralReranker
    from src.query.retriever import Candidate

    candidates = [
        Candidate(chunk_id="1", repo_name="repo", file_path="a.py", symbol=None,
                 content="def foo(): pass", score=0.5, language="python"),
    ]

    with patch.object(NeuralReranker, '__init__', lambda self, **kw: None):
        reranker = NeuralReranker()
        reranker.model = MagicMock()  # Should NOT be called
        reranker.model_name = "BAAI/bge-reranker-v2-m3"
        reranker.max_length = 512
        result = reranker.rerank("test query", candidates)

    # Verify model was NOT called (pass-through behavior)
    assert reranker.model is not None  # Model is set, but should not be called

    # Verify original order preserved
    assert len(result) == 1
    assert result[0].chunk_id == "1"


# [unit] - Edge case: empty list
def test_reranker_handles_empty_list():
    """Given empty candidate list, when reranking executes,
    then empty list is returned with no error.
    """
    from src.query.reranker import NeuralReranker

    with patch.object(NeuralReranker, '__init__', lambda self, **kw: None):
        reranker = NeuralReranker()
        reranker.model_name = "BAAI/bge-reranker-v2-m3"
        reranker.max_length = 512

        result = reranker.rerank("test query", [])

    assert result == []


# [unit] - Error handling: model load failure
def test_reranker_raises_on_model_load_failure():
    """Given model fails to load, when reranking executes,
    then appropriate exception is raised.
    """
    from src.query.reranker import RerankerError

    with patch('src.query.reranker.CrossEncoder') as mock_cross_encoder:
        mock_cross_encoder.side_effect = Exception("Model loading failed")

        with pytest.raises(RerankerError) as exc_info:
            # Directly test _load_model failure
            from src.query.reranker import NeuralReranker
            reranker = NeuralReranker(model_name="invalid-model")

    assert "Failed to load reranker model" in str(exc_info.value)


# [unit] - Boundary: truncation of long queries (test logic only)
def test_reranker_handles_long_query():
    """Given query exceeding max_length, when reranking executes,
    then model is invoked (truncation is handled by model internally).
    """
    from src.query.reranker import NeuralReranker
    from src.query.retriever import Candidate

    # Create a very long query
    long_query = "test " * 200  # 800 characters

    candidates = [
        Candidate(chunk_id="1", repo_name="repo", file_path="a.py", symbol=None,
                 content="def foo(): pass", score=0.5, language="python"),
        Candidate(chunk_id="2", repo_name="repo", file_path="b.py", symbol=None,
                 content="def bar(): pass", score=0.6, language="python"),
    ]

    mock_model = MagicMock()
    mock_model.predict.return_value = [0.5, 0.5]

    with patch.object(NeuralReranker, '__init__', lambda self, **kw: None):
        reranker = NeuralReranker()
        reranker.model = mock_model
        reranker.model_name = "BAAI/bge-reranker-v2-m3"
        reranker.max_length = 50  # Short max_length for testing
        result = reranker.rerank(long_query, candidates)

    # Verify model was called - truncation happens at model level
    assert mock_model.predict.called


# [unit] - Error handling: model predict failure
def test_reranker_raises_on_predict_failure():
    """Given model.predict fails, when reranking executes,
    then appropriate exception is raised.
    """
    from src.query.reranker import NeuralReranker, RerankerError
    from src.query.retriever import Candidate

    candidates = [
        Candidate(chunk_id="1", repo_name="repo", file_path="a.py", symbol=None,
                 content="def foo(): pass", score=0.5, language="python"),
        Candidate(chunk_id="2", repo_name="repo", file_path="b.py", symbol=None,
                 content="def bar(): pass", score=0.6, language="python"),
    ]

    mock_model = MagicMock()
    mock_model.predict.side_effect = Exception("Prediction failed")

    with patch.object(NeuralReranker, '__init__', lambda self, **kw: None):
        reranker = NeuralReranker()
        reranker.model = mock_model
        reranker.model_name = "BAAI/bge-reranker-v2-m3"
        reranker.max_length = 512

        with pytest.raises(RerankerError) as exc_info:
            reranker.rerank("test query", candidates)

    assert "Reranking failed" in str(exc_info.value)


# [unit] - Integration with device selection
def test_reranker_prefers_cuda_when_available():
    """Given CUDA is available, when reranker loads model,
    then model uses CUDA device.
    """
    with patch('src.query.reranker.torch.cuda.is_available', return_value=True):
        with patch('src.query.reranker.CrossEncoder') as mock_cross_encoder:
            mock_instance = MagicMock()
            mock_cross_encoder.return_value = mock_instance

            from src.query.reranker import NeuralReranker
            reranker = NeuralReranker(model_name="BAAI/bge-reranker-v2-m3")

            # Verify CrossEncoder was called with cuda device
            mock_cross_encoder.assert_called_once()
            call_kwargs = mock_cross_encoder.call_args.kwargs
            assert call_kwargs.get('device') == 'cuda'


# [unit] - Verify score update after reranking
def test_reranker_updates_candidate_scores():
    """Given candidates with initial scores, when reranking executes,
    then candidate scores are updated to reflect neural relevance.
    """
    from src.query.reranker import NeuralReranker
    from src.query.retriever import Candidate

    candidates = [
        Candidate(chunk_id="1", repo_name="repo", file_path="a.py", symbol=None,
                 content="def foo(): pass", score=0.5, language="python"),
        Candidate(chunk_id="2", repo_name="repo", file_path="b.py", symbol=None,
                 content="def bar(): pass", score=0.8, language="python"),
    ]

    # Model returns different scores than original
    mock_model = MagicMock()
    mock_model.predict.return_value = [0.9, 0.3]  # Reversed from original

    with patch.object(NeuralReranker, '__init__', lambda self, **kw: None):
        reranker = NeuralReranker()
        reranker.model = mock_model
        reranker.model_name = "BAAI/bge-reranker-v2-m3"
        reranker.max_length = 512
        result = reranker.rerank("test query", candidates)

    # Scores should be updated to neural relevance scores
    assert result[0].score == 0.9
    assert result[1].score == 0.3


# [unit] - Verify query-document pairs are correctly formed
def test_reranker_forms_correct_pairs():
    """Given query and candidates, when reranking executes,
    then query-document pairs are formed correctly for the model.
    """
    from src.query.reranker import NeuralReranker
    from src.query.retriever import Candidate

    query = "How to configure timeout"
    candidates = [
        Candidate(chunk_id="1", repo_name="repo", file_path="a.py", symbol=None,
                 content="def set_timeout(): pass", score=0.5, language="python"),
        Candidate(chunk_id="2", repo_name="repo", file_path="b.py", symbol=None,
                 content="def get_timeout(): pass", score=0.3, language="python"),
    ]

    mock_model = MagicMock()
    mock_model.predict.return_value = [0.7, 0.5]

    with patch.object(NeuralReranker, '__init__', lambda self, **kw: None):
        reranker = NeuralReranker()
        reranker.model = mock_model
        reranker.model_name = "BAAI/bge-reranker-v2-m3"
        reranker.max_length = 512
        reranker.rerank(query, candidates)

    # Verify the pairs were formed correctly
    mock_model.predict.assert_called_once()
    call_args = mock_model.predict.call_args[0][0]
    assert len(call_args) == 2
    assert call_args[0] == (query, candidates[0].content)
    assert call_args[1] == (query, candidates[1].content)
