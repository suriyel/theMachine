# Feature #38 Design: C typedef struct + function prototypes + enum

**Feature ID**: 38
**Date**: 2026-03-22
**Depends on**: Feature #6 (Code Chunking)
**Status**: Design

---

## 1. Overview

Extend the C language chunking support in `src/indexing/chunker.py` to handle three C-specific patterns:

1. **`typedef struct`** — `type_definition` nodes wrapping `struct_specifier` → produce L2 chunks with the typedef name as symbol
2. **Function prototypes** — `declaration` nodes containing `function_declarator` but no body (`;`-terminated) → produce L3 chunks
3. **`enum_specifier`** — enum declarations → produce L2 chunks with the enum tag name as symbol
4. **`#ifndef`/`#if` header guards** — `preproc_ifdef`/`preproc_if` wrappers → recurse into children for all of the above

---

## 2. Tree-sitter AST Shapes

### 2.1 typedef struct

```
(type_definition
  type: (struct_specifier
    name: (type_identifier) "Point"
    body: (field_declaration_list ...))
  declarator: (type_identifier) "Point")
```

The symbol name is taken from the **`declarator`** child (the typedef alias), not the inner struct name.

### 2.2 Function prototype (declaration with function_declarator)

```
(declaration
  type: (primitive_type) "int"
  declarator: (function_declarator
    declarator: (identifier) "add"
    parameters: (parameter_list ...)))
```

No `compound_statement` child → this is a prototype, not a definition.

### 2.3 enum_specifier

```
(enum_specifier
  name: (type_identifier) "Color"
  body: (enumerator_list ...))
```

### 2.4 preproc_ifdef / preproc_if wrapper

```
(preproc_ifdef
  name: (identifier) "MYHEADER_H"
  ...children including type_definition, declaration, etc...)
```

---

## 3. Implementation Plan

### 3.1 LanguageNodeMap changes (line 102–107)

Add `"struct_specifier"` and `"enum_specifier"` to C `class_nodes`:

```python
"c": LanguageNodeMap(
    class_nodes=["struct_specifier", "enum_specifier"],
    function_nodes=["function_definition"],
    import_nodes=["preproc_include"],
    body_delimiter="{",
),
```

### 3.2 `_walk_classes` additions

After the `decorated_definition` branch, add two new branches before the main `child.type in node_map.class_nodes` check:

**Branch A — type_definition unwrap (C)**:
```
if child.type == "type_definition" and language == "c":
    find inner struct_specifier child
    use typedef declarator child for symbol name
    create L2 chunk using inner struct node range
```

**Branch B — preproc_ifdef/preproc_if recurse (C/C++)**:
```
if child.type in ("preproc_ifdef", "preproc_if") and language in ("c", "cpp"):
    self._walk_classes(child, ...)
```

### 3.3 `_walk_functions` additions

Add two new branches:

**Branch A — declaration with function_declarator (C prototypes)**:
```
if child.type == "declaration" and language == "c":
    search for function_declarator child
    if found and no compound_statement child:
        extract name from function_declarator > identifier
        create L3 chunk with content = declaration text
```

**Branch B — preproc_ifdef/preproc_if recurse (C/C++)**:
```
if child.type in ("preproc_ifdef", "preproc_if") and language in ("c", "cpp"):
    self._walk_functions(child, ...)
```

### 3.4 `extract_file_chunk` additions

For top_level_symbols, handle `type_definition` and `preproc_ifdef`/`preproc_if` children when language == "c".

### 3.5 Helper: `_get_typedef_name`

New module-level helper:

```python
def _get_typedef_name(node: ts.Node) -> str:
    """Get the typedef alias name from a type_definition node."""
    for child in reversed(node.children):
        if child.type == "type_identifier":
            return child.text.decode("utf-8") if child.text else ""
    return ""
```

---

## 4. Test Inventory (TDD)

| Test ID | Description | Expected |
|---------|-------------|----------|
| T38-01 | typedef struct → L2 chunk | symbol='Point', chunk_type='class' |
| T38-02 | enum_specifier → L2 chunk | symbol='Color', chunk_type='class' |
| T38-03 | 5 function prototypes in .h file → 5 L3 chunks | chunk_type='function' for each |
| T38-04 | typedef struct inside #ifndef guard | L2 chunk detected |
| T38-05 | function prototypes inside #ifndef guard | L3 chunks detected |
| T38-06 | typedef struct + enum + protos combined | all detected |
| T38-07 | function_definition still produces L3 chunk | not broken |
| T38-08 | typedef struct symbol uses typedef alias not struct tag | symbol='MyPoint' not 'Point' |

---

## 5. Acceptance Criteria Mapping

| Verification Step | Test |
|-------------------|------|
| typedef struct { int x; } Point → L2 symbol='Point' | T38-01 |
| 5 prototype declarations → 5 L3 chunks | T38-03 |
| enum Color { RED, GREEN, BLUE } → L2 symbol='Color' | T38-02 |
| typedef + protos inside #ifndef → all detected | T38-04, T38-05 |

---

## 6. Files Changed

- `src/indexing/chunker.py` — primary implementation
- `tests/test_feature_38_c_chunks.py` — new test file
- `docs/plans/2026-03-22-c-typedef-prototype-enum.md` — this document
