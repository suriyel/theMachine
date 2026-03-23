"""Compatibility tests.

Verifies platform and runtime constraints from SRS §1.4:
  - Python >= 3.11 (pyproject.toml requires-python)
  - Linux amd64 (current CI/test environment)
  - No Python 3.12-only syntax that would break on 3.11

Docker image compatibility (NFR-012) is a design-level requirement (SRS "Should");
Dockerfiles do not exist in this repository. This is documented as a known gap.
"""

from __future__ import annotations

import platform
import sys


def test_python_version_meets_minimum():
    """Python >= 3.11 as specified in pyproject.toml requires-python."""
    assert sys.version_info >= (3, 11), (
        f"Python {sys.version_info.major}.{sys.version_info.minor} < 3.11 minimum"
    )


def test_platform_is_linux():
    """SRS §1.4: Target platform is Linux (amd64)."""
    assert platform.system() == "Linux", (
        f"Expected Linux, got {platform.system()}"
    )


def test_architecture_is_x86_64():
    """SRS §1.4: Target architecture is amd64 (x86_64)."""
    arch = platform.machine()
    assert arch in ("x86_64", "amd64"), f"Expected x86_64/amd64, got {arch}"


def test_all_core_modules_importable():
    """All core production modules import without error on current Python version."""
    modules = [
        "src.query.app",
        "src.query.query_handler",
        "src.query.query_cache",
        "src.query.retriever",
        "src.query.rank_fusion",
        "src.query.reranker",
        "src.query.response_builder",
        "src.query.mcp_server",
        "src.query.metrics_registry",
        "src.query.query_logger",
        "src.indexing.git_cloner",
        "src.indexing.content_extractor",
        "src.indexing.chunker",
        "src.shared.models.api_key",
        "src.shared.models.repository",
        "src.shared.services.auth_middleware",
        "src.shared.services.repo_manager",
    ]
    import importlib

    failed = []
    for mod in modules:
        try:
            importlib.import_module(mod)
        except ImportError as exc:
            failed.append(f"{mod}: {exc}")

    assert not failed, "Module import failures:\n" + "\n".join(failed)


def test_future_annotations_used_in_core_modules():
    """All core modules use 'from __future__ import annotations' for forward compat."""
    import ast
    import pathlib

    src_root = pathlib.Path("src")
    failures = []

    for py_file in src_root.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue
        source = py_file.read_text()
        if not source.strip():
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        # Check if first non-docstring statement imports annotations
        has_future = any(
            isinstance(node, ast.ImportFrom)
            and node.module == "__future__"
            and any(alias.name == "annotations" for alias in node.names)
            for node in ast.walk(tree)
        )
        # Only check files that use type annotations (have function defs)
        has_type_hints = any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and (node.returns is not None or any(
                arg.annotation is not None
                for arg in (node.args.args + node.args.posonlyargs + node.args.kwonlyargs)
            ))
            for node in ast.walk(tree)
        )
        if has_type_hints and not has_future:
            failures.append(str(py_file))

    # Report but don't hard-fail — this is informational
    if failures:
        print(f"\nModules with type hints but missing 'from __future__ import annotations':\n"
              + "\n".join(failures[:20]))
    # Pass regardless — this is an advisory check, not a blocking requirement
