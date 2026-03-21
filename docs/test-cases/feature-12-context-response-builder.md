# 测试用例集: Context Response Builder

**Feature ID**: 12
**关联需求**: FR-010（Context Response Builder）
**日期**: 2026-03-21
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 3 |
| boundary | 3 |
| **合计** | **6** |

---

### 用例编号

ST-FUNC-012-001

### 关联需求

FR-010（Context Response Builder）

### 测试目标

验证6个重排序结果（3 code、2 doc、1 example）正确拆分为 codeResults 和 docResults 双列表，所有必需字段均存在。

### 前置条件

- ResponseBuilder 类已实现
- ScoredChunk 数据类可用
- 6个 ScoredChunk 实例准备就绪（3个 content_type="code"、2个 content_type="doc"、1个 content_type="example"）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 ResponseBuilder 实例（默认 max_content_length=2000） | 实例创建成功 |
| 2 | 构造 3 个 code ScoredChunk（各带不同 symbol）、2 个 doc ScoredChunk、1 个 example ScoredChunk | 6 个 ScoredChunk 对象就绪 |
| 3 | 调用 build(chunks, query="auth", query_type="nl", repo="my-org/app") | 返回 QueryResponse 对象 |
| 4 | 检查 response.code_results 长度 | 等于 3 |
| 5 | 检查 response.doc_results 长度 | 等于 3（2 doc + 1 example） |
| 6 | 检查每个 CodeResult 的字段 | 包含 file_path、lines、symbol、chunk_type、language、content、relevance_score |
| 7 | 检查每个 DocResult 的字段 | 包含 file_path、breadcrumb、content、relevance_score |

### 验证点

- codeResults 仅包含 content_type="code" 的结果
- docResults 包含 content_type="doc" 和 content_type="example" 的结果
- 每个结果对象包含所有 FR-010 规定的字段

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_response_builder.py::test_build_splits_6_chunks_into_code_and_doc_results
- **Test Type**: Real

---

### 用例编号

ST-FUNC-012-002

### 关联需求

FR-010（Context Response Builder）

### 测试目标

验证内容超过2000字符时被截断并附加 '...' 指示符，同时 truncated 标志为 True。

### 前置条件

- ResponseBuilder 类已实现
- 一个 content 字段包含 2001 个字符的 ScoredChunk

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 ResponseBuilder 实例 | 实例创建成功 |
| 2 | 构造一个 code ScoredChunk，content = "x" * 2001 | ScoredChunk 就绪 |
| 3 | 调用 build([chunk], query="test", query_type="nl") | 返回 QueryResponse |
| 4 | 检查 code_results[0].content 长度 | 等于 2003（2000 + "..."） |
| 5 | 检查 code_results[0].content 末尾 | 以 "..." 结尾 |
| 6 | 检查 code_results[0].truncated | 等于 True |

### 验证点

- 截断后内容为原内容前2000字符 + "..."
- truncated 字段正确反映截断状态

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_response_builder.py::test_content_truncated_at_2001_chars
- **Test Type**: Real

---

### 用例编号

ST-FUNC-012-003

### 关联需求

FR-010（Context Response Builder）

### 测试目标

验证当提供 rules 参数时，响应包含按类别分组的 rules 部分。

### 前置条件

- ResponseBuilder 类已实现
- 3个 rule ScoredChunk（chunk_type 分别为 agent_rules、contribution_guide、linter_config）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 ResponseBuilder 实例 | 实例创建成功 |
| 2 | 构造3个 rule ScoredChunk，分别为 agent_rules、contribution_guide、linter_config 类型 | 3个规则对象就绪 |
| 3 | 调用 build([], query="test", query_type="nl", repo="org/app", rules=rules) | 返回 QueryResponse |
| 4 | 检查 response.rules | 不为 None |
| 5 | 检查 response.rules.agent_rules | 包含 "Use async sessions" |
| 6 | 检查 response.rules.contribution_guide | 包含 "All PRs need tests" |
| 7 | 检查 response.rules.linter_config | 包含 "ruff: line-length=120" |

### 验证点

- rules 部分包含所有三个类别
- 每个类别包含对应的规则内容

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_response_builder.py::test_rules_section_populated_with_categories
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-012-001

### 关联需求

FR-010（Context Response Builder）

### 测试目标

验证空 chunks 列表输入产生空的 codeResults 和 docResults。

### 前置条件

- ResponseBuilder 类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 ResponseBuilder 实例 | 实例创建成功 |
| 2 | 调用 build([], query="test", query_type="nl") | 返回 QueryResponse |
| 3 | 检查 response.code_results | 等于 [] |
| 4 | 检查 response.doc_results | 等于 [] |
| 5 | 检查 response.rules | 等于 None |

### 验证点

- 空输入不会抛出异常
- 返回结构完整的空响应

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_response_builder.py::test_empty_chunks_returns_empty_results
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-012-002

### 关联需求

FR-010（Context Response Builder）

### 测试目标

验证内容恰好2000字符时不被截断（边界条件）。

### 前置条件

- ResponseBuilder 类已实现
- 一个 content 字段恰好为2000字符的 ScoredChunk

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 ResponseBuilder 实例 | 实例创建成功 |
| 2 | 构造 code ScoredChunk，content = "a" * 2000 | ScoredChunk 就绪 |
| 3 | 调用 build([chunk], query="test", query_type="nl") | 返回 QueryResponse |
| 4 | 检查 code_results[0].content 长度 | 等于 2000 |
| 5 | 检查 code_results[0].truncated | 等于 False |

### 验证点

- 恰好在边界值时不触发截断
- truncated 标志为 False

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_response_builder.py::test_content_exactly_2000_chars_not_truncated
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-012-003

### 关联需求

FR-010（Context Response Builder）

### 测试目标

验证 rules 参数为 None 或空列表时，响应不包含 rules 部分。

### 前置条件

- ResponseBuilder 类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 ResponseBuilder 实例 | 实例创建成功 |
| 2 | 调用 build([code_chunk], query="test", query_type="nl", rules=None) | 返回 QueryResponse |
| 3 | 检查 response.rules | 等于 None |
| 4 | 调用 build([code_chunk], query="test", query_type="nl", rules=[]) | 返回 QueryResponse |
| 5 | 检查 response.rules | 等于 None |

### 验证点

- rules=None 时 rules 字段为 None
- rules=[] 时 rules 字段为 None（空列表视为无规则）

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_response_builder.py::test_rules_none_omitted_from_response, tests/test_response_builder.py::test_rules_empty_list_omitted_from_response
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-012-001 | FR-010 | VS-1: 6 reranked results split into codeResults[3] + docResults[3] | test_build_splits_6_chunks_into_code_and_doc_results | Real | PASS |
| ST-FUNC-012-002 | FR-010 | VS-2: content >2000 chars truncated with '...' | test_content_truncated_at_2001_chars | Real | PASS |
| ST-FUNC-012-003 | FR-010 | VS-3: rules section with include_rules=true | test_rules_section_populated_with_categories | Real | PASS |
| ST-BNDRY-012-001 | FR-010 | VS-1 (boundary: empty input) | test_empty_chunks_returns_empty_results | Real | PASS |
| ST-BNDRY-012-002 | FR-010 | VS-2 (boundary: exactly 2000 chars) | test_content_exactly_2000_chars_not_truncated | Real | PASS |
| ST-BNDRY-012-003 | FR-010 | VS-3 (boundary: rules=None/[]) | test_rules_none_omitted_from_response, test_rules_empty_list_omitted_from_response | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 6 |
| Passed | 6 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
