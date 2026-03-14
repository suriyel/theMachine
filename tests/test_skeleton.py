"""Basic skeleton test to verify project setup."""

import pytest


def test_project_structure():
    """Verify project structure is correctly scaffolded."""
    from pathlib import Path

    project_root = Path(__file__).parent.parent

    assert (project_root / "src" / "query").exists()
    assert (project_root / "src" / "indexing").exists()
    assert (project_root / "src" / "shared").exists()
    assert (project_root / "tests").exists()
    assert (project_root / "docs" / "plans").exists()
    assert (project_root / "pyproject.toml").exists()


def test_import_query_module():
    """Verify query module can be imported."""
    import src.query
    assert src.query.__version__ is not None


def test_import_shared_module():
    """Verify shared module can be imported."""
    import src.shared
    assert src.shared is not None
