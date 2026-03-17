"""Tests for LanguageFilter class."""

import pytest
from src.query.language_filter import LanguageFilter


class TestLanguageFilterValidate:
    """Tests for LanguageFilter.validate()."""

    def test_validate_returns_none_for_none(self):
        """Test validate returns None when language is None."""
        filter = LanguageFilter()
        result = filter.validate(None)
        assert result is None

    def test_validate_returns_none_for_all(self):
        """Test validate returns None when language is 'all'."""
        filter = LanguageFilter()
        result = filter.validate("all")
        assert result is None

    def test_validate_returns_none_for_all_uppercase(self):
        """Test validate returns None when language is 'ALL' (case-insensitive)."""
        filter = LanguageFilter()
        result = filter.validate("ALL")
        assert result is None

    def test_validate_returns_lowercase_for_java(self):
        """Test validate returns lowercase 'java' for 'Java'."""
        filter = LanguageFilter()
        result = filter.validate("Java")
        assert result == "java"

    def test_validate_returns_lowercase_for_python(self):
        """Test validate returns lowercase 'python' for 'Python'."""
        filter = LanguageFilter()
        result = filter.validate("Python")
        assert result == "python"

    def test_validate_returns_lowercase_for_typescript(self):
        """Test validate returns lowercase for TypeScript."""
        filter = LanguageFilter()
        result = filter.validate("TypeScript")
        assert result == "typescript"

    def test_validate_returns_lowercase_for_javascript(self):
        """Test validate returns lowercase for JavaScript."""
        filter = LanguageFilter()
        result = filter.validate("JavaScript")
        assert result == "javascript"

    def test_validate_returns_lowercase_for_c(self):
        """Test validate returns lowercase for C."""
        filter = LanguageFilter()
        result = filter.validate("C")
        assert result == "c"

    def test_validate_returns_lowercase_for_cpp(self):
        """Test validate returns lowercase for C++."""
        filter = LanguageFilter()
        result = filter.validate("C++")
        assert result == "cpp"

    def test_validate_raises_for_unsupported_language(self):
        """Test validate raises ValueError for unsupported language."""
        filter = LanguageFilter()
        with pytest.raises(ValueError) as exc_info:
            filter.validate("Ruby")
        assert "Unsupported language" in str(exc_info.value)
        assert "Ruby" in str(exc_info.value)
        assert "Java" in str(exc_info.value)
        assert "Python" in str(exc_info.value)
        assert "TypeScript" in str(exc_info.value)
        assert "JavaScript" in str(exc_info.value)
        assert "C" in str(exc_info.value)
        assert "C++" in str(exc_info.value)

    def test_validate_raises_for_unsupported_with_list_in_error(self):
        """Test validation error lists all supported languages."""
        filter = LanguageFilter()
        with pytest.raises(ValueError) as exc_info:
            filter.validate("Go")
        error_msg = str(exc_info.value)
        # Check all supported languages are listed
        assert "Java" in error_msg
        assert "Python" in error_msg
        assert "TypeScript" in error_msg
        assert "JavaScript" in error_msg
        assert "C" in error_msg
        assert "C++" in error_msg


