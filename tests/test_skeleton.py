"""Skeleton tests — verify project structure exists."""


def test_src_packages_importable():
    """Verify core packages are importable."""
    import src
    import src.indexing
    import src.query
    import src.shared
    import src.shared.clients
    import src.shared.models
    import src.shared.services
    import src.shared.utils


def test_project_structure():
    """Verify key project files exist."""
    from pathlib import Path

    root = Path(__file__).parent.parent
    assert (root / "pyproject.toml").exists()
    assert (root / "feature-list.json").exists()
    assert (root / "src" / "__init__.py").exists()
    assert (root / "src" / "indexing" / "__init__.py").exists()
    assert (root / "src" / "query" / "__init__.py").exists()
    assert (root / "src" / "shared" / "__init__.py").exists()
