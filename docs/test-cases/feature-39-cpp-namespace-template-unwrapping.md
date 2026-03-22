# 测试用例集: C++: namespace + template unwrapping

**Feature ID**: 39
**关联需求**: FR-004（Code Chunking）
**日期**: 2026-03-22
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 3 |
| boundary | 2 |
| **合计** | **5** |

---

### 用例编号

ST-FUNC-039-001

### 关联需求

FR-004（Code Chunking — C++ namespace unwrapping）

### 测试目标

验证 C++ namespace 内的 class 和 method 被正确拆分为 L2 和 L3 chunks

### 前置条件

- Chunker 实例已创建
- tree-sitter-cpp 语法已安装

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 C++ 文件内容: `namespace foo { class Bar { public: void method() {} }; }` | 文件内容已准备 |
| 2 | 调用 `chunker.chunk(file, repo_id, branch)` | 返回 chunks 列表 |
| 3 | 检查 L2 chunks | 存在 symbol="Bar", chunk_type="class" 的 chunk |
| 4 | 检查 L3 chunks | 存在 symbol="method", chunk_type="function", parent_class="Bar" 的 chunk |
| 5 | 检查总数 | 共 3 chunks: 1 L1 file + 1 L2 class + 1 L3 function |

### 验证点

- Bar 作为 L2 class chunk 存在
- method 作为 L3 function chunk 存在，parent_class="Bar"
- 总 chunk 数为 3

### 后置检查

- 无（纯计算，无副作用）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_chunker.py::TestFeature39CppNamespaceUnwrap::test_namespace_class_method, tests/test_chunker.py::TestFeature39CppNamespaceUnwrap::test_namespace_chunk_count
- **Test Type**: Real

---

### 用例编号

ST-FUNC-039-002

### 关联需求

FR-004（Code Chunking — C++ nested namespace unwrapping）

### 测试目标

验证嵌套 namespace 内的函数被正确拆分为 L3 chunks

### 前置条件

- Chunker 实例已创建

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 C++ 文件内容: `namespace a { namespace b { void func() { return; } } }` | 文件内容已准备 |
| 2 | 调用 `chunker.chunk(file, repo_id, branch)` | 返回 chunks 列表 |
| 3 | 检查 L3 chunks | 存在 symbol="func", chunk_type="function" 的 chunk |

### 验证点

- func 在嵌套 namespace 内被正确发现为 L3 chunk

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_chunker.py::TestFeature39CppNamespaceUnwrap::test_nested_namespace_function
- **Test Type**: Real

---

### 用例编号

ST-FUNC-039-003

### 关联需求

FR-004（Code Chunking — C++ template unwrapping）

### 测试目标

验证 template class 和 template function 被正确拆分为 L2/L3 chunks

### 前置条件

- Chunker 实例已创建

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 C++ 文件: `template<typename T> class Container { public: void push(T val) {} };` | 文件内容已准备 |
| 2 | 调用 `chunker.chunk(file, repo_id, branch)` | 返回 chunks 列表 |
| 3 | 检查 L2 chunks | 存在 symbol="Container", chunk_type="class" 的 chunk |
| 4 | 检查 L3 chunks | 存在 symbol="push", parent_class="Container" 的 chunk |
| 5 | 创建 C++ 文件: `template<typename T> T max_val(T a, T b) { return a > b ? a : b; }` | 文件内容已准备 |
| 6 | 调用 `chunker.chunk(file, repo_id, branch)` | 返回 chunks 列表 |
| 7 | 检查 L3 chunks | 存在 symbol="max_val", chunk_type="function" 的 chunk |

### 验证点

- Container 作为 L2 class chunk 存在
- push 作为 L3 function chunk 存在，parent_class="Container"
- Container L2 chunk 的 content 包含 "push" 方法签名
- max_val 作为独立的 L3 function chunk 存在

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_chunker.py::TestFeature39CppTemplateUnwrap::test_template_class_method, tests/test_chunker.py::TestFeature39CppTemplateUnwrap::test_template_function, tests/test_chunker.py::TestFeature39CppTemplateUnwrap::test_template_class_method_signatures
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-039-001

