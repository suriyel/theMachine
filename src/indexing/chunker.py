"""Code Chunker — splits source code files into AST-based chunks."""

import logging
import os
from dataclasses import dataclass, field

import tree_sitter as ts

from src.indexing.content_extractor import ExtractedFile

logger = logging.getLogger(__name__)

MAX_FUNCTION_LINES = 500
OVERLAP_LINES = 50


@dataclass
class LanguageNodeMap:
    """Maps tree-sitter node types for a specific language."""

    class_nodes: list[str]
    function_nodes: list[str]
    import_nodes: list[str]
    body_delimiter: str


@dataclass
class CodeChunk:
    """A chunk of source code extracted from an AST."""

    chunk_id: str
    repo_id: str
    branch: str
    file_path: str
    language: str
    chunk_type: str  # "file", "class", "function"
    symbol: str
    signature: str
    doc_comment: str
    parent_class: str
    content: str
    line_start: int
    line_end: int
    imports: list[str] = field(default_factory=list)
    top_level_symbols: list[str] = field(default_factory=list)


EXT_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".java": "java",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
}

LANGUAGE_NODE_MAPS: dict[str, LanguageNodeMap] = {
    "python": LanguageNodeMap(
        class_nodes=["class_definition"],
        function_nodes=["function_definition"],
        import_nodes=["import_statement", "import_from_statement"],
        body_delimiter=":",
    ),
    "java": LanguageNodeMap(
        class_nodes=[
            "class_declaration",
            "interface_declaration",
            "enum_declaration",
            "record_declaration",
        ],
        function_nodes=[
            "method_declaration",
            "constructor_declaration",
            "static_initializer",
        ],
        import_nodes=["import_declaration"],
        body_delimiter="{",
    ),
    "javascript": LanguageNodeMap(
        class_nodes=["class_declaration"],
        function_nodes=[
            "function_declaration",
            "arrow_function",
            "method_definition",
        ],
        import_nodes=["import_statement"],
        body_delimiter="{",
    ),
    "typescript": LanguageNodeMap(
        class_nodes=["class_declaration", "interface_declaration", "enum_declaration"],
        function_nodes=[
            "function_declaration",
            "arrow_function",
            "method_definition",
        ],
        import_nodes=["import_statement"],
        body_delimiter="{",
    ),
    "c": LanguageNodeMap(
        class_nodes=["struct_specifier", "enum_specifier"],
        function_nodes=["function_definition"],
        import_nodes=["preproc_include"],
        body_delimiter="{",
    ),
    "cpp": LanguageNodeMap(
        class_nodes=["class_specifier", "struct_specifier"],
        function_nodes=["function_definition"],
        import_nodes=["preproc_include", "using_declaration"],
        body_delimiter="{",
    ),
}

# Grammar module imports (lazy-loaded)
_GRAMMAR_MODULES: dict[str, str] = {
    "python": "tree_sitter_python",
    "java": "tree_sitter_java",
    "javascript": "tree_sitter_javascript",
    "typescript": "tree_sitter_typescript",
    "c": "tree_sitter_c",
    "cpp": "tree_sitter_cpp",
}


