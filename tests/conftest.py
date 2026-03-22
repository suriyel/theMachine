"""Shared test fixtures for Code Context Retrieval."""

import os
import sys

import pytest

# When mutmut runs tests from mutants/ directory, ensure the trampolined
# source code in mutants/ takes priority over the editable-installed package.
# Also set MUTANT_UNDER_TEST if missing (mutmut v3 stats collection phase
# doesn't set this env var, but the trampoline code requires it).
if os.path.basename(os.getcwd()) == "mutants":
    if "MUTANT_UNDER_TEST" not in os.environ:
        os.environ["MUTANT_UNDER_TEST"] = ""
    _cwd = os.getcwd()
    if _cwd not in sys.path or sys.path.index(_cwd) > 0:
        sys.path.insert(0, _cwd)
    # Force reimport of src package from CWD (mutants/) instead of editable install
    for mod_name in list(sys.modules):
        if mod_name == "src" or mod_name.startswith("src."):
            del sys.modules[mod_name]


def pytest_collection_modifyitems(config, items):
    """Skip Jinja2 template tests when running in mutmut mutants/ directory.

    mutmut copies source to mutants/ but not templates/static, causing
    Jinja2 TemplateNotFound errors. These tests are unrelated to mutation
    coverage and are safely skippable in that context.
    """
    if os.environ.get("MUTANT_UNDER_TEST") or os.path.basename(os.getcwd()) == "mutants":
        skip_marker = pytest.mark.skip(reason="Jinja2 templates unavailable in mutants/ dir")
        for item in items:
            if "test_web_ui" in item.nodeid:
                item.add_marker(skip_marker)


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