### 关联需求

FR-004（Code Chunking — C++ boundary cases）

### 测试目标

验证 C++17 nested namespace specifier、inline namespace、空 namespace 的边界处理

### 前置条件

- Chunker 实例已创建

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 C++ 文件: `namespace a::b::c { class D { public: int value() { return 42; } }; }` | 文件内容已准备 |
| 2 | 调用 `chunker.chunk(file, repo_id, branch)` | D 作为 L2 chunk 存在 |
| 3 | 创建 C++ 文件: `inline namespace v2 { void helper() {} }` | 文件内容已准备 |
| 4 | 调用 `chunker.chunk(file, repo_id, branch)` | helper 作为 L3 chunk 存在 |
| 5 | 创建 C++ 文件: `namespace Empty {}` | 文件内容已准备 |
| 6 | 调用 `chunker.chunk(file, repo_id, branch)` | 仅有 1 个 L1 file chunk，无 L2/L3 |

### 验证点

- C++17 `namespace a::b::c` 正确展开，内部类 D 被发现
- inline namespace 等同于普通 namespace 处理
- 空 namespace 不产生额外 chunks

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_chunker.py::TestFeature39CppNamespaceUnwrap::test_cpp17_nested_namespace, tests/test_chunker.py::TestFeature39CppNamespaceUnwrap::test_inline_namespace, tests/test_chunker.py::TestFeature39CppNamespaceUnwrap::test_empty_namespace
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-039-002

### 关联需求

FR-004（Code Chunking — namespace + template combined）

### 测试目标

验证 namespace 内嵌套 template class 以及 namespace 内独立函数的边界组合

### 前置条件

- Chunker 实例已创建

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 C++ 文件: `namespace ns { template<typename T> class Tmpl { public: void m() {} }; }` | 文件内容已准备 |
| 2 | 调用 `chunker.chunk(file, repo_id, branch)` | 返回 chunks 列表 |
| 3 | 检查 L2 chunks | 存在 symbol="Tmpl" 的 L2 chunk |
| 4 | 检查 L3 chunks | 存在 symbol="m", parent_class="Tmpl" 的 L3 chunk |
| 5 | 创建 C++ 文件: `namespace math { int add(int a, int b) { return a + b; } }` | 文件内容已准备 |
| 6 | 调用 `chunker.chunk(file, repo_id, branch)` | add 作为 L3 chunk 存在 |
| 7 | 检查 L1 file chunk top_level_symbols | 包含来自 namespace 内部的符号 |

### 验证点

- namespace + template 组合正确展开，Tmpl 为 L2，m 为 L3
- namespace 内独立函数 add 被正确发现
- L1 file chunk 的 top_level_symbols 包含 namespace 内部符号

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_chunker.py::TestFeature39CppCombined::test_namespace_template_class, tests/test_chunker.py::TestFeature39CppNamespaceUnwrap::test_namespace_function_only, tests/test_chunker.py::TestFeature39CppNamespaceUnwrap::test_namespace_top_level_symbols
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-039-001 | FR-004 | VS-1: namespace class→L2, method→L3 | test_namespace_class_method, test_namespace_chunk_count | Real | PASS |
| ST-FUNC-039-002 | FR-004 | VS-2: nested namespace→func L3 | test_nested_namespace_function | Real | PASS |
| ST-FUNC-039-003 | FR-004 | VS-3: template class→L2+L3; VS-4: template func→L3 | test_template_class_method, test_template_function, test_template_class_method_signatures | Real | PASS |
| ST-BNDRY-039-001 | FR-004 | VS-1/VS-2 (boundary: C++17, inline, empty) | test_cpp17_nested_namespace, test_inline_namespace, test_empty_namespace | Real | PASS |
| ST-BNDRY-039-002 | FR-004 | VS-1/VS-3 (boundary: ns+template combined, ns+function) | test_namespace_template_class, test_namespace_function_only, test_namespace_top_level_symbols | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 5 |
| Passed | 5 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
