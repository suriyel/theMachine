# 测试用例集: C: typedef struct + function prototypes + enum

**Feature ID**: 38
**关联需求**: FR-004 (Code Chunking — Wave 2, C language support)
**日期**: 2026-03-22
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 4 |
| boundary | 2 |
| **合计** | **6** |

---

### 用例编号

ST-FUNC-038-001

### 关联需求

FR-004（Code Chunking — C typedef struct）

### 测试目标

验证 C 文件中的 `typedef struct { ... } Name;` 模式产生 L2 chunk，symbol 为 typedef 名。

### 前置条件

- tree-sitter C grammar 已安装
- Chunker 实例已创建

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 解析包含 `typedef struct { int x; int y; } Point;` 的 C 文件 | tree-sitter 成功解析 |
| 2 | 调用 extract_class_chunks() | 返回至少 1 个 chunk |
| 3 | 检查 chunk 属性 | chunk_type == "class", symbol == "Point" |

### 验证点

- L2 chunk 的 symbol 为 typedef 别名 "Point"，而非 struct 标签
- chunk_type 为 "class"

### 后置检查

- 无状态变更

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_feature_38_c_chunks.py::TestTypedefStruct::test_typedef_struct_produces_l2_chunk
- **Test Type**: Real

---

### 用例编号

ST-FUNC-038-002

### 关联需求

FR-004（Code Chunking — C function prototypes）

### 测试目标

验证 C 头文件中的函数原型声明（无函数体）产生 L3 chunk。

### 前置条件

- tree-sitter C grammar 已安装
- C 头文件包含 5 个函数原型

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 解析包含 5 个函数原型的 C 头文件 | tree-sitter 成功解析 |
| 2 | 调用 extract_function_chunks() | 返回恰好 5 个 chunk |
| 3 | 检查每个 chunk 内容 | 每个 chunk 的 content 等于声明文本 |

### 验证点

- 恰好 5 个 L3 function chunk
- 每个 chunk 的 content 包含完整函数声明（含分号）

### 后置检查

- 无状态变更

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_feature_38_c_chunks.py::TestFunctionPrototypes::test_five_prototypes_produce_five_l3_chunks
- **Test Type**: Real

---

### 用例编号

ST-FUNC-038-003

### 关联需求

FR-004（Code Chunking — C enum）

### 测试目标

验证 C 文件中的 `enum Color { RED, GREEN, BLUE };` 产生 L2 chunk。

### 前置条件

- tree-sitter C grammar 已安装

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 解析包含 `enum Color { RED, GREEN, BLUE };` 的 C 文件 | tree-sitter 成功解析 |
| 2 | 调用 extract_class_chunks() | 返回至少 1 个 chunk |
| 3 | 检查 chunk 属性 | chunk_type == "class", symbol == "Color" |

### 验证点

- L2 chunk 的 symbol 为 "Color"
- chunk_type 为 "class"

### 后置检查

- 无状态变更

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_feature_38_c_chunks.py::TestEnumChunks::test_enum_produces_l2_chunk
- **Test Type**: Real

---

### 用例编号

ST-FUNC-038-004

### 关联需求

FR-004（Code Chunking — preproc guard handling）

### 测试目标

验证 `#ifndef` guard 包裹的 typedef struct 和函数原型仍被正确检测。

### 前置条件

- tree-sitter C grammar 已安装
- C 头文件结构为 `#ifndef HEADER_H` ... `#endif`

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 解析包含 #ifndef 保护的头文件（含 typedef struct 和原型） | tree-sitter 成功解析 |
| 2 | 调用 extract_class_chunks() | 检测到 typedef struct chunk |
| 3 | 调用 extract_function_chunks() | 检测到函数原型 chunk |

### 验证点

- preproc_ifdef 不阻止 typedef struct 的检测
- preproc_ifdef 不阻止函数原型的检测

### 后置检查

- 无状态变更

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_feature_38_c_chunks.py::TestPreprocGuards::test_typedef_inside_ifndef_produces_l2_chunk
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-038-001

### 关联需求

FR-004（Code Chunking — boundary: anonymous struct）

### 测试目标

验证匿名 typedef struct（无标签）仍产生 L2 chunk。

### 前置条件

- tree-sitter C grammar 已安装

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 解析 `typedef struct { int val; } Anon;` | tree-sitter 成功解析 |
| 2 | 调用 extract_class_chunks() | 返回 L2 chunk |
| 3 | 检查 symbol | symbol == "Anon"（typedef 别名，非 struct 标签） |

### 验证点

- 匿名 struct 通过 typedef 名正确命名

### 后置检查

- 无状态变更

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_feature_38_c_chunks.py::TestTypedefStruct::test_typedef_struct_symbol_is_typedef_name
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-038-002

### 关联需求

FR-004（Code Chunking — boundary: prototype vs definition）

### 测试目标

验证函数定义（有函数体）不被误识别为函数原型。

### 前置条件

- tree-sitter C grammar 已安装
- C 文件同时包含函数定义和函数原型

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 解析包含函数定义和原型的 C 文件 | tree-sitter 成功解析 |
| 2 | 调用 extract_function_chunks() | 原型产生 L3 chunk |
| 3 | 检查非原型函数 | 函数定义也产生 L3 chunk（通过 function_nodes） |

### 验证点

- 函数定义和函数原型分别产生独立的 L3 chunk
- 两者不冲突或重复

### 后置检查

- 无状态变更

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_feature_38_c_chunks.py::TestFunctionPrototypes::test_prototype_not_confused_with_definition
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-038-001 | FR-004 | VS-1: typedef struct L2 chunk with symbol='Point' | test_typedef_struct_produces_l2_chunk | Real | PASS |
| ST-FUNC-038-002 | FR-004 | VS-2: 5 prototype L3 chunks | test_five_prototypes_produce_five_l3_chunks | Real | PASS |
| ST-FUNC-038-003 | FR-004 | VS-3: enum L2 chunk with symbol='Color' | test_enum_produces_l2_chunk | Real | PASS |
| ST-FUNC-038-004 | FR-004 | VS-4: #ifndef guard handling | test_typedef_inside_ifndef_produces_l2_chunk | Real | PASS |
| ST-BNDRY-038-001 | FR-004 | VS-1 (boundary: anonymous struct) | test_typedef_struct_symbol_is_typedef_name | Real | PASS |
| ST-BNDRY-038-002 | FR-004 | VS-2 (boundary: prototype vs definition) | test_prototype_not_confused_with_definition | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 6 |
| Passed | 6 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
