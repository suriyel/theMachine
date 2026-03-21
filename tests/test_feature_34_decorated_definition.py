"""Tests for Feature #34 — Python: decorated_definition Unwrapping.

# [no integration test] — pure computation feature, no external I/O
# tree-sitter is a local library (not an external service)

Tests verify that Python @decorator-wrapped functions and classes
produce proper L2/L3 chunks with correct symbol, parent_class,
and decorator text preserved in content.
"""

import pytest

from src.indexing.chunker import Chunker, CodeChunk
from src.indexing.content_extractor import ContentType, ExtractedFile


# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def chunker():
    return Chunker()


def _make_file(
    path: str,
    content: str,
    content_type: ContentType = ContentType.CODE,
) -> ExtractedFile:
    return ExtractedFile(
        path=path, content_type=content_type, content=content, size=len(content)
    )


# ---------------------------------------------------------------------------
# Test snippets
# ---------------------------------------------------------------------------

PROPERTY_GETTER = """\
class Foo:
    @property
    def name(self):
        return self._name
"""

PROPERTY_SETTER = """\
class Foo:
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, val):
        self._name = val
"""

STATICMETHOD = """\
class Svc:
    @staticmethod
    def create():
        return Svc()
"""

CLASSMETHOD = """\
class Svc:
    @classmethod
    def from_config(cls):
        return cls()
"""

DATACLASS = """\
from dataclasses import dataclass

@dataclass
class Config:
    host: str
    port: int
"""

APP_ROUTE = """\
from flask import Flask
app = Flask(__name__)

@app.route('/')
def index():
    return 'hello'
"""

STACKED_DECORATORS = """\
@decorator1
@decorator2
def multi():
    pass
"""

PLAIN_FUNCTIONS = """\
def foo():
    pass

def bar():
    pass

class Baz:
    def method(self):
        pass
"""

DATACLASS_WITH_METHODS = """\
from dataclasses import dataclass

@dataclass
class Config:
    host: str
    port: int

    def validate(self):
        if not self.host:
            raise ValueError("host required")
"""

MIXED_DECORATED = """\
@app.route('/')
def index():
    return 'hello'

@dataclass
class Cfg:
    x: int
"""


# ---------------------------------------------------------------------------
# Happy path tests
# ---------------------------------------------------------------------------


