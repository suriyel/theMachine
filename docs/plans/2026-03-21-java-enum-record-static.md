# Feature #35 — Java: enum + record + static initializer — Detailed Design

**Date**: 2026-03-21
**Feature ID**: 35
**Feature Title**: Java: enum + record + static initializer
**SRS Ref**: FR-004 (Wave 2, acceptance criteria for enum/record L2 chunks and static initializer L3 chunk)
**Design Ref**: §4.1.4, Java node mappings

---

## 1. Overview

The current Java `LanguageNodeMap` only recognises `class_declaration` and `interface_declaration` as class nodes and `method_declaration` / `constructor_declaration` as function nodes. This means:

- **Enum declarations** (`enum_declaration`) are invisible — no L2 chunk is produced, and methods inside the enum body are never walked.
- **Record declarations** (`record_declaration`, Java 16+) are likewise invisible.
- **Static initializer blocks** (`static_initializer`) are never chunked — they contain real logic (e.g. cache loading, registry wiring) that should be retrievable.

This feature extends the Java node map and supporting helpers so that:

1. `enum_declaration` and `record_declaration` produce L2 class chunks.
2. Methods inside enum/record bodies produce L3 function chunks.
3. `static_initializer` produces an L3 function chunk with the synthetic symbol `<static>`.

**Scope**: Java only. No other languages are affected.

### Tree-sitter AST findings

| Construct | Node type | Body child | Notes |
|-----------|-----------|------------|-------|
| `enum` | `enum_declaration` | `enum_body` (NOT `class_body`) | Methods live inside an `enum_body_declarations` node within `enum_body` |
| `record` | `record_declaration` | `class_body` | Already handled by `_get_body_node` |
| `static { ... }` | `static_initializer` | `block` | Direct child of `class_body`; has no `identifier` child |

---

## 2. Component Data-Flow Diagram

N/A — single-class feature. The change modifies configuration (`LANGUAGE_NODE_MAPS`), one helper function (`_get_body_node`), and one helper function (`_get_node_name`) in the existing `Chunker` module. No new classes or components are introduced.

---

## 3. Interface Contract

No new public methods are added. Existing methods gain new behavior for Java enum/record/static initializer nodes:

| Method / Config | Signature | Preconditions | Postconditions | Raises |
|-----------------|-----------|---------------|----------------|--------|
| `LANGUAGE_NODE_MAPS["java"]` | `LanguageNodeMap(...)` | N/A | `class_nodes` includes `enum_declaration`, `record_declaration`; `function_nodes` includes `static_initializer` | N/A |
| `_get_body_node` | `(node, language) -> Node \| None` | `node.type == "enum_declaration"`, `language == "java"` | Returns `enum_body` child (or walks into `enum_body_declarations` for method discovery) | (no new exceptions) |
| `_get_node_name` | `(node) -> str` | `node.type == "static_initializer"` | Returns `"<static>"` | (no new exceptions) |
| `Chunker._walk_classes` | (unchanged signature) | `language == "java"` | When child is `enum_declaration`, an L2 chunk is appended with `symbol` = enum name; when child is `record_declaration`, an L2 chunk is appended with `symbol` = record name | (no new exceptions) |
| `Chunker._walk_functions` | (unchanged signature) | `language == "java"` | When child is `static_initializer` inside a class body, an L3 chunk is appended with `symbol` = `"<static>"` and `parent_class` = enclosing class name | (no new exceptions) |

**Verification step traceability**:
- VS-1 ("enum with constants and method → L2 + L3") → `_walk_classes` + `_walk_functions` postconditions
- VS-2 ("record declaration → L2 chunk") → `_walk_classes` postcondition
- VS-3 ("static initializer → L3 with parent_class") → `_walk_functions` postcondition

---

## 4. Internal Sequence Diagram

N/A — the changes are configuration-driven. Adding node types to the map causes the existing `_walk_classes` and `_walk_functions` loops to pick them up automatically. The only non-trivial logic is in `_get_body_node` (new body types) and `_get_node_name` (static initializer special case). Error paths documented in Algorithm §5.

---

## 5. Algorithm / Core Logic

### 5a. Configuration change

```python
"java": LanguageNodeMap(
    class_nodes=["class_declaration", "interface_declaration",
                 "enum_declaration", "record_declaration"],
    function_nodes=["method_declaration", "constructor_declaration",
                    "static_initializer"],
    import_nodes=["import_declaration"],
    body_delimiter="{",
),
```

### 5b. `_get_body_node` extension

The existing C-family branch checks for `class_body`, `interface_body`, `block`, etc. We add `enum_body` and `enum_body_declarations` to the set:

```
FUNCTION _get_body_node(node, language) -> Node | None
  IF language == "python":
    ... (existing)
  ELSE:
    FOR child in node.children:
      IF child.type in ("class_body", "interface_body", "block",
                         "field_declaration_list", "declaration_list",
                         "enum_body", "enum_body_declarations"):
        RETURN child
  RETURN None
END
```

**Why `enum_body_declarations`?** In the tree-sitter Java grammar, an `enum_body` contains enum constants followed by an optional `enum_body_declarations` node (delimited by `;`). The `enum_body_declarations` node contains the actual method/constructor declarations. When `_walk_functions` recurses into the body of an `enum_declaration`, it calls `_get_body_node` on the enum. This returns `enum_body`. Then when iterating `enum_body.children`, the walker encounters `enum_body_declarations` — but methods are children of that node, not direct children of `enum_body`. So the walker must also recurse into `enum_body_declarations`. By adding `enum_body_declarations` to the body types, `_get_body_node` can be called again on `enum_body` children to descend into the declarations block.

However, a simpler approach: when `_walk_functions` iterates `enum_body.children` and finds an `enum_body_declarations` node, it does not match any class/function node type, so methods inside it would be missed. The fix is to treat `enum_body_declarations` as a body-like container that `_walk_functions` should recurse into. We handle this by adding a check: if a child's type is `enum_body_declarations`, recurse `_walk_functions` into it with the same `parent_class`.

```
# In _walk_functions, after existing checks:
ELIF child.type == "enum_body_declarations":
    _walk_functions(child, ..., parent_class=parent_class)
```

Similarly, for `_walk_classes` to collect method signatures from enum bodies, the method-signature-collection loop must descend into `enum_body_declarations`.

### 5c. `_get_node_name` extension for `static_initializer`

```
FUNCTION _get_node_name(node) -> str
  IF node.type == "static_initializer":
    RETURN "<static>"
  // ... existing logic (identifier, property_identifier, etc.)
END
```

The check is placed at the top of `_get_node_name` because `static_initializer` nodes have no `identifier` child — the existing passes would all return `""`.

### 5d. `_walk_classes` — enum method signature collection

When collecting method signatures for the L2 class chunk content, the existing loop iterates `body.children` looking for `function_nodes`. For enums, the body is `enum_body`, whose children include `enum_constant` nodes and an `enum_body_declarations` node. Methods are inside `enum_body_declarations`, not directly in `enum_body`. So the method-signature collection must also look inside `enum_body_declarations`:

```
body = _get_body_node(child, language)
IF body:
  FOR member in body.children:
    IF member.type in node_map.function_nodes:
      // collect signature (existing)
    ELIF member.type == "enum_body_declarations":
      FOR inner_member in member.children:
        IF inner_member.type in node_map.function_nodes:
          // collect signature
```

### 5e. Boundary decisions table

| Parameter | Min | Max | Empty/Null | At boundary |
|-----------|-----|-----|------------|-------------|
| Enum constants | 0 | Many | Empty enum body → L2 chunk, no L3 | Enum with 0 methods → L2 only |
| Enum methods | 0 | Many | No methods → no L3 chunks | Enum with 1 method → 1 L3 with parent_class = enum name |
| Record components | 0 | Many | `record R()` → L2 chunk | Record with no methods → L2 only |
| Static initializer count | 0 | Multiple per class | No static blocks → no change | Multiple static blocks → each produces an L3 chunk |
| Static initializer name | Always `<static>` | N/A | N/A | Symbol is synthetic; never empty |

### 5f. Error handling table

| Condition | Detection | Response | Recovery |
|-----------|-----------|----------|----------|
| `enum_declaration` with no `enum_body` | `_get_body_node` returns None | L2 chunk created with no method signatures; no L3 recurse | No action needed |
| `record_declaration` with no `class_body` | `_get_body_node` returns None | Same as above | No action needed |
| `static_initializer` with no `block` child | `_get_node_name` still returns `<static>`; chunk content = node text | L3 chunk created with whatever text is present | No action needed |
| `enum_body_declarations` absent (enum with no methods after `;`) | `_walk_functions` iterates `enum_body` children, finds no `enum_body_declarations` | No L3 chunks produced, no error | Expected behavior |

---

## 6. State Diagram

N/A — stateless feature. The chunker is a pure function (input: AST node -> output: chunks). No object lifecycle.

---

## 7. Test Inventory