class Chunker:
    """Splits source code files into hierarchical AST-based chunks."""

    def __init__(self) -> None:
        self._parsers: dict[str, ts.Parser] = {}

    def _get_or_create_parser(self, language: str) -> ts.Parser:
        """Get or create a tree-sitter parser for the given language."""
        if language in self._parsers:
            return self._parsers[language]

        import importlib

        mod_name = _GRAMMAR_MODULES[language]
        mod = importlib.import_module(mod_name)

        # TypeScript grammar module has a special API
        if language == "typescript":
            lang_fn = getattr(mod, "language_typescript", None)
            if lang_fn is None:
                lang_fn = mod.language
            lang = ts.Language(lang_fn())
        else:
            lang = ts.Language(mod.language())

        parser = ts.Parser(lang)
        self._parsers[language] = parser
        return parser

    def chunk(
        self, file: ExtractedFile, repo_id: str, branch: str
    ) -> list[CodeChunk]:
        """Produce all chunks for a single ExtractedFile."""
        ext = os.path.splitext(file.path)[1].lower()
        language = EXT_TO_LANGUAGE.get(ext)

        if language is None:
            return [self.fallback_file_chunk(file, repo_id, branch)]

        try:
            tree = self.parse_ast(file.content, language)
        except Exception:
            logger.warning(
                "Parse failed for %s, falling back to file chunk", file.path
            )
            return [self.fallback_file_chunk(file, repo_id, branch)]

        chunks: list[CodeChunk] = []
        chunks.append(
            self.extract_file_chunk(tree, file, repo_id, branch, language)
        )
        chunks.extend(
            self.extract_class_chunks(tree, file, repo_id, branch, language)
        )
        chunks.extend(
            self.extract_function_chunks(
                tree, file, repo_id, branch, language
            )
        )
        return chunks

    def parse_ast(self, content: str, language: str) -> ts.Tree:
        """Parse source content into a tree-sitter AST."""
        if language not in LANGUAGE_NODE_MAPS:
            raise ValueError(f"Unsupported language: {language}")
        parser = self._get_or_create_parser(language)
        return parser.parse(content.encode("utf-8"))

    def extract_file_chunk(
        self,
        tree: ts.Tree,
        file: ExtractedFile,
        repo_id: str,
        branch: str,
        language: str | None = None,
    ) -> CodeChunk:
        """Extract the top-level L1 file chunk."""
        if language is None:
            language = EXT_TO_LANGUAGE.get(
                os.path.splitext(file.path)[1].lower(), ""
            )

        node_map = LANGUAGE_NODE_MAPS.get(language)
        imports = self.extract_imports(tree, language)
        top_level_symbols: list[str] = []

        if node_map:
            all_interesting = (
                node_map.class_nodes + node_map.function_nodes
            )
            for child in tree.root_node.children:
                if child.type in all_interesting:
                    name = _get_node_name(child)
                    if name:
                        top_level_symbols.append(name)
                elif child.type == "export_statement":
                    for inner in child.children:
                        if inner.type in all_interesting:
                            name = _get_node_name(inner)
                            if name:
                                top_level_symbols.append(name)
                elif child.type == "decorated_definition":
                    inner = _find_decorated_inner(
                        child, all_interesting
                    )
                    if inner is not None:
                        name = _get_node_name(inner)
                        if name:
                            top_level_symbols.append(name)
                elif (
                    child.type == "expression_statement"
                    and language == "javascript"
                ):
                    result = _is_prototype_assign(child)
                    if result is not None:
                        top_level_symbols.append(result[0])
                elif (
                    child.type == "type_definition"
                    and language in ("c", "cpp")
                ):
                    inner = _find_child_of_type(child, all_interesting)
                    if inner is not None:
                        name = _get_typedef_name(child) or _get_node_name(inner)
                        if name:
                            top_level_symbols.append(name)
                elif (
                    child.type in ("preproc_ifdef", "preproc_if")
                    and language in ("c", "cpp")
                ):
                    # Recurse into header guards for symbols
                    for inner in child.children:
                        if inner.type in all_interesting:
                            name = _get_node_name(inner)
                            if name:
                                top_level_symbols.append(name)
                        elif inner.type == "type_definition":
                            sub = _find_child_of_type(inner, all_interesting)
                            if sub is not None:
                                name = _get_typedef_name(inner) or _get_node_name(sub)
                                if name:
                                    top_level_symbols.append(name)
                elif (
                    child.type == "namespace_definition"
                    and language == "cpp"
                ):
                    _collect_namespace_symbols(
                        child, all_interesting, top_level_symbols
                    )
                elif (
                    child.type == "template_declaration"
                    and language == "cpp"
                ):
                    inner = _find_child_of_type(child, all_interesting)
                    if inner is not None:
                        name = _get_node_name(inner)
                        if name:
                            top_level_symbols.append(name)

        content_parts = imports + ([""] if imports else []) + top_level_symbols
        content = "\n".join(content_parts)

        chunk_id = f"{repo_id}:{branch}:{file.path}::file:0"
        return CodeChunk(
            chunk_id=chunk_id,
            repo_id=repo_id,
            branch=branch,
            file_path=file.path,
            language=language,
            chunk_type="file",
            symbol="",
            signature="",
            doc_comment="",
            parent_class="",
            content=content,
            line_start=0,
            line_end=tree.root_node.end_point[0],
            imports=imports,
            top_level_symbols=top_level_symbols,
        )

    def extract_class_chunks(
        self,
        tree: ts.Tree,
        file: ExtractedFile,
        repo_id: str,
        branch: str,
        language: str | None = None,
    ) -> list[CodeChunk]:
        """Extract L2 class/interface chunks."""
        if language is None:
            language = EXT_TO_LANGUAGE.get(
                os.path.splitext(file.path)[1].lower(), ""
            )
        node_map = LANGUAGE_NODE_MAPS.get(language)
        if not node_map or not node_map.class_nodes:
            return []

        chunks: list[CodeChunk] = []
        self._walk_classes(
            tree.root_node, file, repo_id, branch, language, node_map, chunks
        )
        return chunks

    def _walk_classes(
        self,
        node: ts.Node,
        file: ExtractedFile,
        repo_id: str,
        branch: str,
        language: str,
        node_map: LanguageNodeMap,
        chunks: list[CodeChunk],
    ) -> None:
        """Recursively find class nodes and create L2 chunks."""
        for child in node.children:
            # Unwrap export_statement: recurse into export node so its class
            # children are found by the class_nodes check below on next level.
            if child.type == "export_statement":
                self._walk_classes(
                    child, file, repo_id, branch, language, node_map, chunks
                )
                continue
            # Unwrap TS namespace: expression_statement > internal_module
            # or direct internal_module (inside export_statement)
            if child.type in ("expression_statement", "internal_module"):
                target = child
                if child.type == "expression_statement":
                    target = None
                    for sub in child.children:
                        if sub.type == "internal_module":
                            target = sub
                            break
                if target is not None and target.type == "internal_module":
                    body = _get_namespace_body(target)
                    if body:
                        self._walk_classes(
                            body, file, repo_id, branch,
                            language, node_map, chunks,
                        )
                continue
            # C: unwrap type_definition containing struct_specifier
            if child.type == "type_definition" and language in ("c", "cpp"):
                inner = _find_child_of_type(child, node_map.class_nodes)
                if inner is not None:
                    # Symbol is the typedef alias (last type_identifier in declarator)
                    name = _get_typedef_name(child) or _get_node_name(inner)
                    signature = self.extract_signature(inner, language)
                    doc_comment = self.extract_doc_comment(child, language)
                    method_sigs: list[str] = []
                    body = _get_body_node(inner, language)
                    if body:
                        for member in body.children:
                            if member.type in node_map.function_nodes:
                                m_name = _get_node_name(member)
                                m_sig = self.extract_signature(member, language)
                                method_sigs.append(m_sig if m_sig else m_name)
                    content = signature + "\n" + doc_comment
                    if method_sigs:
                        content += "\n" + "\n".join(method_sigs)
                    chunk_id = (
                        f"{repo_id}:{branch}:{file.path}:"
                        f"{name}:class:{child.start_point[0]}"
                    )
                    chunks.append(
                        CodeChunk(
                            chunk_id=chunk_id,
                            repo_id=repo_id,
                            branch=branch,
                            file_path=file.path,
                            language=language,
                            chunk_type="class",
                            symbol=name,
                            signature=signature,
                            doc_comment=doc_comment,
                            parent_class="",
                            content=content,
                            line_start=child.start_point[0],
                            line_end=child.end_point[0],
                        )
                    )
                continue
            # C/C++: recurse into preproc_ifdef / preproc_if to find class nodes
            if child.type in ("preproc_ifdef", "preproc_if") and language in ("c", "cpp"):
                self._walk_classes(
                    child, file, repo_id, branch, language, node_map, chunks
                )
                continue
            # C++: recurse into namespace_definition body
            if child.type == "namespace_definition" and language == "cpp":
                body = _find_child_of_type(child, ["declaration_list"])
                if body is not None:
                    self._walk_classes(
                        body, file, repo_id, branch, language, node_map, chunks
                    )
                continue
            # C++: single-level unwrap template_declaration for inner class
            if child.type == "template_declaration" and language == "cpp":
                inner = _find_child_of_type(child, node_map.class_nodes)
                if inner is not None:
                    name = _get_node_name(inner)
                    signature = self.extract_signature(inner, language)
                    doc_comment = self.extract_doc_comment(child, language)
                    method_sigs: list[str] = []
                    body = _get_body_node(inner, language)
                    if body:
                        for member in body.children:
                            if member.type in node_map.function_nodes:
                                m_name = _get_node_name(member)
                                m_sig = self.extract_signature(member, language)
                                method_sigs.append(m_sig if m_sig else m_name)
                    content = signature + "\n" + doc_comment
                    if method_sigs:
                        content += "\n" + "\n".join(method_sigs)
                    chunk_id = (
                        f"{repo_id}:{branch}:{file.path}:"
                        f"{name}:class:{child.start_point[0]}"
                    )
                    chunks.append(
                        CodeChunk(
                            chunk_id=chunk_id,
                            repo_id=repo_id,
                            branch=branch,
                            file_path=file.path,
                            language=language,
                            chunk_type="class",
                            symbol=name,
                            signature=signature,
                            doc_comment=doc_comment,
                            parent_class="",
                            content=content,
                            line_start=child.start_point[0],
                            line_end=child.end_point[0],
                        )
                    )
                    if body:
                        self._walk_classes(
                            body, file, repo_id, branch, language, node_map, chunks
                        )
                continue
            # Unwrap decorated_definition: find inner class node
            if child.type == "decorated_definition":
                inner = _find_decorated_inner(child, node_map.class_nodes)
                if inner is None:
                    continue
                name = _get_node_name(inner)
                signature = self.extract_signature(inner, language)
                doc_comment = self.extract_doc_comment(inner, language)

                method_sigs: list[str] = []
                body = _get_body_node(inner, language)
                if body:
                    for member in body.children:
                        if member.type in node_map.function_nodes:
                            m_name = _get_node_name(member)
                            m_sig = self.extract_signature(
                                member, language
                            )
                            method_sigs.append(
                                m_sig if m_sig else m_name
                            )

                # Include decorator text (SRS: decorator preserved)
                decorator_lines: list[str] = []
                for dc in child.children:
                    if dc.type == "decorator":
                        dt = dc.text.decode("utf-8") if dc.text else ""
                        if dt:
                            decorator_lines.append(dt)
                decorator_prefix = (
                    "\n".join(decorator_lines) + "\n"
                    if decorator_lines
                    else ""
                )
                content = decorator_prefix + signature + "\n" + doc_comment
                if method_sigs:
                    content += "\n" + "\n".join(method_sigs)

                chunk_id = (
                    f"{repo_id}:{branch}:{file.path}:"
                    f"{name}:class:{child.start_point[0]}"
                )
                chunks.append(
                    CodeChunk(
                        chunk_id=chunk_id,
                        repo_id=repo_id,
                        branch=branch,
                        file_path=file.path,
                        language=language,
                        chunk_type="class",
                        symbol=name,
                        signature=signature,
                        doc_comment=doc_comment,
                        parent_class="",
                        content=content,
                        line_start=child.start_point[0],
                        line_end=child.end_point[0],
                    )
                )
                if body:
                    self._walk_classes(
                        body,
                        file,
                        repo_id,
                        branch,
                        language,
                        node_map,
                        chunks,
                    )
                continue
            if child.type in node_map.class_nodes:
                name = _get_node_name(child)
                signature = self.extract_signature(child, language)
                doc_comment = self.extract_doc_comment(child, language)

                # Collect method signatures
                method_sigs: list[str] = []
                body = _get_body_node(child, language)
                if body:
                    for member in body.children:
                        if member.type in node_map.function_nodes:
                            m_name = _get_node_name(member)
                            m_sig = self.extract_signature(member, language)
                            method_sigs.append(
                                m_sig if m_sig else m_name
                            )

                content = signature + "\n" + doc_comment
                if method_sigs:
                    content += "\n" + "\n".join(method_sigs)

                chunk_id = (
                    f"{repo_id}:{branch}:{file.path}:"
                    f"{name}:class:{child.start_point[0]}"
                )
                chunks.append(
                    CodeChunk(
                        chunk_id=chunk_id,
                        repo_id=repo_id,
                        branch=branch,
                        file_path=file.path,
                        language=language,
                        chunk_type="class",
                        symbol=name,
                        signature=signature,
                        doc_comment=doc_comment,
                        parent_class="",
                        content=content,
                        line_start=child.start_point[0],
                        line_end=child.end_point[0],
                    )
                )
                # Recurse for nested classes
                if body:
                    self._walk_classes(
                        body,
                        file,
                        repo_id,
                        branch,
                        language,
                        node_map,
                        chunks,
                    )

    def extract_function_chunks(
        self,
        tree: ts.Tree,
        file: ExtractedFile,
        repo_id: str,
        branch: str,
        language: str | None = None,
    ) -> list[CodeChunk]:
        """Extract L3 function/method chunks."""
        if language is None:
            language = EXT_TO_LANGUAGE.get(
                os.path.splitext(file.path)[1].lower(), ""
            )
        node_map = LANGUAGE_NODE_MAPS.get(language)
        if not node_map:
            return []

        chunks: list[CodeChunk] = []
        self._walk_functions(
            tree.root_node,
            file,
            repo_id,
            branch,
            language,
            node_map,
            chunks,
            parent_class="",
        )
        return chunks

    def _walk_functions(
        self,
        node: ts.Node,
        file: ExtractedFile,
        repo_id: str,
        branch: str,
        language: str,
        node_map: LanguageNodeMap,
        chunks: list[CodeChunk],
        parent_class: str,
    ) -> None:
        """Recursively find function nodes and create L3 chunks."""
        for child in node.children:
            # C: declaration with function_declarator but no body = prototype
            if child.type == "declaration" and language == "c":
                func_decl = _find_child_of_type(child, ["function_declarator"])
                has_body = any(
                    sub.type == "compound_statement" for sub in child.children
                )
                if func_decl is not None and not has_body:
                    name = _get_node_name(func_decl)
                    if name:
                        self._add_function_chunk(
                            child,
                            name,
                            file,
                            repo_id,
                            branch,
                            language,
                            parent_class,
                            chunks,
                        )
                continue
            # C/C++: recurse into preproc_ifdef / preproc_if
            if child.type in ("preproc_ifdef", "preproc_if") and language in ("c", "cpp"):
                self._walk_functions(
                    child,
                    file,
                    repo_id,
                    branch,
                    language,
                    node_map,
                    chunks,
                    parent_class=parent_class,
                )
                continue
            # C++: recurse into namespace_definition body
            if child.type == "namespace_definition" and language == "cpp":
                body = _find_child_of_type(child, ["declaration_list"])
                if body is not None:
                    self._walk_functions(
                        body,
                        file,
                        repo_id,
                        branch,
                        language,
                        node_map,
                        chunks,
                        parent_class=parent_class,
                    )
                continue
            # C++: single-level unwrap template_declaration
            if child.type == "template_declaration" and language == "cpp":
                inner_class = _find_child_of_type(child, node_map.class_nodes)
                if inner_class is not None:
                    cls_name = _get_node_name(inner_class)
                    body = _get_body_node(inner_class, language)
                    if body:
                        self._walk_functions(
                            body,
                            file,
                            repo_id,
                            branch,
                            language,
                            node_map,
                            chunks,
                            parent_class=cls_name,
                        )
                else:
                    inner_func = _find_child_of_type(child, node_map.function_nodes)
                    if inner_func is not None:
                        name = _get_node_name(inner_func)
                        self._add_function_chunk(
                            inner_func,
                            name,
                            file,
                            repo_id,
                            branch,
                            language,
                            parent_class,
                            chunks,
                        )
                continue
            if child.type == "decorated_definition":
                # Unwrap decorated_definition to find inner class/function
                all_targets = (
                    node_map.class_nodes + node_map.function_nodes
                )
                inner = _find_decorated_inner(child, all_targets)
                if inner is None:
                    continue
                if inner.type in node_map.class_nodes:
                    cls_name = _get_node_name(inner)
                    body = _get_body_node(inner, language)
                    if body:
                        self._walk_functions(
                            body,
                            file,
                            repo_id,
                            branch,
                            language,
                            node_map,
                            chunks,
                            parent_class=cls_name,
                        )
                elif inner.type in node_map.function_nodes:
                    name = _get_node_name(inner)
                    # Pass `child` (decorated_definition) so content
                    # includes decorator text
                    self._add_function_chunk(
                        child,
                        name,
                        file,
                        repo_id,
                        branch,
                        language,
                        parent_class,
                        chunks,
                    )
            elif child.type in node_map.class_nodes:
                # Recurse into class body with class name as parent
                cls_name = _get_node_name(child)
                body = _get_body_node(child, language)
                if body:
                    self._walk_functions(
                        body,
                        file,
                        repo_id,
                        branch,
                        language,
                        node_map,
                        chunks,
                        parent_class=cls_name,
                    )
            elif child.type in (
                "lexical_declaration",
                "variable_declaration",
                "export_statement",
            ):
                # JS/TS: const x = (args) => ...
                arrow = _find_arrow_in_declaration(child)
                if arrow:
                    var_name = _get_var_name_from_declaration(child)
                    self._add_function_chunk(
                        arrow,
                        var_name,
                        file,
                        repo_id,
                        branch,
                        language,
                        parent_class,
                        chunks,
                    )
                elif child.type == "export_statement":
                    # export function foo() / export class Foo — unwrap
                    for inner in child.children:
                        if inner.type in node_map.function_nodes:
                            name = _get_node_name(inner)
                            self._add_function_chunk(
                                inner,
                                name,
                                file,
                                repo_id,
                                branch,
                                language,
                                parent_class,
                                chunks,
                            )
                        elif inner.type in node_map.class_nodes:
                            cls_name = _get_node_name(inner)
                            body = _get_body_node(inner, language)
                            if body:
                                self._walk_functions(
                                    body,
                                    file,
                                    repo_id,
                                    branch,
                                    language,
                                    node_map,
                                    chunks,
                                    parent_class=cls_name,
                                )
                        elif inner.type == "internal_module":
                            ns_body = _get_namespace_body(inner)
                            if ns_body:
                                self._walk_functions(
                                    ns_body,
                                    file,
                                    repo_id,
                                    branch,
                                    language,
                                    node_map,
                                    chunks,
                                    parent_class=parent_class,
                                )
            elif child.type == "expression_statement":
                if language == "javascript":
                    # JS prototype-assigned functions:
                    # obj.method = function(...){} or obj.method = (...) => {}
                    result = _is_prototype_assign(child)
                    if result is not None:
                        prop_name, _func_node = result
                        self._add_function_chunk(
                            child,
                            prop_name,
                            file,
                            repo_id,
                            branch,
                            language,
                            parent_class,
                            chunks,
                        )
                # TS namespace: expression_statement > internal_module
                for sub in child.children:
                    if sub.type == "internal_module":
                        ns_body = _get_namespace_body(sub)
                        if ns_body:
                            self._walk_functions(
                                ns_body,
                                file,
                                repo_id,
                                branch,
                                language,
                                node_map,
                                chunks,
                                parent_class=parent_class,
                            )
            elif child.type in node_map.function_nodes:
                name = _get_node_name(child)
                self._add_function_chunk(
                    child,
                    name,
                    file,
                    repo_id,
                    branch,
                    language,
                    parent_class,
                    chunks,
                )

    def _add_function_chunk(
        self,
        node: ts.Node,
        name: str,
        file: ExtractedFile,
        repo_id: str,
        branch: str,
        language: str,
        parent_class: str,
        chunks: list[CodeChunk],
    ) -> None:
        """Create L3 chunk(s) for a function node, splitting if >500 lines."""
        signature = self.extract_signature(node, language)
        doc_comment = self.extract_doc_comment(node, language)

        func_text = node.text.decode("utf-8") if node.text else ""
        func_lines = func_text.split("\n")
        line_count = len(func_lines)

        if line_count > MAX_FUNCTION_LINES:
            self._split_large_function(
                func_lines,
                node,
                file,
                repo_id,
                branch,
                language,
                name,
                signature,
                doc_comment,
                parent_class,
                chunks,
            )
        else:
            chunk_id = (
                f"{repo_id}:{branch}:{file.path}:"
                f"{name}:function:{node.start_point[0]}"
            )
            chunks.append(
                CodeChunk(
                    chunk_id=chunk_id,
                    repo_id=repo_id,
                    branch=branch,
                    file_path=file.path,
                    language=language,
                    chunk_type="function",
                    symbol=name,
                    signature=signature,
                    doc_comment=doc_comment,
                    parent_class=parent_class,
                    content=func_text,
                    line_start=node.start_point[0],
                    line_end=node.end_point[0],
                )
            )

    def _split_large_function(
        self,
        func_lines: list[str],
        node: ts.Node,
        file: ExtractedFile,
        repo_id: str,
        branch: str,
        language: str,
        name: str,
        signature: str,
        doc_comment: str,
        parent_class: str,
        chunks: list[CodeChunk],
    ) -> None:
        """Split a large function into overlapping windows."""
        line_count = len(func_lines)
        start = 0
        part = 1
        func_start_line = node.start_point[0]

        while start < line_count:
            end = min(start + MAX_FUNCTION_LINES, line_count)
            window = func_lines[start:end]
            window_text = "\n".join(window)

            chunk_id = (
                f"{repo_id}:{branch}:{file.path}:"
                f"{name}_part_{part}:function:{func_start_line + start}"
            )
            chunks.append(
                CodeChunk(
                    chunk_id=chunk_id,
                    repo_id=repo_id,
                    branch=branch,
                    file_path=file.path,
                    language=language,
                    chunk_type="function",
                    symbol=name,
                    signature=signature,
                    doc_comment=doc_comment,
                    parent_class=parent_class,
                    content=window_text,
                    line_start=func_start_line + start,
                    line_end=func_start_line + end - 1,
                )
            )

            if end >= line_count:
                break
            start = end - OVERLAP_LINES
            part += 1

    def extract_signature(self, node: ts.Node, language: str) -> str:
        """Extract the signature of a function or class node."""
        try:
            node_text = node.text.decode("utf-8") if node.text else ""
            node_map = LANGUAGE_NODE_MAPS.get(language)
            if not node_map:
                return ""
            delimiter = node_map.body_delimiter

            if language == "python":
                # For Python, find the body delimiter `:` that comes
                # after parameter list (respecting parentheses depth)
                return _extract_python_signature(node_text, delimiter)
            else:
                # C-family: first `{`
                idx = node_text.find(delimiter)
                if idx == -1:
                    return node_text.split("\n")[0]
                return node_text[:idx].rstrip()
        except Exception:
            return ""

    def extract_doc_comment(self, node: ts.Node, language: str) -> str:
        """Extract the docstring or doc comment for a node."""
        try:
            if language == "python":
                return self._extract_python_docstring(node)
            else:
                return self._extract_c_family_doc_comment(node)
        except Exception:
            return ""

    def _extract_python_docstring(self, node: ts.Node) -> str:
        """Extract Python triple-quoted docstring from a class or function."""
        # Look for the body block
        body = None
        for child in node.children:
            if child.type == "block":
                body = child
                break
        if not body or not body.children:
            return ""

        # First child of block should be expression_statement with string
        first = body.children[0]
        if first.type == "expression_statement":
            for sub in first.children:
                if sub.type == "string":
                    raw = sub.text.decode("utf-8") if sub.text else ""
                    # Strip triple quotes
                    for q in ('"""', "'''"):
                        if raw.startswith(q) and raw.endswith(q):
                            return raw[3:-3].strip()
                    return raw.strip("\"'").strip()
        return ""

    def _extract_c_family_doc_comment(self, node: ts.Node) -> str:
        """Extract Javadoc / block comment preceding a node."""
        # Strategy: look at previous sibling (named or unnamed)
        comment_types = {"comment", "block_comment"}

        # Check prev_sibling first (catches block_comment in Java)
        prev = node.prev_sibling
        if prev and prev.type in comment_types:
            return _clean_comment(prev.text.decode("utf-8"))

        prev = node.prev_named_sibling
        if prev and prev.type in comment_types:
            return _clean_comment(prev.text.decode("utf-8"))

        # For top-level nodes, check parent's children list
        if node.parent:
            for i, child in enumerate(node.parent.children):
                if child.id == node.id and i > 0:
                    prev_node = node.parent.children[i - 1]
                    if prev_node.type in comment_types:
                        return _clean_comment(
                            prev_node.text.decode("utf-8")
                        )
                    break

        return ""

    def extract_imports(self, tree: ts.Tree, language: str) -> list[str]:
        """Extract import statements from the AST."""
        node_map = LANGUAGE_NODE_MAPS.get(language)
        if not node_map:
            return []

        imports: list[str] = []
        self._collect_imports(tree.root_node, node_map.import_nodes, imports)
        if language == "javascript":
            _collect_require_imports(tree.root_node, imports)
        return imports

    def _collect_imports(
        self,
        node: "ts.Node",
        import_types: list[str],
        imports: list[str],
    ) -> None:
        """Recursively collect import nodes (handles #ifndef header guards)."""
        for child in node.children:
            if child.type in import_types:
                text = child.text.decode("utf-8") if child.text else ""
                if text:
                    imports.append(text.strip())
            elif child.type in ("preproc_ifdef", "preproc_if"):
                self._collect_imports(child, import_types, imports)

    def fallback_file_chunk(
        self, file: ExtractedFile, repo_id: str, branch: str
    ) -> CodeChunk:
        """Create a single L1 chunk for unsupported languages."""
        ext = os.path.splitext(file.path)[1].lower()
        language = EXT_TO_LANGUAGE.get(ext, "unknown")
        chunk_id = f"{repo_id}:{branch}:{file.path}::file:0"
        return CodeChunk(
            chunk_id=chunk_id,
            repo_id=repo_id,
            branch=branch,
            file_path=file.path,
            language=language,
            chunk_type="file",
            symbol="",
            signature="",
            doc_comment="",
            parent_class="",
            content=file.content,
            line_start=0,
            line_end=max(0, file.content.count("\n")),
            imports=[],
            top_level_symbols=[],
        )


