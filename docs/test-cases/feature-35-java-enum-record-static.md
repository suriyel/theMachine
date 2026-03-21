# 测试用例集: Java: enum + record + static initializer

**Feature ID**: 35
**关联需求**: FR-004 (Wave 2)
**日期**: 2026-03-21
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 3 |
| boundary | 4 |
| **合计** | **7** |

---

### 用例编号

ST-FUNC-035-001

### 关联需求

FR-004（Code Chunking — enum declaration produces L2 with methods as L3）

### 测试目标

Verify that a Java enum declaration with constants and methods produces an L2 class chunk and L3 method chunks with correct parent_class.

### 前置条件

- Chunker initialized with Java tree-sitter grammar

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create Java file with enum Color containing RED/GREEN/BLUE constants and display() method | File created |
| 2 | Run chunker.chunk() | Chunks produced |
| 3 | Filter for class chunks | 1 L2 chunk with symbol="Color" |
| 4 | Filter for function chunks with symbol "display" | 1 L3 chunk with parent_class="Color" |

### 验证点

- Enum produces L2 chunk with symbol="Color"
- Method inside enum produces L3 with parent_class="Color"

### 后置检查

- None required

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_feature_35::TestEnumDeclaration::test_enum_produces_l2_chunk, test_enum_method_produces_l3_with_parent
- **Test Type**: Real

---

### 用例编号

ST-FUNC-035-002

### 关联需求

FR-004（Code Chunking — record declaration produces L2 chunk）

### 测试目标

Verify that a Java record declaration produces an L2 chunk and its methods produce L3 chunks.

### 前置条件

- Chunker initialized with Java tree-sitter grammar

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create Java file with record Point(int x, int y) containing distance() method | File created |
| 2 | Run chunker.chunk() | Chunks produced |
| 3 | Filter for class chunks | 1 L2 chunk with symbol="Point" |
| 4 | Filter for function chunks | 1 L3 chunk "distance" with parent_class="Point" |

### 验证点

- Record produces L2 with symbol="Point"
- Record method produces L3 with correct parent_class

### 后置检查

- None required

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_feature_35::TestRecordDeclaration::test_record_produces_l2_chunk, test_record_method_produces_l3
- **Test Type**: Real

---

### 用例编号

ST-FUNC-035-003

### 关联需求

FR-004（Code Chunking — static initializer produces L3 chunk）

### 测试目标

Verify that a Java static initializer block produces an L3 function chunk with symbol="<static>" and correct parent_class.

### 前置条件

- Chunker initialized with Java tree-sitter grammar

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create Java file with class AppConfig containing static {} block and run() method | File created |
| 2 | Run chunker.chunk() | Chunks produced |
| 3 | Filter for function chunks with symbol "<static>" | 1 L3 chunk with parent_class="AppConfig" |
| 4 | Check content | Contains "defaults.put" |

### 验证点

- Static initializer produces L3 with symbol="<static>"
- parent_class correctly set to enclosing class
- Content includes block body

### 后置检查

- None required

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_feature_35::TestStaticInitializer::test_static_initializer_produces_l3, test_static_initializer_content
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-035-001

### 关联需求

FR-004（Boundary — enum without methods）

### 测试目标

Verify that an enum without methods produces only an L2 chunk, no L3.

### 前置条件

- Chunker initialized

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create Java file with enum Direction { NORTH, SOUTH, EAST, WEST } | File created |
| 2 | Run chunker.chunk() | L2 chunk for Direction, 0 L3 chunks |

### 验证点

- L2 chunk with symbol="Direction" produced
- No function chunks produced

### 后置检查

- None required

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_feature_35::TestBoundaryEdgeCases::test_enum_without_methods_l2_only
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-035-002

### 关联需求

FR-004（Boundary — record without methods）

### 测试目标

Verify that a record without methods produces an L2 chunk only.

### 前置条件

- Chunker initialized

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create Java file with record Config(String host, int port) {} | File created |
| 2 | Run chunker.chunk() | L2 chunk for Config |

### 验证点

- L2 chunk with symbol="Config" produced

### 后置检查

- None required

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_feature_35::TestBoundaryEdgeCases::test_record_without_methods_l2_only
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-035-003

### 关联需求

FR-004（Boundary — no regression on plain Java）

### 测试目标

Verify plain Java classes still produce correct chunks (no regression).

### 前置条件

- Chunker initialized

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create Java file with class Service { start(), stop() } | File created |
| 2 | Run chunker.chunk() | 1 L2 + 2 L3 chunks |

### 验证点

- L2 with symbol="Service", L3 with symbols "start" and "stop"

### 后置检查

- None required

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_feature_35::TestBoundaryEdgeCases::test_plain_java_no_regression
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-035-004

### 关联需求

FR-004（Boundary — enum with constructor）

### 测试目标

Verify enum with constructor and method produces L2 + multiple L3 chunks.

### 前置条件

- Chunker initialized

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create Java file with enum Planet with constructor and surfaceGravity() | File created |
| 2 | Run chunker.chunk() | L2 for Planet, L3 for constructor + method |

### 验证点

- L2 with symbol="Planet"
- L3 for "Planet" (constructor) and "surfaceGravity" with parent_class="Planet"

### 后置检查

- None required

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_feature_35::TestBoundaryEdgeCases::test_enum_with_constructor_and_method
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-035-001 | FR-004 | VS-1: enum → L2 + method → L3 | test_enum_produces_l2/test_enum_method | Real | PASS |
| ST-FUNC-035-002 | FR-004 | VS-2: record → L2 | test_record_produces_l2/test_record_method | Real | PASS |
| ST-FUNC-035-003 | FR-004 | VS-3: static init → L3 with parent_class | test_static_initializer | Real | PASS |
| ST-BNDRY-035-001 | FR-004 | VS-1 (boundary) | test_enum_without_methods | Real | PASS |
| ST-BNDRY-035-002 | FR-004 | VS-2 (boundary) | test_record_without_methods | Real | PASS |
| ST-BNDRY-035-003 | FR-004 | (regression) | test_plain_java_no_regression | Real | PASS |
| ST-BNDRY-035-004 | FR-004 | VS-1 (boundary) | test_enum_with_constructor | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 7 |
| Passed | 7 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
