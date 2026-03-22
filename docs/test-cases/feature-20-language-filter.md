# 测试用例集: Language Filter

**Feature ID**: 20
**关联需求**: FR-018
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

ST-FUNC-020-001

### 关联需求

FR-018（Language Filter — 单语言过滤）

### 测试目标

验证当查询指定 language_filter=['java'] 时，LanguageFilter 验证通过并返回归一化后的语言列表，检索仅返回 Java 代码块。

### 前置条件

- LanguageFilter 类已实现并可导入
- QueryHandler 已集成 LanguageFilter

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 LanguageFilter 实例，调用 `validate(["java"])` | 返回 `["java"]` |
| 2 | 创建 LanguageFilter 实例，调用 `validate(["Java"])` | 返回 `["java"]`（大小写归一化） |
| 3 | 构造 QueryHandler（含 LanguageFilter），调用 `handle_nl_query("timeout", languages=["java"])` | Retriever 的 bm25_code_search 和 vector_code_search 接收 `languages=["java"]` |

### 验证点

- validate 对小写输入返回原值
- validate 对混合大小写输入返回小写归一化结果
- QueryHandler 将验证后的语言列表正确传递给 Retriever

### 后置检查

- 无（纯计算，无副作用）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_language_filter.py::test_a1_single_language_java, tests/test_language_filter.py::test_a3_case_normalization_mixed, tests/test_language_filter.py::test_d1_query_handler_passes_languages_to_retriever
- **Test Type**: Real

---

### 用例编号

ST-FUNC-020-002

### 关联需求

FR-018（Language Filter — 多语言过滤）

### 测试目标

验证当查询指定多个语言 ['java', 'python'] 时，LanguageFilter 验证通过并返回完整列表。

### 前置条件

- LanguageFilter 类已实现并可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 `validate(["java", "python"])` | 返回 `["java", "python"]` |
| 2 | 调用 `validate(["java", "python", "typescript", "javascript", "c", "c++"])` | 返回全部 6 种支持的语言 |

### 验证点

- 多语言列表原样返回（均为支持语言）
- 全部 6 种支持语言均可通过验证

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_language_filter.py::test_a2_multiple_languages, tests/test_language_filter.py::test_a6_all_six_supported
- **Test Type**: Real

---

### 用例编号

ST-FUNC-020-003

### 关联需求

FR-018（Language Filter — 不支持的语言拒绝）

### 测试目标

验证当提交不支持的语言（如 'rust'）时，系统抛出 ValidationError 并在错误消息中列出所有支持的语言。

### 前置条件

- LanguageFilter 类已实现并可导入
- 支持的语言集合: java, python, typescript, javascript, c, c++

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 `validate(["rust"])` | 抛出 ValidationError，消息包含 "rust" 和所有支持语言 |
| 2 | 调用 `validate(["java", "rust"])` | 抛出 ValidationError，消息包含 "rust" |
| 3 | 调用 `validate(["go", "rust"])` | 抛出 ValidationError，消息同时包含 "go" 和 "rust" |
| 4 | POST /api/v1/query，body 为 `{"query": "timeout", "languages": ["rust"]}` | 返回 HTTP 400，detail 包含 "rust" |

### 验证点

- 单个不支持语言触发 ValidationError
- 混合有效/无效语言仍触发 ValidationError
- 多个无效语言均列在错误消息中
- HTTP 端点返回 400 状态码

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_language_filter.py::test_b1_unsupported_language_rust, tests/test_language_filter.py::test_b2_mixed_valid_invalid, tests/test_language_filter.py::test_b3_multiple_unsupported, tests/test_language_filter.py::test_d3_endpoint_returns_400_for_unsupported_language
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-020-001

### 关联需求

FR-018（Language Filter — 空列表和 None 输入）

### 测试目标

验证当提交空语言过滤列表 [] 或 None 时，系统不应用任何语言过滤，搜索所有语言。

### 前置条件

- LanguageFilter 类已实现并可导入
- QueryHandler 已集成 LanguageFilter

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 `validate([])` | 返回 None |
| 2 | 调用 `validate(None)` | 返回 None |
| 3 | QueryHandler 调用 `handle_nl_query("timeout", languages=[])` | Retriever 接收 `languages=None`（不过滤） |

### 验证点

- 空列表归一化为 None
- None 输入直接返回 None
- QueryHandler 将空过滤转换为无过滤传递给 Retriever

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_language_filter.py::test_c1_empty_list_returns_none, tests/test_language_filter.py::test_c2_none_returns_none, tests/test_language_filter.py::test_d2_query_handler_empty_languages_passes_none
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-020-002

### 关联需求

FR-018（Language Filter — 边界输入处理）

### 测试目标

验证空白填充输入和单字符语言名正确处理。

### 前置条件

- LanguageFilter 类已实现并可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 `validate(["  java  "])` | 返回 `["java"]`（去除空白后归一化） |
| 2 | 调用 `validate(["c"])` | 返回 `["c"]`（单字符语言有效） |
| 3 | 调用 `validate(["c++"])` | 返回 `["c++"]`（含特殊字符的语言有效） |

### 验证点

- 空白填充的语言字符串被正确 strip 和 lowercase
- 单字符语言 "c" 不被拒绝
- 含 "+" 特殊字符的语言 "c++" 不被拒绝

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_language_filter.py::test_c3_whitespace_stripped, tests/test_language_filter.py::test_c4_single_char_language_c, tests/test_language_filter.py::test_a5_cpp_special_char
- **Test Type**: Real

---

## 可追溯性矩阵

| 用例 ID | 需求 | verification_step | 自动化测试 | 结果 |
|---------|------|-------------------|------------|------|
| ST-FUNC-020-001 | FR-018 AC-1 | VS-1: query 'timeout' with language_filter=['java'] → all chunks language='java' | test_a1, test_a3, test_d1 | PASS |
| ST-FUNC-020-002 | FR-018 AC-2 | VS-2: multiple languages ['java', 'python'] → chunks in either | test_a2, test_a6 | PASS |
| ST-FUNC-020-003 | FR-018 AC-3 | VS-3: unrecognized 'rust' → ValidationError listing supported | test_b1, test_b2, test_b3, test_d3 | PASS |
| ST-BNDRY-020-001 | FR-018 AC-4 | VS-4: empty language filter → no filtering applied | test_c1, test_c2, test_d2 | PASS |
| ST-BNDRY-020-002 | FR-018 | Boundary: whitespace, single-char, special chars | test_c3, test_c4, test_a5 | PASS |

## Real Test Case Execution Summary

| Total Real | Passed | Failed | Pending |
|------------|--------|--------|---------|
| 5 | 5 | 0 | 0 |