def _find_decorated_inner(
    node: ts.Node, target_types: list[str]
) -> ts.Node | None:
    """Find the inner class/function node inside a decorated_definition."""
    for child in node.children:
        if child.type in target_types:
            return child
    return None


def _get_node_name(node: ts.Node) -> str:
    """Extract the name/identifier from a class or function node."""
    # Java static_initializer has no identifier — use sentinel name
    if node.type == "static_initializer":
        return "<static>"
    # First pass: look for direct 'identifier' or 'name'
    for child in node.children:
        if child.type in ("identifier", "name", "property_identifier"):
            return child.text.decode("utf-8") if child.text else ""
    # Second pass: look inside declarator nodes (C/C++ function_declarator)
    for child in node.children:
        if child.type in ("function_declarator", "declarator"):
            for sub in child.children:
                if sub.type in ("identifier", "field_identifier"):
                    return sub.text.decode("utf-8") if sub.text else ""
    # Third pass: fall back to type_identifier (C++ class_specifier)
    for child in node.children:
        if child.type == "type_identifier":
            return child.text.decode("utf-8") if child.text else ""
    return ""


def _get_body_node(node: ts.Node, language: str) -> ts.Node | None:
    """Get the body/block child of a class or function node."""
    if language == "python":
        for child in node.children:
            if child.type == "block":
                return child
    else:
        # C-family: look for class_body, body, block, etc.
        for child in node.children:
            if child.type in (
                "class_body",
                "interface_body",
                "block",
                "field_declaration_list",
                "declaration_list",
            ):
                return child
            # Java enum: enum_body > enum_body_declarations holds methods
            if child.type == "enum_body":
                for sub in child.children:
                    if sub.type == "enum_body_declarations":
                        return sub
                return child
    return None


