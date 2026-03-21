"""Tests for Feature #35 — Java: enum + record + static initializer.

# [no integration test] — pure computation feature, no external I/O
# tree-sitter is a local library (not an external service)

Tests verify that Java enum declarations, record declarations, and
static initializer blocks produce proper L2/L3 chunks.
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

ENUM_WITH_METHOD = """\
public enum Color {
    RED, GREEN, BLUE;

    public String display() {
        return name().toLowerCase();
    }
}
"""

ENUM_WITHOUT_METHODS = """\
public enum Direction {
    NORTH, SOUTH, EAST, WEST
}
"""

RECORD_WITH_METHOD = """\
public record Point(int x, int y) {
    public double distance() {
        return Math.sqrt(x * x + y * y);
    }
}
"""

RECORD_WITHOUT_METHODS = """\
public record Config(String host, int port) {}
"""

STATIC_INITIALIZER = """\
public class AppConfig {
    private static final Map<String, String> defaults = new HashMap<>();

    static {
        defaults.put("timeout", "30");
        defaults.put("retries", "3");
    }

    public void run() {}
}
"""

PLAIN_JAVA = """\
public class Service {
    public void start() {}
    public void stop() {}
}
"""

ENUM_WITH_CONSTRUCTOR = """\
public enum Planet {
    EARTH(5.976e+24, 6.37814e6),
    MARS(6.421e+23, 3.3972e6);

    private final double mass;
    private final double radius;

    Planet(double mass, double radius) {
        this.mass = mass;
        this.radius = radius;
    }