class TestLanguageFilterApply:
    """Tests for LanguageFilter.apply()."""

    def test_apply_returns_all_when_language_none(self):
        """Test apply returns all candidates when language is None."""
        from src.query.retriever import Candidate

        filter = LanguageFilter()
        candidates = [
            Candidate(chunk_id="1", repo_name="repo1", file_path="a.java", symbol="Foo", content="code", score=0.9, language="java"),
            Candidate(chunk_id="2", repo_name="repo2", file_path="b.py", symbol="Bar", content="code", score=0.8, language="python"),
        ]
        result = filter.apply(candidates, None)
        assert len(result) == 2

    def test_apply_filters_to_java_only(self):
        """Test apply filters to Java only."""
        from src.query.retriever import Candidate

        filter = LanguageFilter()
        candidates = [
            Candidate(chunk_id="1", repo_name="repo1", file_path="a.java", symbol="Foo", content="code", score=0.9, language="java"),
            Candidate(chunk_id="2", repo_name="repo2", file_path="b.py", symbol="Bar", content="code", score=0.8, language="python"),
            Candidate(chunk_id="3", repo_name="repo3", file_path="c.ts", symbol="Baz", content="code", score=0.7, language="typescript"),
        ]
        result = filter.apply(candidates, "java")
        assert len(result) == 1
        assert result[0].language == "java"
        assert result[0].file_path == "a.java"

    def test_apply_filters_to_python_case_insensitive(self):
        """Test apply filters case-insensitively."""
        from src.query.retriever import Candidate

        filter = LanguageFilter()
        candidates = [
            Candidate(chunk_id="1", repo_name="repo1", file_path="a.java", symbol="Foo", content="code", score=0.9, language="java"),
            Candidate(chunk_id="2", repo_name="repo2", file_path="b.py", symbol="Bar", content="code", score=0.8, language="python"),
        ]
        result = filter.apply(candidates, "PYTHON")
        assert len(result) == 1
        assert result[0].language == "python"

    def test_apply_returns_empty_for_no_matches(self):
        """Test apply returns empty list when no matches."""
        from src.query.retriever import Candidate

        filter = LanguageFilter()
        candidates = [
            Candidate(chunk_id="1", repo_name="repo1", file_path="a.java", symbol="Foo", content="code", score=0.9, language="java"),
        ]
        result = filter.apply(candidates, "python")
        assert len(result) == 0

    def test_apply_handles_none_language_in_candidates(self):
        """Test apply handles candidates with None language."""
        from src.query.retriever import Candidate

        filter = LanguageFilter()
        candidates = [
            Candidate(chunk_id="1", repo_name="repo1", file_path="a.java", symbol="Foo", content="code", score=0.9, language=None),
            Candidate(chunk_id="2", repo_name="repo2", file_path="b.py", symbol="Bar", content="code", score=0.8, language="python"),
        ]
        result = filter.apply(candidates, "python")
        assert len(result) == 1
        assert result[0].language == "python"


class TestLanguageFilterIntegration:
    """Integration tests for LanguageFilter with QueryHandler."""

    def test_filter_can_be_imported(self):
        """Test LanguageFilter can be imported."""
        from src.query.language_filter import LanguageFilter
        assert LanguageFilter is not None


class TestRESTAPILanguageValidation:
    """Tests for language validation in REST API."""

    def test_get_query_rejects_unsupported_language(self):
        """Test GET query rejects unsupported language with 422."""
        from unittest.mock import MagicMock, AsyncMock, patch

        with patch('src.query.api.v1.endpoints.query.AuthMiddleware') as mock_auth:
            mock_auth.return_value.require_auth = AsyncMock()

            from src.query.api.v1.endpoints.query import get_query
            from fastapi import Request, HTTPException

            mock_request = MagicMock(spec=Request)
            mock_request.headers = {}

            import asyncio
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_query(
                    request=mock_request,
                    query="test",
                    language="Ruby",
                ))
            assert exc_info.value.status_code == 422
            assert "Unsupported language" in exc_info.value.detail

    def test_post_query_rejects_unsupported_language(self):
        """Test POST query rejects unsupported language with 422."""
        from unittest.mock import MagicMock, AsyncMock, patch

        with patch('src.query.api.v1.endpoints.query.AuthMiddleware') as mock_auth:
            mock_auth.return_value.require_auth = AsyncMock()

            from src.query.api.v1.endpoints.query import post_query
            from src.query.models import QueryRequest
            from fastapi import Request, HTTPException

            mock_request = MagicMock(spec=Request)
            mock_request.headers = {}

            import asyncio
            query_req = QueryRequest(query="test", language="Ruby")
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(post_query(
                    request=mock_request,
                    query_request=query_req,
                ))
            assert exc_info.value.status_code == 422
            assert "Unsupported language" in exc_info.value.detail

    def test_validate_empty_string_raises(self):
        """Test validate raises for empty string."""
        filter = LanguageFilter()
        with pytest.raises(ValueError) as exc_info:
            filter.validate("")
        assert "Unsupported language" in str(exc_info.value)

    def test_validate_numeric_string_raises(self):
        """Test validate raises for numeric string."""
        filter = LanguageFilter()
        with pytest.raises(ValueError) as exc_info:
            filter.validate("123")
        assert "Unsupported language" in str(exc_info.value)

    def test_apply_with_empty_candidates(self):
        """Test apply returns empty list for empty input."""
        filter = LanguageFilter()
        result = filter.apply([], "java")
        assert result == []