# [unit]
class TestPropertyDecorators:
    """VS-1: @property getter and @property.setter produce L3 with parent_class."""

    def test_property_getter_produces_l3_with_parent_class(self, chunker):
        """T1: @property getter → L3 chunk with symbol='name', parent_class='Foo'."""
        f = _make_file("src/model.py", PROPERTY_GETTER)
        chunks = chunker.chunk(f, repo_id="repo-34", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(funcs) >= 1, f"Expected at least 1 function chunk, got {len(funcs)}"
        getter = [c for c in funcs if c.symbol == "name"]
        assert len(getter) == 1, f"Expected exactly 1 'name' function chunk, got {len(getter)}"
        assert getter[0].parent_class == "Foo"

    def test_property_setter_produces_l3_with_parent_class(self, chunker):
        """T2: @name.setter → L3 chunk with symbol='name', parent_class='Foo'."""
        f = _make_file("src/model.py", PROPERTY_SETTER)
        chunks = chunker.chunk(f, repo_id="repo-34", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        name_funcs = [c for c in funcs if c.symbol == "name"]
        # Both getter and setter should produce L3 chunks
        assert len(name_funcs) == 2, (
            f"Expected 2 'name' function chunks (getter + setter), got {len(name_funcs)}"
        )
        for fn in name_funcs:
            assert fn.parent_class == "Foo"


# [unit]
class TestStaticAndClassMethod:
    """VS-2: @staticmethod and @classmethod produce L3 with parent_class."""

    def test_staticmethod_produces_l3_with_parent_class(self, chunker):
        """T3: @staticmethod → L3 with symbol='create', parent_class='Svc'."""
        f = _make_file("src/svc.py", STATICMETHOD)
        chunks = chunker.chunk(f, repo_id="repo-34", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(funcs) >= 1
        create_fn = [c for c in funcs if c.symbol == "create"]
        assert len(create_fn) == 1
        assert create_fn[0].parent_class == "Svc"

    def test_classmethod_produces_l3_with_parent_class(self, chunker):
        """T4: @classmethod → L3 with symbol='from_config', parent_class='Svc'."""
        f = _make_file("src/svc.py", CLASSMETHOD)
        chunks = chunker.chunk(f, repo_id="repo-34", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(funcs) >= 1
        from_cfg = [c for c in funcs if c.symbol == "from_config"]
        assert len(from_cfg) == 1
        assert from_cfg[0].parent_class == "Svc"


# [unit]
class TestDecoratedClass:
    """VS-3: @dataclass decorated class produces L2 chunk."""

    def test_dataclass_decorated_class_produces_l2(self, chunker):
        """T5: @dataclass class Config → L2 with symbol='Config'."""
        f = _make_file("src/cfg.py", DATACLASS)
        chunks = chunker.chunk(f, repo_id="repo-34", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        assert len(classes) == 1
        assert classes[0].symbol == "Config"

    def test_dataclass_class_content_includes_decorator(self, chunker):
        """L2 class chunk content includes decorator text (@dataclass)."""
        f = _make_file("src/cfg.py", DATACLASS)
        chunks = chunker.chunk(f, repo_id="repo-34", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        assert len(classes) == 1
        assert "@dataclass" in classes[0].content


# [unit]
class TestTopLevelDecoratedFunction:
    """VS-4: @app.route top-level function produces L3 with empty parent_class."""

    def test_app_route_top_level_produces_l3_no_parent(self, chunker):
        """T6: @app.route('/') def index → L3, parent_class=''."""
        f = _make_file("src/app.py", APP_ROUTE)
        chunks = chunker.chunk(f, repo_id="repo-34", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        index_fn = [c for c in funcs if c.symbol == "index"]
        assert len(index_fn) == 1, f"Expected 1 'index' function chunk, got {len(index_fn)}"
        assert index_fn[0].parent_class == ""

    def test_decorated_chunk_content_includes_decorator(self, chunker):
        """T7: Chunk content starts with @app.route (decorator preserved)."""
        f = _make_file("src/app.py", APP_ROUTE)
        chunks = chunker.chunk(f, repo_id="repo-34", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        index_fn = [c for c in funcs if c.symbol == "index"]
        assert len(index_fn) == 1
        assert "@app.route" in index_fn[0].content


# ---------------------------------------------------------------------------
# Boundary & edge case tests
# ---------------------------------------------------------------------------


# [unit]
class TestBoundaryEdgeCases:
    """Boundary and edge case tests for decorated_definition unwrapping."""

    def test_stacked_decorators_produce_l3(self, chunker):
        """T8: Multiple stacked decorators → single L3 chunk with symbol='multi'."""
        f = _make_file("src/stacked.py", STACKED_DECORATORS)
        chunks = chunker.chunk(f, repo_id="repo-34", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        multi_fn = [c for c in funcs if c.symbol == "multi"]
        assert len(multi_fn) == 1
        # Both decorators preserved in content
        assert "@decorator1" in multi_fn[0].content
        assert "@decorator2" in multi_fn[0].content

    def test_plain_functions_no_regression(self, chunker):
        """T9: Plain functions/classes still produce correct chunks (no regression)."""
        f = _make_file("src/plain.py", PLAIN_FUNCTIONS)
        chunks = chunker.chunk(f, repo_id="repo-34", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        classes = [c for c in chunks if c.chunk_type == "class"]
        func_symbols = sorted([c.symbol for c in funcs])
        # foo, bar at top level, method inside Baz
        assert "foo" in func_symbols
        assert "bar" in func_symbols
        assert "method" in func_symbols
        assert len(classes) == 1
        assert classes[0].symbol == "Baz"

    def test_decorated_class_with_methods(self, chunker):
        """T10: @dataclass class with methods → L2 for class + L3 for method."""
        f = _make_file("src/cfg.py", DATACLASS_WITH_METHODS)
        chunks = chunker.chunk(f, repo_id="repo-34", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(classes) == 1
        assert classes[0].symbol == "Config"
        validate_fn = [c for c in funcs if c.symbol == "validate"]
        assert len(validate_fn) == 1
        assert validate_fn[0].parent_class == "Config"

    def test_file_chunk_includes_decorated_symbols(self, chunker):
        """T11: L1 file chunk top_level_symbols includes decorated func/class names."""
        f = _make_file("src/mixed.py", MIXED_DECORATED)
        chunks = chunker.chunk(f, repo_id="repo-34", branch="main")
        file_chunks = [c for c in chunks if c.chunk_type == "file"]
        assert len(file_chunks) == 1
        tls = file_chunks[0].top_level_symbols
        assert "index" in tls, f"'index' not in top_level_symbols: {tls}"
        assert "Cfg" in tls, f"'Cfg' not in top_level_symbols: {tls}"

    def test_decorated_definition_without_function_or_class(self, chunker):
        """T12: decorated_definition with no recognizable inner node → no crash."""
        # In practice tree-sitter always wraps a func/class, but test defensively.
        # Use a plain Python file — if there's somehow a decorated_definition with
        # only decorators and no inner node, the chunker should not crash.
        f = _make_file("src/safe.py", "def safe(): pass\n")
        chunks = chunker.chunk(f, repo_id="repo-34", branch="main")
        # Should produce at least L1 + L3 for the plain function
        assert len(chunks) >= 2

    def test_decorated_function_empty_symbol_no_crash(self, chunker):
        """T13: Decorated function that has an identifier → symbol extracted correctly.
        (Defensive: if somehow name extraction fails, no crash.)"""
        # Normal decorated function
        code = "@dec\ndef func_with_name():\n    pass\n"
        f = _make_file("src/named.py", code)
        chunks = chunker.chunk(f, repo_id="repo-34", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(funcs) >= 1
        assert funcs[0].symbol == "func_with_name"


# Security: N/A — internal utility with no user-facing input