def _extract_python_signature(text: str, delimiter: str) -> str:
    """Extract Python signature, handling parenthesized multi-line params."""
    depth = 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == delimiter and depth == 0:
            return text[:i].rstrip()
    # No delimiter found, return first line
    return text.split("\n")[0]


def _find_arrow_in_declaration(node: ts.Node) -> ts.Node | None:
    """Find an arrow_function inside a lexical/variable declaration."""
    for child in node.children:
        if child.type == "variable_declarator":
            for sub in child.children:
                if sub.type == "arrow_function":
                    return sub
        # Also handle export_statement wrapping
        if child.type in ("lexical_declaration", "variable_declaration"):
            result = _find_arrow_in_declaration(child)
            if result:
                return result
    return None


def _get_var_name_from_declaration(node: ts.Node) -> str:
    """Extract variable name from a declaration containing an arrow function."""
    for child in node.children:
        if child.type == "variable_declarator":
            for sub in child.children:
                if sub.type == "identifier":
                    return sub.text.decode("utf-8") if sub.text else ""
        if child.type in ("lexical_declaration", "variable_declaration"):
            result = _get_var_name_from_declaration(child)
            if result:
                return result
    return ""


def _get_namespace_body(node: ts.Node) -> ts.Node | None:
    """Get the statement_block body of a TS internal_module (namespace)."""
    for child in node.children:
        if child.type == "statement_block":
            return child
    return None