    public double surfaceGravity() {
        return 6.67300E-11 * mass / (radius * radius);
    }
}
"""


# ---------------------------------------------------------------------------
# Happy path tests
# ---------------------------------------------------------------------------


# [unit]
class TestEnumDeclaration:
    """VS-1: Enum declarations produce L2 chunks with methods as L3."""

    def test_enum_produces_l2_chunk(self, chunker):
        """T1a: Enum declaration → L2 chunk with symbol='Color'."""
        f = _make_file("src/Color.java", ENUM_WITH_METHOD)
        chunks = chunker.chunk(f, repo_id="repo-35", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        assert len(classes) == 1
        assert classes[0].symbol == "Color"

    def test_enum_method_produces_l3_with_parent(self, chunker):
        """T1b: Method inside enum → L3 with parent_class='Color'."""
        f = _make_file("src/Color.java", ENUM_WITH_METHOD)
        chunks = chunker.chunk(f, repo_id="repo-35", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        display_fn = [c for c in funcs if c.symbol == "display"]
        assert len(display_fn) == 1
        assert display_fn[0].parent_class == "Color"


# [unit]
class TestRecordDeclaration:
    """VS-2: Record declarations produce L2 chunks."""

    def test_record_produces_l2_chunk(self, chunker):
        """T2: Record declaration → L2 with symbol='Point'."""
        f = _make_file("src/Point.java", RECORD_WITH_METHOD)
        chunks = chunker.chunk(f, repo_id="repo-35", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        assert len(classes) == 1
        assert classes[0].symbol == "Point"

    def test_record_method_produces_l3(self, chunker):
        """Record method → L3 with parent_class='Point'."""
        f = _make_file("src/Point.java", RECORD_WITH_METHOD)
        chunks = chunker.chunk(f, repo_id="repo-35", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        dist_fn = [c for c in funcs if c.symbol == "distance"]
        assert len(dist_fn) == 1
        assert dist_fn[0].parent_class == "Point"


# [unit]
class TestStaticInitializer:
    """VS-3: Static initializer blocks produce L3 chunks."""

    def test_static_initializer_produces_l3(self, chunker):
        """T3: static {} block → L3 chunk with parent_class='AppConfig'."""
        f = _make_file("src/AppConfig.java", STATIC_INITIALIZER)
        chunks = chunker.chunk(f, repo_id="repo-35", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        static_fn = [c for c in funcs if c.symbol == "<static>"]
        assert len(static_fn) == 1, (
            f"Expected 1 '<static>' function chunk, got {len(static_fn)}. "
            f"All funcs: {[(f.symbol, f.parent_class) for f in funcs]}"
        )
        assert static_fn[0].parent_class == "AppConfig"

    def test_static_initializer_content(self, chunker):
        """Static block content includes the block body."""
        f = _make_file("src/AppConfig.java", STATIC_INITIALIZER)
        chunks = chunker.chunk(f, repo_id="repo-35", branch="main")
        funcs = [c for c in chunks if c.chunk_type == "function"]
        static_fn = [c for c in funcs if c.symbol == "<static>"]
        assert len(static_fn) == 1
        assert "defaults.put" in static_fn[0].content


# ---------------------------------------------------------------------------
# Boundary & edge case tests
# ---------------------------------------------------------------------------


# [unit]
class TestBoundaryEdgeCases:
    """Boundary and edge case tests."""

    def test_enum_without_methods_l2_only(self, chunker):
        """T4: Enum without methods → L2 only, no L3."""
        f = _make_file("src/Direction.java", ENUM_WITHOUT_METHODS)
        chunks = chunker.chunk(f, repo_id="repo-35", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(classes) == 1
        assert classes[0].symbol == "Direction"
        assert len(funcs) == 0

    def test_record_without_methods_l2_only(self, chunker):
        """T5: Record without methods → L2 only."""
        f = _make_file("src/Config.java", RECORD_WITHOUT_METHODS)
        chunks = chunker.chunk(f, repo_id="repo-35", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        assert len(classes) == 1
        assert classes[0].symbol == "Config"

    def test_plain_java_no_regression(self, chunker):
        """T6: Plain Java class still works (no regression)."""
        f = _make_file("src/Service.java", PLAIN_JAVA)
        chunks = chunker.chunk(f, repo_id="repo-35", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(classes) == 1
        assert classes[0].symbol == "Service"
        assert len(funcs) == 2
        func_names = sorted([c.symbol for c in funcs])
        assert func_names == ["start", "stop"]

    def test_enum_in_top_level_symbols(self, chunker):
        """Enum name appears in L1 file chunk top_level_symbols."""
        f = _make_file("src/Color.java", ENUM_WITH_METHOD)
        chunks = chunker.chunk(f, repo_id="repo-35", branch="main")
        file_chunks = [c for c in chunks if c.chunk_type == "file"]
        assert len(file_chunks) == 1
        assert "Color" in file_chunks[0].top_level_symbols

    def test_enum_with_constructor_and_method(self, chunker):
        """Enum with constructor and method → L2 + L3 for constructor + method."""
        f = _make_file("src/Planet.java", ENUM_WITH_CONSTRUCTOR)
        chunks = chunker.chunk(f, repo_id="repo-35", branch="main")
        classes = [c for c in chunks if c.chunk_type == "class"]
        funcs = [c for c in chunks if c.chunk_type == "function"]
        assert len(classes) == 1
        assert classes[0].symbol == "Planet"
        func_names = sorted([c.symbol for c in funcs])
        # Should have constructor (Planet) and method (surfaceGravity)
        assert "Planet" in func_names
        assert "surfaceGravity" in func_names
        for fn in funcs:
            assert fn.parent_class == "Planet"

    def test_record_in_top_level_symbols(self, chunker):
        """Record name appears in L1 file chunk top_level_symbols."""
        f = _make_file("src/Point.java", RECORD_WITH_METHOD)
        chunks = chunker.chunk(f, repo_id="repo-35", branch="main")
        file_chunks = [c for c in chunks if c.chunk_type == "file"]
        assert len(file_chunks) == 1
        assert "Point" in file_chunks[0].top_level_symbols


# Security: N/A — internal utility with no user-facing input
