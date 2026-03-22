# Feature #37 — TypeScript: enum + namespace + decorator unwrapping — Detailed Design

**Date**: 2026-03-21
**Feature ID**: 37
**Feature Title**: TypeScript: enum + namespace + decorator unwrapping
**SRS Ref**: FR-004 (Wave 2, acceptance criteria for TS enum L2, namespace unwrapping, decorator unwrapping)
**Design Ref**: §4.1.4, TypeScript node mappings, AST wrapper node unwrapping rules

---

## 1. Overview

The current TypeScript `LanguageNodeMap` recognizes `class_declaration` and `interface_declaration` as class nodes. Three patterns are NOT supported:

- **Enum declarations** (`enum_declaration`) — no L2 chunk produced.
- **Namespace/module blocks** (`internal_module` wrapped in `expression_statement`) — classes and functions inside namespaces are invisible.
- **Decorator-wrapped classes** — in TypeScript, decorators are children of the `class_declaration` node itself (unlike Python where they create a `decorated_definition` wrapper). Testing confirms decorators already work with existing code. This is a verification task, not an implementation task.

This feature:

1. Adds `enum_declaration` to TypeScript `class_nodes` → produces L2 chunks.
2. Adds namespace unwrapping: when `expression_statement` contains `internal_module`, recurse into its `statement_block` body for class/function detection.
3. Verifies decorator support already works (no code change needed).

**Scope**: TypeScript only. No other languages are affected.

### Tree-sitter AST findings

| Construct | Top-level node | Key child | Body node |
|-----------|---------------|-----------|-----------|
| `enum Color { ... }` | `enum_declaration` | `identifier` (name), `enum_body` | `enum_body` (contains `property_identifier` members) |
| `namespace Foo { ... }` | `expression_statement` → `internal_module` | `identifier` (name), `statement_block` (body) | `statement_block` |
| Nested namespace | `expression_statement` → `internal_module` (inside parent's `statement_block`) | Same structure, recursive | `statement_block` |
| `@Component class Foo {}` | `class_declaration` (decorator is a child, not a wrapper) | `decorator` child, `type_identifier` (name) | `class_body` |

---

## 2. Component Data-Flow Diagram

N/A — single-class feature. Modifications to `LANGUAGE_NODE_MAPS` configuration and walker methods in existing `Chunker` module.

---

## 3. Interface Contract

| Method / Config | Signature | Preconditions | Postconditions | Raises |
|-----------------|-----------|---------------|----------------|--------|
| `LANGUAGE_NODE_MAPS["typescript"]` | `LanguageNodeMap(...)` | N/A | `class_nodes` includes `enum_declaration` | N/A |
| `Chunker._walk_classes` | (unchanged) | `language == "typescript"`, child is `expression_statement` containing `internal_module` | Recurses into namespace `statement_block` to find class nodes | (no new exceptions) |
| `Chunker._walk_functions` | (unchanged) | `language == "typescript"`, child is `expression_statement` containing `internal_module` | Recurses into namespace `statement_block` to find function nodes | (no new exceptions) |

**VS traceability**:
- VS-1 ("enum → L2 chunk") → `class_nodes` config change
- VS-2 ("namespace Foo { class Bar {} } → L2 + L3") → `_walk_classes` + `_walk_functions` namespace unwrapping
- VS-3 ("nested namespace → L2 for class C") → recursive namespace unwrapping
- VS-4 ("@Component class → L2 with correct symbol") → already working, verification only

---

## 4. Internal Sequence Diagram

N/A — configuration-driven + walker extension. The namespace unwrapping follows the same pattern as `export_statement` unwrapping.

---

## 5. Algorithm / Core Logic

### 5a. Enum support

Config change only — add `"enum_declaration"` to `LANGUAGE_NODE_MAPS["typescript"].class_nodes`. The existing `_walk_classes` loop will automatically pick it up. `_get_body_node` already handles `enum_body` (from Java feature #35).

### 5b. Namespace unwrapping

```
// In _walk_classes/_walk_functions, for each child:
IF child.type == "expression_statement":
  FOR sub IN child.children:
    IF sub.type == "internal_module":
      // Find statement_block body
      FOR body_child IN sub.children:
        IF body_child.type == "statement_block":
          // Recurse into statement_block to find classes/functions
          _walk_classes/functions(body_child, ...)
          BREAK
```

### 5c. Boundary decisions

| Parameter | Min | Max | Empty/Null | At boundary |
|-----------|-----|-----|------------|-------------|
| Namespace nesting depth | 1 | unbounded (recursive) | Empty namespace → no chunks | Single class in deep chain still found |
| Enum members | 0 | many | Empty enum → L2 chunk with no methods | Works as class chunk |

### 5d. Error handling

| Condition | Detection | Response | Recovery |
|-----------|-----------|----------|----------|
| expression_statement has no internal_module | Loop doesn't match | Skip, continue walking | Normal flow |
| internal_module has no statement_block | Inner loop doesn't match | Skip, no recursion | Normal flow |
| Decorator on non-class node | Existing code handles | Class detection still works | TS decorator is a child, not wrapper |

---

## 6. State Diagram

N/A — stateless feature.

---

## 7. Test Inventory

| ID | Category | Traces To | Input / Setup | Expected | Kills Which Bug? |
|----|----------|-----------|---------------|----------|-----------------|
| T01 | happy path | VS-1 | TS file: `enum Color { Red, Green, Blue }` | L2 chunk with symbol='Color' | Missing enum in class_nodes |
| T02 | happy path | VS-2 | TS file: `namespace Foo { class Bar { method() {} } }` | L2 chunk symbol='Bar', L3 chunk symbol='method' | Missing namespace unwrapping |
| T03 | happy path | VS-3 | TS file: `namespace A { namespace B { class C {} } }` | L2 chunk symbol='C' | Non-recursive namespace walk |
| T04 | happy path | VS-4 | TS file: `@Component class AppComponent { render() {} }` | L2 chunk symbol='AppComponent', L3 chunk symbol='render' | Decorator breaks TS class detection |
| T05 | boundary | §5c | TS file: empty namespace `namespace Empty {}` | No L2/L3 chunks from namespace | Crash on empty namespace |
| T06 | boundary | §5c | TS file: enum + class + namespace coexist | All produce correct chunks | Enum/namespace detection breaks existing class/function detection |
| T07 | boundary | §5c | TS file: namespace with functions (no class) | L3 function chunks produced | Namespace unwrapping only checks classes |
| T08 | boundary | §5c | TS file: exported namespace `export namespace Foo { class Bar {} }` | L2 chunk for Bar | Export wrapping hides namespace |
| T09 | boundary | §5b | TS file: normal TS file with no namespaces/enums | Unchanged behavior, same as before | Namespace detection breaks normal flow |

Negative tests: T05, T06, T07, T08, T09 = 5/9 = 56% >= 40%

---

## 8. TDD Task Decomposition

### Task 1: Write failing tests
**Files**: `tests/test_chunker.py`

### Task 2: Implement
**Files**: `src/indexing/chunker.py`
1. Add `enum_declaration` to `LANGUAGE_NODE_MAPS["typescript"].class_nodes`
2. Add namespace unwrapping in `_walk_classes` and `_walk_functions`

### Task 3-5: Coverage, Refactor, Mutation Gates
