# 测试用例集: MCP Server

**Feature ID**: 18
**关联需求**: FR-016 (MCP Server)
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

ST-FUNC-018-001

### 关联需求

FR-016（MCP Server — search_code_context tool）

### 测试目标

验证 search_code_context 工具接收查询参数并返回与 REST API 格式一致的结构化上下文结果

### 前置条件

- MCP server 模块已实现
- QueryHandler 已初始化（可使用 mock）
- FastMCP 实例已创建并注册了 3 个工具

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 MCP server 实例，配置 mock QueryHandler 返回包含 code_results 和 doc_results 的 QueryResponse | MCP server 创建成功，3 个工具已注册 |
| 2 | 调用 search_code_context(query="spring webclient timeout", repo="spring-framework") | 返回 JSON 字符串 |
| 3 | 解析返回的 JSON 字符串 | JSON 包含 "query", "query_type", "code_results", "doc_results" 键 |
| 4 | 验证 code_results[0] 的字段 | file_path, content, relevance_score 字段存在且值正确 |

### 验证点

- 返回值是合法的 JSON 字符串
- JSON 结构包含 query, query_type, code_results, doc_results 四个顶层键
- code_results 中的条目包含 file_path 和 relevance_score
- 返回格式与 REST API 的 QueryResponse 一致

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_mcp_server.py::test_search_code_context_returns_valid_json
- **Test Type**: Real

---

### 用例编号

ST-FUNC-018-002

### 关联需求

FR-016（MCP Server — list_repositories tool）

### 测试目标

验证 list_repositories 工具返回包含所有必要字段的仓库列表

### 前置条件

- MCP server 模块已实现
- Mock session 返回 3 个仓库记录

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 MCP server 实例，配置 mock session 返回 3 个仓库 | MCP server 创建成功 |
| 2 | 调用 list_repositories() 无参数 | 返回 JSON 字符串 |
| 3 | 解析 JSON 数组 | 数组长度为 3 |
| 4 | 验证每个仓库对象的字段 | 包含 id, name, url, default_branch, indexed_branch, last_indexed_at, status 共 7 个字段 |

### 验证点

- 返回值是合法的 JSON 数组
- 数组包含 3 个仓库对象
- 每个对象包含 7 个必要字段（id, name, url, default_branch, indexed_branch, last_indexed_at, status）
- 字段值与 mock 数据一致

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_mcp_server.py::test_list_repositories_returns_all_repos
- **Test Type**: Real

---

### 用例编号

ST-FUNC-018-003

### 关联需求

FR-016（MCP Server — cross-repository search）

### 测试目标

验证不提供 repo 参数时 search_code_context 搜索所有仓库

### 前置条件

- MCP server 模块已实现
- QueryHandler mock 已配置

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 MCP server 实例 | 创建成功 |
| 2 | 调用 search_code_context(query="timeout")，不传 repo 参数 | 调用成功，返回 JSON |
| 3 | 验证 QueryHandler.handle_nl_query 的调用参数 | repo 参数为 None |

### 验证点

- search_code_context 不传 repo 时，QueryHandler 的 repo 参数为 None
- 搜索跨所有仓库执行

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_mcp_server.py::test_search_code_context_without_repo
- **Test Type**: Real

---

### 用例编号

ST-FUNC-018-004

### 关联需求

FR-016（MCP Server — error handling）

### 测试目标

验证缺少必需 query 字段时返回 MCP 错误响应，以及内部检索失败时返回错误而非崩溃

### 前置条件

- MCP server 模块已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 search_code_context(query="") | 抛出 ValueError，消息包含 "query is required" |
| 2 | 配置 QueryHandler 抛出 RetrievalError | mock 设置成功 |
| 3 | 调用 search_code_context(query="test") | 抛出 RuntimeError，消息包含 "Retrieval failed" |
| 4 | 配置 QueryHandler 抛出 ValidationError("Unsupported language: rust") | mock 设置成功 |
| 5 | 调用 search_code_context(query="test") | 抛出 ValueError，消息包含 "Unsupported language: rust" |

### 验证点

- 空查询触发 ValueError（不会崩溃 MCP 连接）
- RetrievalError 被转换为 RuntimeError
- ValidationError 被转换为 ValueError
- 错误消息包含有意义的描述

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_mcp_server.py::test_search_code_context_empty_query_raises, test_search_code_context_retrieval_error, test_search_code_context_validation_error
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-018-001

### 关联需求

FR-016（MCP Server — boundary inputs）

### 测试目标

验证边界输入（空白字符串、单字符查询）的处理行为

### 前置条件

- MCP server 模块已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 search_code_context(query="   ")（仅空白） | 抛出 ValueError，消息 "query is required" |
| 2 | 调用 get_chunk(chunk_id="   ")（仅空白） | 抛出 ValueError，消息 "chunk_id is required" |
| 3 | 调用 search_code_context(query="x")（单字符） | 调用成功，QueryHandler 被调用 |
| 4 | 调用 get_chunk(chunk_id="")（空字符串） | 抛出 ValueError |

### 验证点

- 空白字符串被视为空值，触发验证错误
- 单字符查询被接受并正常处理
- 空字符串的 chunk_id 触发验证错误

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_mcp_server.py::test_search_code_context_whitespace_query_raises, test_get_chunk_whitespace_id_raises, test_search_code_context_single_char_query, test_get_chunk_empty_id_raises
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-018-002

### 关联需求

FR-016（MCP Server — list_repositories filter boundaries）

### 测试目标

验证 list_repositories 的过滤参数在边界条件下的行为

### 前置条件

- MCP server 模块已实现
- Mock session 返回 3 个仓库（spring-framework, react, spring-boot）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 list_repositories(query="")（空字符串） | 返回所有 3 个仓库（不应用过滤） |
| 2 | 调用 list_repositories(query="spring") | 返回 2 个仓库（spring-framework, spring-boot） |
| 3 | 调用 list_repositories(query="SPRING")（大写） | 返回 2 个仓库（大小写不敏感匹配） |

### 验证点

- 空字符串过滤器不过滤任何结果
- 子字符串匹配在名称和 URL 中生效
- 过滤是大小写不敏感的

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_mcp_server.py::test_list_repositories_empty_filter_returns_all, test_list_repositories_with_filter, test_list_repositories_case_insensitive_filter
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-018-001 | FR-016 | VS-1: search_code_context returns structured results | test_search_code_context_returns_valid_json | Real | PASS |
| ST-FUNC-018-002 | FR-016 | VS-2: list_repositories returns repo list with status | test_list_repositories_returns_all_repos | Real | PASS |
| ST-FUNC-018-003 | FR-016 | VS-3: search without repo searches all repositories | test_search_code_context_without_repo | Real | PASS |
| ST-FUNC-018-004 | FR-016 | VS-4: missing query returns MCP error | test_search_code_context_empty_query_raises, test_search_code_context_retrieval_error, test_search_code_context_validation_error | Real | PASS |
| ST-BNDRY-018-001 | FR-016 | VS-4: boundary inputs (whitespace, single char) | test_search_code_context_whitespace_query_raises, test_get_chunk_whitespace_id_raises, test_search_code_context_single_char_query | Real | PASS |
| ST-BNDRY-018-002 | FR-016 | VS-2: filter edge cases (empty, case-insensitive) | test_list_repositories_empty_filter_returns_all, test_list_repositories_with_filter, test_list_repositories_case_insensitive_filter | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 6 |
| Passed | 6 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
