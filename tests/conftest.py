"""Shared test fixtures for Code Context Retrieval."""

import pytest


@pytest.fixture
def sample_query():
    """A sample natural language query for testing."""
    return "how to configure spring http client timeout"


@pytest.fixture
def sample_symbol_query():
    """A sample symbol query for testing."""
    return "UserService.getById"