def _clean_comment(text: str) -> str:
    """Clean up a comment block by removing comment markers."""
    lines = text.split("\n")
    cleaned: list[str] = []
    for line in lines:
        line = line.strip()
        if line.startswith("/**"):
            line = line[3:].strip()
        elif line.startswith("/*"):
            line = line[2:].strip()
        elif line.startswith("*/"):
            continue
        elif line.startswith("*"):
            line = line[1:].strip()
        elif line.startswith("//"):
            line = line[2:].strip()
        if line:
            cleaned.append(line)
    return "\n".join(cleaned)


def _is_prototype_assign(node: ts.Node) -> tuple[str, ts.Node] | None:
    """Detect JS prototype-assigned function: obj.x = function/arrow.

    Returns (property_name, function_node) if pattern matches, else None.
    """
    # Find assignment_expression child
    assign = None
    for child in node.children:
        if child.type == "assignment_expression":
            assign = child
            break
    if assign is None:
        return None

    # Check LHS is member_expression, RHS is function
    lhs = None
    rhs = None
    for child in assign.children:
        if child.type == "member_expression":
            lhs = child
        elif child.type in ("function_expression", "arrow_function"):
            rhs = child

    if lhs is None or rhs is None:
        return None

    # Extract property name from member_expression
    for child in lhs.children:
        if child.type == "property_identifier":
            prop_name = child.text.decode("utf-8") if child.text else ""
            if prop_name:
                return (prop_name, rhs)

    return None


