"""Shared test fixtures for Code Context Retrieval."""

import os
import sys

import pytest

# When mutmut runs tests from mutants/ directory, ensure the trampolined
# source code in mutants/ takes priority over the editable-installed package.
# Also set MUTANT_UNDER_TEST if missing (mutmut v3 stats collection phase
# doesn't set this env var, but the trampoline code requires it).
if os.path.basename(os.getcwd()) == "mutants":
    _cwd = os.getcwd()
    if _cwd not in sys.path or sys.path.index(_cwd) > 0:
        sys.path.insert(0, _cwd)
    if "MUTANT_UNDER_TEST" not in os.environ:
        os.environ["MUTANT_UNDER_TEST"] = ""

    # Remove the editable-install finder so mutants/src/ takes priority
    # over the project-root editable install at /home/.../theMachine/src.
    # The editable finder is a class (not instance) in meta_path, so check
    # both type(f).__name__ and getattr(f, '__name__', '').
    sys.meta_path[:] = [
        f for f in sys.meta_path
        if "Editable" not in type(f).__name__
        and "Editable" not in getattr(f, "__name__", "")
    ]
    # Also remove editable namespace path hooks and entries
    sys.path_hooks[:] = [
        h for h in sys.path_hooks
        if "Editable" not in getattr(h, "__qualname__", "")
    ]
    sys.path[:] = [p for p in sys.path if "__editable__" not in p]
    # Clear import caches so PathFinder re-resolves from cleaned sys.path
    import importlib
    sys.path_importer_cache.clear()
    importlib.invalidate_caches()


def _fix_mutmut_src_prefix():
    """Fix mutmut 3.x src/ layout prefix mismatch on every pytest invocation.

    mutmut 3.x strips "src." when generating mutant names
    (src/query/app.py → query.app) but modules are imported as src.query.app.
    This causes the trampoline's prefix check to fail on every mutation run:
      prefix = "src.query.app.x_create_app__mutmut_"
      MUTANT_UNDER_TEST = "query.app.x_create_app__mutmut_1"  ← no match

    Fixes applied here (called from pytest_configure, which runs per invocation):
    1. MUTANT_UNDER_TEST: add "src." prefix for non-special values
    2. record_trampoline_hit: strip "src." so stats keys match mutant names
    3. Force reimport of src.* modules from mutants/ dir
    """
    if os.path.basename(os.getcwd()) != "mutants":
        return

    # Fix MUTANT_UNDER_TEST
    _mut = os.environ.get("MUTANT_UNDER_TEST", "")
    _special = {"", "stats", "fail", "mutant_generation", "list_all_tests"}
    if _mut not in _special and not _mut.startswith("src."):
        os.environ["MUTANT_UNDER_TEST"] = "src." + _mut

    # Note: record_trampoline_hit no longer needs patching since Patch 1
    # (env-guide.md) keeps the "src." prefix in meta keys, matching
    # orig.__module__ which already starts with "src.".

    # Force reimport of src package from CWD (mutants/) instead of editable install
    for mod_name in list(sys.modules):
        if mod_name == "src" or mod_name.startswith("src."):
            del sys.modules[mod_name]


def pytest_configure(config):
    """Run src. prefix fix on every pytest invocation (not just module import)."""
    _fix_mutmut_src_prefix()


def pytest_collection_modifyitems(config, items):
    """Skip tests incompatible with mutmut mutants/ directory.

    mutmut copies source to mutants/ but not docker/ build context,
    causing Docker build failures.
    Templates ARE available (copied via also_copy src/), so test_web_ui runs.
    """
    if os.environ.get("MUTANT_UNDER_TEST") or os.path.basename(os.getcwd()) == "mutants":
        skip_marker = pytest.mark.skip(reason="Unavailable in mutants/ dir (no docker)")
        for item in items:
            if "test_feature_44" in item.nodeid or "test_feature_45" in item.nodeid:
                item.add_marker(skip_marker)
            if "test_docker" in item.nodeid or "test_container" in item.nodeid:
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
