"""Shared test fixtures for Code Context Retrieval."""

import os
import sys

import pytest

# When mutmut runs tests from mutants/ directory, ensure the trampolined
# source code in mutants/ takes priority over the editable-installed package.
if os.environ.get("MUTANT_UNDER_TEST"):
    _cwd = os.getcwd()
    if _cwd not in sys.path or sys.path.index(_cwd) > 0:
        sys.path.insert(0, _cwd)
    # Force reimport of src package from CWD (mutants/) instead of editable install
    for mod_name in list(sys.modules):
        if mod_name == "src" or mod_name.startswith("src."):
            del sys.modules[mod_name]


@pytest.fixture(autouse=True)
def _clear_proxy_env(request, monkeypatch):
    """Remove proxy env vars that break Qdrant/httpx client instantiation.

    Skipped for tests marked with @pytest.mark.real that need network
    access through the proxy (e.g., git clone tests).
    """
    if request.node.get_closest_marker("real"):
        return
    for key in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy",
                "HTTPS_PROXY", "https_proxy", "NO_PROXY", "no_proxy"):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def sample_query():
    """A sample natural language query for testing."""
    return "how to configure spring http client timeout"


@pytest.fixture
def sample_symbol_query():
    """A sample symbol query for testing."""
    return "UserService.getById"