| ID | Category | Traces To | Input / Setup | Expected | Kills Which Bug? |
|----|----------|-----------|---------------|----------|-----------------|
| T1 | happy path | VS-1 | Java file: `public enum Color { RED, GREEN; public String label() { return name().toLowerCase(); } }` | L2 chunk with symbol="Color"; L3 chunk with symbol="label", parent_class="Color" | Enum not producing L2; enum methods not producing L3 |
| T2 | happy path | VS-2 | Java file: `public record Point(int x, int y) { public double distance() { return Math.sqrt(x*x + y*y); } }` | L2 chunk with symbol="Point"; L3 chunk with symbol="distance", parent_class="Point" | Record not producing L2 |
| T3 | happy path | VS-3 | Java file: `public class Registry { static { init(); } }` | L3 chunk with symbol="<static>", parent_class="Registry" | Static initializer not producing L3 |
| T4 | boundary | VS-1 | Java file: `public enum Empty { A, B, C }` (no methods) | L2 chunk with symbol="Empty"; no L3 chunks | Enum without methods should not crash or produce spurious L3 |
| T5 | boundary | VS-2 | Java file: `public record Pair(String a, String b) {}` (no methods) | L2 chunk with symbol="Pair"; no L3 chunks | Record without methods should not produce L3 |
| T6 | boundary | regression | Java file: `public class Foo { public void bar() {} }` (plain class) | L2 chunk with symbol="Foo"; L3 chunk with symbol="bar" — same as before | Adding enum/record/static must not regress plain class handling |
| T7 | boundary | §5c | Java file with `static_initializer` | L3 chunk symbol = "<static>" (not empty string) | `_get_node_name` returns "" for static_initializer |

**Negative ratio**: T4, T5, T6, T7 = 4 boundary out of 7 total = 57%. Exceeds 40% threshold.

---

## 8. TDD Task Decomposition

### Task 1: Write failing tests
**Files**: `tests/test_feature_35_java_enum_record_static.py`
**Steps**:
1. Create test file with imports: `Chunker`, `ExtractedFile`, helper `_make_file`
2. Write tests for each row in Test Inventory (§7):
   - T1: `test_enum_with_method_produces_l2_and_l3`
   - T2: `test_record_with_method_produces_l2_and_l3`
   - T3: `test_static_initializer_produces_l3_with_parent_class`
   - T4: `test_enum_without_methods_produces_l2_only`
   - T5: `test_record_without_methods_produces_l2_only`
   - T6: `test_plain_class_no_regression`
   - T7: `test_static_initializer_symbol_is_angle_bracket_static`
3. Run: `pytest tests/test_feature_35_java_enum_record_static.py -v`
4. **Expected**: T1-T5, T7 FAIL (enum/record/static not yet handled). T6 should PASS (existing behavior).

### Task 2: Implement minimal code
**Files**: `src/indexing/chunker.py`
**Steps**:
1. Add `"enum_declaration"`, `"record_declaration"` to `LANGUAGE_NODE_MAPS["java"].class_nodes`
2. Add `"static_initializer"` to `LANGUAGE_NODE_MAPS["java"].function_nodes`
3. Add `"enum_body"`, `"enum_body_declarations"` to the body-type set in `_get_body_node` C-family branch
4. Add `static_initializer` check at top of `_get_node_name` returning `"<static>"`
5. Add `enum_body_declarations` recurse in `_walk_functions` (when `child.type == "enum_body_declarations"`, recurse with same `parent_class`)
6. Extend method-signature collection loop in `_walk_classes` to descend into `enum_body_declarations`
7. Run: `pytest tests/test_feature_35_java_enum_record_static.py -v`
8. **Expected**: All tests PASS

### Task 3: Coverage Gate
1. Run: `pytest --cov=src --cov-branch --cov-report=term-missing tests/`
2. Check thresholds: line >= 90%, branch >= 80%
3. If below: add tests for uncovered lines/branches

### Task 4: Refactor
1. Review changes for DRY — ensure `enum_body_declarations` handling is consistent between `_walk_classes` and `_walk_functions`
2. Run full test suite: `pytest tests/ -v`
3. All tests PASS

### Task 5: Mutation Gate
1. Run: `mutmut run --paths-to-mutate=src/indexing/chunker.py`
2. Check threshold: mutation score >= 80%
3. If below: strengthen assertions (specific symbol names, parent_class values, chunk counts)

---

## Verification Checklist

- [x] All verification_steps traced to Interface Contract postconditions (VS-1->_walk_classes+_walk_functions, VS-2->_walk_classes, VS-3->_walk_functions)
- [x] All verification_steps traced to Test Inventory rows (VS-1->T1, VS-2->T2, VS-3->T3)
- [x] Algorithm pseudocode covers all non-trivial methods (config change, _get_body_node extension, _get_node_name extension, _walk_functions enum_body_declarations recurse, _walk_classes method-sig collection)
- [x] Boundary table covers all algorithm parameters (enum constants, enum methods, record components, static initializer count, static initializer name)
- [x] Error handling table covers all edge cases (no body, no block, no enum_body_declarations)
- [x] Test Inventory negative ratio >= 40% (4/7 boundary = 57%)
- [x] Every skipped section has explicit "N/A — [reason]"
