"""Code chunking module using tree-sitter parsers."""

from pathlib import Path
from typing import Optional

from tree_sitter import Language, Node, Parser, Tree

from src.indexing.models import ChunkType, CodeChunk, RawContent


# Map file extensions to tree-sitter language names
EXTENSION_TO_LANGUAGE = {
    ".java": "java",
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".c": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "c",
    ".hpp": "cpp",
}

# Languages supported by tree-sitter
SUPPORTED_LANGUAGES = {"java", "python", "javascript", "typescript", "c", "cpp"}

# Map language names to tree-sitter module attributes
LANGUAGE_MODULE_MAP = {
    "java": ("tree_sitter_java", "language"),
    "python": ("tree_sitter_python", "language"),
    "javascript": ("tree_sitter_typescript", "language_typescript"),
    "typescript": ("tree_sitter_typescript", "language_typescript"),
    "c": ("tree_sitter_c", "language"),
    "cpp": ("tree_sitter_cpp", "language"),
}

# Unsupported languages fallback to file-level chunking
UNSUPPORTED_LANGUAGES = set()


class CodeChunker:
    """Segments source code into multi-granularity chunks using tree-sitter."""

    def __init__(self):
        """Initialize the CodeChunker with tree-sitter parsers."""
        self._parsers: dict[str, Parser] = {}
        self._language_cache: dict[str, Language] = {}

    def _get_parser(self, language: str) -> Optional[Parser]:
        """Get or create a tree-sitter parser for the given language."""
        if language not in self._parsers:
            if language not in self._language_cache:
                try:
                    module_name, attr_name = LANGUAGE_MODULE_MAP[language]
                    lang_module = __import__(module_name, fromlist=[attr_name])
                    lang_attr = getattr(lang_module, attr_name)
                    self._language_cache[language] = Language(lang_attr())
                except (ImportError, KeyError, AttributeError):
                    return None

            if language in self._language_cache:
                parser = Parser(self._language_cache[language])
                self._parsers[language] = parser

        return self._parsers.get(language)

    def chunk(self, raw_content: RawContent) -> list[CodeChunk]:
        """Chunk the raw content into multi-granularity chunks.

        Args:
            raw_content: The raw content to chunk

        Returns:
            List of CodeChunk objects at file, class, function, and symbol levels
        """
        language = raw_content.language or "unknown"
        file_path = raw_content.file_path

        # Check if language is supported
        if language not in SUPPORTED_LANGUAGES:
            return self._fallback_chunk(raw_content)

        # Get the parser for this language
        parser = self._get_parser(language)
        if parser is None:
            return self._fallback_chunk(raw_content)

        # Parse the source code
        try:
            tree = parser.parse(raw_content.content.encode("utf-8"))
        except Exception:
            return self._fallback_chunk(raw_content)

        chunks: list[CodeChunk] = []

        # Always add file-level chunk
        chunks.append(CodeChunk(
            repo_id=raw_content.repo_id,
            file_path=file_path,
            language=raw_content.language or "unknown",
            chunk_type=ChunkType.FILE,
            start_line=1,
            end_line=len(raw_content.content.splitlines()),
            content=raw_content.content
        ))

        # Extract class and function chunks based on language
        if language == "java":
            chunks.extend(self._extract_java_chunks(tree, raw_content))
        elif language == "python":
            chunks.extend(self._extract_python_chunks(tree, raw_content))
        elif language == "javascript":
            chunks.extend(self._extract_javascript_chunks(tree, raw_content))
        elif language == "typescript":
            chunks.extend(self._extract_typescript_chunks(tree, raw_content))
        elif language in ("c", "cpp"):
            chunks.extend(self._extract_c_chunks(tree, raw_content, language))

        return chunks

    def _fallback_chunk(self, raw_content: RawContent) -> list[CodeChunk]:
        """Create a single file-level chunk for unsupported languages."""
        lines = raw_content.content.splitlines()
        return [CodeChunk(
            repo_id=raw_content.repo_id,
            file_path=raw_content.file_path,
            language=raw_content.language or "unknown",
            chunk_type=ChunkType.FILE,
            start_line=1,
            end_line=len(lines),
            content=raw_content.content
        )]

    def _extract_java_chunks(self, tree: Tree, raw_content: RawContent) -> list[CodeChunk]:
        """Extract class and method chunks from Java source."""
        chunks: list[CodeChunk] = []
        lines = raw_content.content.splitlines()

        def walk(node: Node) -> None:
            if node.type == "class_declaration":
                class_chunks = self._extract_java_class(node, lines, raw_content)
                chunks.extend(class_chunks)
            for child in node.children:
                walk(child)

        try:
            walk(tree.root_node)
        except Exception:
            pass

        return chunks

    def _extract_java_class(self, class_node: Node, lines: list[str], raw_content: RawContent) -> list[CodeChunk]:
        """Extract class and method chunks from a Java class node."""
        chunks: list[CodeChunk] = []

        # Get class name - it's in the children
        class_name = None
        for child in class_node.children:
            if child.type == "identifier":
                class_name = self._get_node_text(child, lines)
                break

        if class_name:
            start = class_node.start_point.row + 1
            end = class_node.end_point.row + 1
            class_content = "\n".join(lines[start-1:end])

            chunks.append(CodeChunk(
                repo_id=raw_content.repo_id,
                file_path=raw_content.file_path,
                language=raw_content.language or "unknown",
                chunk_type=ChunkType.CLASS,
                symbol_name=class_name,
                symbol_type="class",
                start_line=start,
                end_line=end,
                content=class_content
            ))

        # Find method declarations within the class - need to walk all children
        def find_methods(node: Node) -> None:
            if node.type == "method_declaration":
                method_chunks = self._extract_java_method(node, lines, raw_content)
                chunks.extend(method_chunks)
            for child in node.children:
                find_methods(child)

        find_methods(class_node)

        return chunks

    def _extract_java_method(self, method_node: Node, lines: list[str], raw_content: RawContent) -> list[CodeChunk]:
        """Extract method chunks from a Java method node."""
        chunks: list[CodeChunk] = []

        method_name = None
        for child in method_node.children:
            if child.type == "identifier":
                method_name = self._get_node_text(child, lines)
                break

        if method_name:
            start = method_node.start_point.row + 1
            end = method_node.end_point.row + 1
            method_content = "\n".join(lines[start-1:end])

            chunks.append(CodeChunk(
                repo_id=raw_content.repo_id,
                file_path=raw_content.file_path,
                language=raw_content.language or "unknown",
                chunk_type=ChunkType.FUNCTION,
                symbol_name=method_name,
                symbol_type="method",
                start_line=start,
                end_line=end,
                content=method_content
            ))

        return chunks

    def _extract_python_chunks(self, tree: Tree, raw_content: RawContent) -> list[CodeChunk]:
        """Extract class and function chunks from Python source."""
        chunks: list[CodeChunk] = []
        lines = raw_content.content.splitlines()

        def walk_node(node: Node):
            if node.type in ("class_definition", "function_definition"):
                symbol_name = None
                for child in node.children:
                    if child.type == "identifier":
                        symbol_name = self._get_node_text(child, lines)
                        break

                if symbol_name:
                    chunk_type = ChunkType.CLASS if node.type == "class_definition" else ChunkType.FUNCTION
                    start = node.start_point.row + 1
                    end = node.end_point.row + 1
                    content = "\n".join(lines[start-1:end])

                    chunks.append(CodeChunk(
                        repo_id=raw_content.repo_id,
                        file_path=raw_content.file_path,
                        language=raw_content.language or "unknown",
                        chunk_type=chunk_type,
                        symbol_name=symbol_name,
                        symbol_type="class" if node.type == "class_definition" else "function",
                        start_line=start,
                        end_line=end,
                        content=content
                    ))

            for child in node.children:
                walk_node(child)

        if tree.root_node:
            walk_node(tree.root_node)

        return chunks

    def _extract_javascript_chunks(self, tree: Tree, raw_content: RawContent) -> list[CodeChunk]:
        """Extract function and class chunks from JavaScript source."""
        chunks: list[CodeChunk] = []
        lines = raw_content.content.splitlines()

        def walk_node(node: Node) -> None:
            # Top-level function declarations
            if node.type == "function_declaration":
                symbol_name = None
                for child in node.children:
                    if child.type == "identifier":
                        symbol_name = self._get_node_text(child, lines)
                        break

                if symbol_name:
                    start = node.start_point.row + 1
                    end = node.end_point.row + 1
                    content = "\n".join(lines[start-1:end])

                    chunks.append(CodeChunk(
                        repo_id=raw_content.repo_id,
                        file_path=raw_content.file_path,
                        language=raw_content.language or "unknown",
                        chunk_type=ChunkType.FUNCTION,
                        symbol_name=symbol_name,
                        symbol_type="function",
                        start_line=start,
                        end_line=end,
                        content=content
                    ))

            # Class declarations
            elif node.type == "class_declaration":
                # Get class name
                class_name = None
                for child in node.children:
                    if child.type in ("identifier", "type_identifier"):
                        class_name = self._get_node_text(child, lines)
                        break

                if class_name:
                    start = node.start_point.row + 1
                    end = node.end_point.row + 1
                    class_content = "\n".join(lines[start-1:end])

                    chunks.append(CodeChunk(
                        repo_id=raw_content.repo_id,
                        file_path=raw_content.file_path,
                        language=raw_content.language or "unknown",
                        chunk_type=ChunkType.CLASS,
                        symbol_name=class_name,
                        symbol_type="class",
                        start_line=start,
                        end_line=end,
                        content=class_content
                    ))

                # Find method definitions inside class body
                for child in node.children:
                    if child.type == "class_body":
                        self._extract_js_methods(child, lines, raw_content, chunks)

            for child in node.children:
                walk_node(child)

        if tree.root_node:
            walk_node(tree.root_node)

        return chunks

    def _extract_js_methods(self, node: Node, lines: list[str], raw_content: RawContent, chunks: list[CodeChunk]) -> None:
        """Extract method definitions from class body."""
        for child in node.children:
            if child.type == "method_definition":
                method_name = None
                for c in child.children:
                    if c.type == "property_identifier":
                        method_name = self._get_node_text(c, lines)
                        break

                if method_name:
                    start = child.start_point.row + 1
                    end = child.end_point.row + 1
                    content = "\n".join(lines[start-1:end])

                    chunks.append(CodeChunk(
                        repo_id=raw_content.repo_id,
                        file_path=raw_content.file_path,
                        language=raw_content.language or "unknown",
                        chunk_type=ChunkType.FUNCTION,
                        symbol_name=method_name,
                        symbol_type="method",
                        start_line=start,
                        end_line=end,
                        content=content
                    ))

            # Recursively search for nested class bodies
            for c in child.children:
                if c.type == "class_body":
                    self._extract_js_methods(c, lines, raw_content, chunks)

    def _extract_ts_methods(self, node: Node, lines: list[str], raw_content: RawContent, chunks: list[CodeChunk]) -> None:
        """Extract method definitions from TypeScript class body."""
        for child in node.children:
            if child.type == "method_definition":
                method_name = None
                for c in child.children:
                    if c.type == "property_identifier":
                        method_name = self._get_node_text(c, lines)
                        break

                if method_name:
                    start = child.start_point.row + 1
                    end = child.end_point.row + 1
                    content = "\n".join(lines[start-1:end])

                    chunks.append(CodeChunk(
                        repo_id=raw_content.repo_id,
                        file_path=raw_content.file_path,
                        language=raw_content.language or "unknown",
                        chunk_type=ChunkType.FUNCTION,
                        symbol_name=method_name,
                        symbol_type="method",
                        start_line=start,
                        end_line=end,
                        content=content
                    ))

            # Recursively search for nested class bodies
            for c in child.children:
                if c.type == "class_body":
                    self._extract_ts_methods(c, lines, raw_content, chunks)

    def _extract_typescript_chunks(self, tree: Tree, raw_content: RawContent) -> list[CodeChunk]:
        """Extract interface, type, function, and class chunks from TypeScript source."""
        chunks: list[CodeChunk] = []
        lines = raw_content.content.splitlines()

        def walk_node(node: Node) -> None:
            # Interface declarations (uses type_identifier)
            if node.type == "interface_declaration":
                symbol_name = None
                for child in node.children:
                    if child.type == "type_identifier":
                        symbol_name = self._get_node_text(child, lines)
                        break

                if symbol_name:
                    start = node.start_point.row + 1
                    end = node.end_point.row + 1
                    content = "\n".join(lines[start-1:end])

                    chunks.append(CodeChunk(
                        repo_id=raw_content.repo_id,
                        file_path=raw_content.file_path,
                        language=raw_content.language or "unknown",
                        chunk_type=ChunkType.INTERFACE,
                        symbol_name=symbol_name,
                        symbol_type="interface",
                        start_line=start,
                        end_line=end,
                        content=content
                    ))

            # Type alias declarations (uses type_identifier)
            elif node.type == "type_alias_declaration":
                symbol_name = None
                for child in node.children:
                    if child.type == "type_identifier":
                        symbol_name = self._get_node_text(child, lines)
                        break

                if symbol_name:
                    start = node.start_point.row + 1
                    end = node.end_point.row + 1
                    content = "\n".join(lines[start-1:end])

                    chunks.append(CodeChunk(
                        repo_id=raw_content.repo_id,
                        file_path=raw_content.file_path,
                        language=raw_content.language or "unknown",
                        chunk_type=ChunkType.TYPE,
                        symbol_name=symbol_name,
                        symbol_type="type",
                        start_line=start,
                        end_line=end,
                        content=content
                    ))

            # Top-level function declarations (not method definitions)
            elif node.type == "function_declaration":
                symbol_name = None
                for child in node.children:
                    if child.type == "identifier":
                        symbol_name = self._get_node_text(child, lines)
                        break

                if symbol_name:
                    start = node.start_point.row + 1
                    end = node.end_point.row + 1
                    content = "\n".join(lines[start-1:end])

                    chunks.append(CodeChunk(
                        repo_id=raw_content.repo_id,
                        file_path=raw_content.file_path,
                        language=raw_content.language or "unknown",
                        chunk_type=ChunkType.FUNCTION,
                        symbol_name=symbol_name,
                        symbol_type="function",
                        start_line=start,
                        end_line=end,
                        content=content
                    ))

            # Class declarations (uses type_identifier)
            elif node.type == "class_declaration":
                symbol_name = None
                for child in node.children:
                    if child.type == "type_identifier":
                        symbol_name = self._get_node_text(child, lines)
                        break

                if symbol_name:
                    start = node.start_point.row + 1
                    end = node.end_point.row + 1
                    content = "\n".join(lines[start-1:end])

                    chunks.append(CodeChunk(
                        repo_id=raw_content.repo_id,
                        file_path=raw_content.file_path,
                        language=raw_content.language or "unknown",
                        chunk_type=ChunkType.CLASS,
                        symbol_name=symbol_name,
                        symbol_type="class",
                        start_line=start,
                        end_line=end,
                        content=content
                    ))

                # Extract method definitions inside class
                for child in node.children:
                    if child.type == "class_body":
                        self._extract_ts_methods(child, lines, raw_content, chunks)

            for child in node.children:
                walk_node(child)

        if tree.root_node:
            walk_node(tree.root_node)

        return chunks

    def _extract_c_chunks(self, tree: Tree, raw_content: RawContent, language: str) -> list[CodeChunk]:
        """Extract function chunks from C/C++ source."""
        chunks: list[CodeChunk] = []
        lines = raw_content.content.splitlines()

        def find_identifier(node: Node) -> str | None:
            """Recursively find identifier in node tree."""
            for child in node.children:
                if child.type == "identifier":
                    return self._get_node_text(child, lines)
                result = find_identifier(child)
                if result:
                    return result
            return None

        def walk_node(node: Node):
            # Function definitions
            if node.type == "function_definition":
                symbol_name = find_identifier(node)

                if symbol_name:
                    start = node.start_point.row + 1
                    end = node.end_point.row + 1
                    content = "\n".join(lines[start-1:end])

                    chunks.append(CodeChunk(
                        repo_id=raw_content.repo_id,
                        file_path=raw_content.file_path,
                        language=raw_content.language or "unknown",
                        chunk_type=ChunkType.FUNCTION,
                        symbol_name=symbol_name,
                        symbol_type="function",
                        start_line=start,
                        end_line=end,
                        content=content
                    ))

            # C++ class declarations
            elif language == "cpp" and node.type == "class_specifier":
                symbol_name = None
                for child in node.children:
                    if child.type == "type_identifier":
                        symbol_name = self._get_node_text(child, lines)
                        break

                if symbol_name:
                    start = node.start_point.row + 1
                    end = node.end_point.row + 1
                    content = "\n".join(lines[start-1:end])

                    chunks.append(CodeChunk(
                        repo_id=raw_content.repo_id,
                        file_path=raw_content.file_path,
                        language=raw_content.language or "unknown",
                        chunk_type=ChunkType.CLASS,
                        symbol_name=symbol_name,
                        symbol_type="class",
                        start_line=start,
                        end_line=end,
                        content=content
                    ))

            for child in node.children:
                walk_node(child)

        if tree.root_node:
            walk_node(tree.root_node)

        return chunks

    def _get_node_text(self, node: Node, lines: list[str]) -> str:
        """Get the text content of a tree-sitter node."""
        start = node.start_point.row
        end = node.end_point.row

        if start == end:
            return lines[start][node.start_point.column:node.end_point.column]
        else:
            result = [lines[start][node.start_point.column:]]
            for i in range(start + 1, end):
                result.append(lines[i])
            result.append(lines[end][:node.end_point.column])
            return "\n".join(result)