def _collect_require_imports(
    node: ts.Node, imports: list[str]
) -> None:
    """Collect CommonJS require() imports from JS root children."""
    for child in node.children:
        if child.type in ("variable_declaration", "lexical_declaration"):
            for declarator in child.children:
                if declarator.type == "variable_declarator":
                    for sub in declarator.children:
                        if sub.type == "call_expression":
                            _extract_require_arg(sub, imports)


def _extract_require_arg(
    call_node: ts.Node, imports: list[str]
) -> None:
    """Extract module path from a require('module') call_expression."""
    func_name = None
    arg_str = None
    for child in call_node.children:
        if child.type == "identifier":
            text = child.text.decode("utf-8") if child.text else ""
            if text == "require":
                func_name = "require"
        elif child.type == "arguments":
            for arg in child.children:
                if arg.type == "string":
                    raw = arg.text.decode("utf-8") if arg.text else ""
                    # Strip outer quotes
                    arg_str = raw.strip("'\"")
    if func_name == "require" and arg_str:
        imports.append(arg_str)


def _find_child_of_type(
    node: ts.Node, target_types: list[str]
) -> "ts.Node | None":
    """Return the first direct child whose type is in target_types."""
    for child in node.children:
        if child.type in target_types:
            return child
    return None


def _collect_namespace_symbols(
    ns_node: ts.Node,
    interesting_types: list[str],
    symbols: list[str],
) -> None:
    """Recursively collect symbols from C++ namespace_definition nodes."""
    body = _find_child_of_type(ns_node, ["declaration_list"])
    if body is None:
        return
    for inner in body.children:
        if inner.type in interesting_types:
            name = _get_node_name(inner)
            if name:
                symbols.append(name)
        elif inner.type == "namespace_definition":
            _collect_namespace_symbols(inner, interesting_types, symbols)
        elif inner.type == "template_declaration":
            sub = _find_child_of_type(inner, interesting_types)
            if sub is not None:
                name = _get_node_name(sub)
                if name:
                    symbols.append(name)


def _get_typedef_name(node: ts.Node) -> str:
    """Get the typedef alias from a type_definition node.

    In C tree-sitter AST the typedef alias is the last type_identifier
    that appears as a *direct* child of type_definition (the declarator).
    """
    # The declarator child holds the alias name for simple typedefs.
    # Iterate in reverse to pick the last type_identifier (the alias).
    last: str = ""
    for child in node.children:
        if child.type == "type_identifier":
            last = child.text.decode("utf-8") if child.text else ""
    return last
