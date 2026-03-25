# 测试用例集: MCP Server

**Feature ID**: 18
**关联需求**: FR-016 (MCP Server)
**日期**: 2026-03-25
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 5 |
| boundary | 4 |
| **合计** | **9** |

---

### 用例编号

ST-FUNC-018-001

### 关联需求

FR-016（MCP Server — resolve_repository tool）

### 测试目标

验证 resolve_repository 工具接收 query 和 libraryName 参数后，返回仅含 status=indexed 仓库的列表，包含所有必需字段（id, name, url, indexed_branch, default_branch, available_branches, last_indexed_at）

### 前置条件

- MCP server 模块已实现
- mock session 返回 3 个仓库记录（2 个 indexed: spring-framework, spring-boot; 1 个 pending: react）
- FastMCP 实例已创建并注册了 3 个工具

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 MCP server 实例，配置 mock session 返回 3 个仓库（2 indexed, 1 pending） | MCP server 创建成功，3 个工具已注册 |
| 2 | 调用 resolve_repository(query="JSON parsing", libraryName="spring") | 返回 JSON 字符串 |
| 3 | 解析返回的 JSON 数组 | 数组长度为 2（仅 indexed 仓库） |
| 4 | 验证每个仓库对象的字段 | 包含 id, name, url, indexed_branch, default_branch, available_branches, last_indexed_at 共 7 个字段；available_branches 为列表类型 |
| 5 | 验证 react（pending 仓库）不在结果中 | 结果名称集合为 {"spring-framework", "spring-boot"} |

### 验证点

- 返回值是合法的 JSON 数组
- 仅包含 status=indexed 的仓库（排除 pending/error 状态）
- 每个对象包含 7 个必要字段
- available_branches 字段为列表类型

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_mcp_server.py::test_resolve_repository_returns_indexed_repos_only
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-018-002

### 关联需求

FR-016（MCP Server — search_code_context with repo required）

### 测试目标

验证 search_code_context 工具在 repo 为必填参数时，接收 query 和 repo 参数后返回与 REST API 格式一致的结构化上下文结果

### 前置条件

- MCP server 模块已实现
- QueryHandler mock 已配置，返回包含 code_results 和 doc_results 的 QueryResponse

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 MCP server 实例，配置 mock QueryHandler | MCP server 创建成功 |
| 2 | 调用 search_code_context(query="spring webclient timeout", repo="spring-framework") | 返回 JSON 字符串 |
| 3 | 解析返回的 JSON 字符串 | JSON 包含 "query", "query_type", "code_results", "doc_results" 键 |
| 4 | 验证 QueryHandler.handle_nl_query 的调用参数 | 调用参数为 ("spring webclient timeout", "spring-framework", None) |

### 验证点

- 返回值是合法的 JSON 字符串
- JSON 结构包含 query, query_type, code_results, doc_results 四个顶层键
- repo 参数被正确传递给 QueryHandler
- 返回格式与 REST API 的 QueryResponse 一致

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_mcp_server.py::test_search_code_context_with_required_repo
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-018-003

### 关联需求

FR-016（MCP Server — @branch pass-through）

### 测试目标

验证 search_code_context 在 repo 参数包含 @branch 后缀时，将完整的 repo 字符串（含 @branch）原样传递给 QueryHandler，由 QueryHandler 内部解析分支

### 前置条件

- MCP server 模块已实现
- QueryHandler mock 已配置

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 MCP server 实例 | 创建成功 |
| 2 | 调用 search_code_context(query="spring webclient timeout", repo="spring-framework@main") | 返回 JSON 字符串 |
| 3 | 验证 QueryHandler.handle_nl_query 的调用参数 | repo 参数为 "spring-framework@main"（未在 MCP 层解析 @branch） |

### 验证点

- QueryHandler.handle_nl_query 接收完整的 "spring-framework@main" 字符串
- MCP 层不进行 @branch 解析（解析在 QueryHandler 内部完成）

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_mcp_server.py::test_search_code_context_branch_passthrough
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-018-004

### 关联需求

FR-016（MCP Server — get_chunk tool）

### 测试目标

验证 get_chunk 工具通过 chunk_id 返回完整的 chunk 内容，绕过截断限制

### 前置条件

- MCP server 模块已实现
- Mock ES client 配置返回包含 file_path, content, language, symbol 的 chunk 文档

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 MCP server 实例，配置 mock ES 返回 chunk 文档 | MCP server 创建成功 |
| 2 | 调用 get_chunk(chunk_id="abc123") | 返回 JSON 字符串 |
| 3 | 解析 JSON 并验证字段 | 包含 file_path="src/WebClient.java", content（完整内容）, language="java", symbol="WebClient" |

### 验证点

- 返回值是合法的 JSON 字符串
- 返回的 content 是完整内容（未截断）
- 所有字段值与 ES 中的 _source 一致

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_mcp_server.py::test_get_chunk_returns_full_content
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-018-005

### 关联需求

FR-016（MCP Server — error handling）

### 测试目标

验证 MCP 工具在无效参数和内部检索失败时返回错误响应而非崩溃 MCP 连接

### 前置条件

- MCP server 模块已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 search_code_context(query="", repo="x")（空查询） | 抛出 ValueError，消息包含 "query is required" |
| 2 | 配置 QueryHandler 抛出 RetrievalError，调用 search_code_context(query="test", repo="x") | 抛出 RuntimeError，消息包含 "Retrieval failed" |
| 3 | 配置 QueryHandler 抛出 ValidationError("Unsupported language: rust")，调用 search_code_context(query="test", repo="x") | 抛出 ValueError，消息包含 "Unsupported language: rust" |
| 4 | 调用 get_chunk(chunk_id="nonexistent")，ES 返回 NotFoundError | 抛出 ValueError，消息包含 "Chunk not found" |
| 5 | 配置 mock session 抛出 Exception("DB connection lost")，调用 resolve_repository(query="test", libraryName="x") | 抛出 RuntimeError，消息包含 "Failed to resolve repositories" |
| 6 | 调用 get_chunk(chunk_id="abc123")，ES 抛出 ConnectionError | 抛出 RuntimeError，消息包含 "Failed to retrieve chunk" |

### 验证点

- 空查询触发 ValueError（不崩溃 MCP 连接）
- RetrievalError 被转换为 RuntimeError
- ValidationError 被转换为 ValueError
- ES NotFoundError 被转换为 ValueError
- DB 异常被转换为 RuntimeError
- ES ConnectionError 被转换为 RuntimeError
- 所有错误消息包含有意义的描述

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_mcp_server.py::test_search_code_context_empty_query_raises, test_search_code_context_retrieval_error, test_search_code_context_validation_error, test_get_chunk_not_found_raises, test_resolve_repository_db_failure, test_get_chunk_es_connection_failure
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-018-001

### 关联需求

FR-016（MCP Server — search_code_context without repo raises TypeError）

### 测试目标

验证 search_code_context 在不提供 repo 参数时抛出 TypeError（repo 为必填参数，无默认值）

### 前置条件

- MCP server 模块已实现
- search_code_context 函数签名中 repo 参数无默认值

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 MCP server 实例 | 创建成功 |
| 2 | 调用 search_code_context(query="test")，不传 repo 参数 | 抛出 TypeError（缺少必填参数） |

### 验证点

- Python 运行时抛出 TypeError（缺少必填位置参数 repo）
- 不是返回 None 或空结果，而是直接抛出类型错误

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_mcp_server.py::test_search_code_context_without_repo_raises_type_error
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-018-002

### 关联需求

FR-016（MCP Server — resolve_repository empty match returns empty list）

### 测试目标

验证 resolve_repository 在无匹配仓库时返回空 JSON 数组，以及大小写不敏感匹配行为

### 前置条件

- MCP server 模块已实现
- Mock session 返回 2 个 indexed 仓库（spring-framework, spring-boot）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 resolve_repository(query="JSON parsing", libraryName="nonexistent") | 返回空 JSON 数组 `[]` |
| 2 | 调用 resolve_repository(query="auth", libraryName="SPRING")（大写） | 返回 2 个仓库（大小写不敏感匹配） |

### 验证点

- 不匹配的 libraryName 返回空数组（不抛出错误）
- 大小写不敏感的子字符串匹配在 name 和 URL 中生效
- 空数组是合法的 JSON (`[]`)

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_mcp_server.py::test_resolve_repository_no_match_returns_empty, test_resolve_repository_case_insensitive
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-018-003

### 关联需求

FR-016（MCP Server — whitespace and empty input validation）

### 测试目标

验证所有工具对空白字符串和空字符串的输入验证行为

### 前置条件

- MCP server 模块已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 search_code_context(query="   ", repo="x")（仅空白） | 抛出 ValueError，消息 "query is required" |
| 2 | 调用 get_chunk(chunk_id="   ")（仅空白） | 抛出 ValueError，消息 "chunk_id is required" |
| 3 | 调用 get_chunk(chunk_id="")（空字符串） | 抛出 ValueError，消息 "chunk_id is required" |
| 4 | 调用 resolve_repository(query="", libraryName="spring")（空 query） | 抛出 ValueError，消息 "query is required" |
| 5 | 调用 resolve_repository(query="test", libraryName="")（空 libraryName） | 抛出 ValueError，消息 "libraryName is required" |
| 6 | 调用 resolve_repository(query="   ", libraryName="spring")（空白 query） | 抛出 ValueError，消息 "query is required" |
| 7 | 调用 resolve_repository(query="test", libraryName="   ")（空白 libraryName） | 抛出 ValueError，消息 "libraryName is required" |

### 验证点

- 空白字符串被视为空值，触发验证错误
- 空字符串触发验证错误
- 错误消息准确描述缺少的参数

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_mcp_server.py::test_search_code_context_whitespace_query_raises, test_get_chunk_whitespace_id_raises, test_get_chunk_empty_id_raises, test_resolve_repository_empty_query_raises, test_resolve_repository_empty_library_name_raises, test_resolve_repository_whitespace_query_raises, test_resolve_repository_whitespace_library_name_raises
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-018-004

### 关联需求

FR-016（MCP Server — tool registration and single char boundary）

### 测试目标

验证 MCP server 注册正确的 3 个工具（resolve_repository, search_code_context, get_chunk，不含已废弃的 list_repositories），以及单字符查询被接受

### 前置条件

- MCP server 模块已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 MCP server 实例 | 创建成功 |
| 2 | 获取所有注册的工具名称 | 工具集合为 {"resolve_repository", "search_code_context", "get_chunk"} |
| 3 | 验证旧工具未注册 | "list_repositories" 不在工具集合中 |
| 4 | 调用 search_code_context(query="x", repo="x")（单字符） | 调用成功，QueryHandler 被正常调用 |

### 验证点

- 注册的工具数量为 3
- 工具名称完全匹配 Wave 5 规格（不含 list_repositories）
- 单字符查询不被拒绝（边界最小值通过）

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_mcp_server.py::test_mcp_server_registers_three_correct_tools, test_search_code_context_single_char_query
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-018-001 | FR-016 | verification_step[0]: resolve_repository(query, libraryName) returns indexed repos with branches | test_resolve_repository_returns_indexed_repos_only | Mock | PASS |
| ST-FUNC-018-002 | FR-016 | verification_step[1]: search_code_context(query, repo) with repo required returns scoped results | test_search_code_context_with_required_repo | Mock | PASS |
| ST-FUNC-018-003 | FR-016 | verification_step[2]: search_code_context(query, repo='owner/repo@branch') parses branch and filters | test_search_code_context_branch_passthrough | Mock | PASS |
| ST-FUNC-018-004 | FR-016 | verification_step[4]: get_chunk(chunk_id) returns full chunk content | test_get_chunk_returns_full_content | Mock | PASS |
| ST-FUNC-018-005 | FR-016 | verification_step[5]: MCP error response on invalid params (no crash); verification_step[6]: MCP error response on internal retrieval failure (no crash) | test_search_code_context_empty_query_raises, test_search_code_context_retrieval_error, test_search_code_context_validation_error, test_get_chunk_not_found_raises, test_resolve_repository_db_failure, test_get_chunk_es_connection_failure | Mock | PASS |
| ST-BNDRY-018-001 | FR-016 | verification_step[3]: search_code_context without repo raises TypeError | test_search_code_context_without_repo_raises_type_error | Mock | PASS |
| ST-BNDRY-018-002 | FR-016 | verification_step[0]: resolve_repository(query, libraryName) returns indexed repos with branches (empty match, case-insensitive) | test_resolve_repository_no_match_returns_empty, test_resolve_repository_case_insensitive | Mock | PASS |
| ST-BNDRY-018-003 | FR-016 | verification_step[5]: MCP error response on invalid params (whitespace/empty inputs) | test_search_code_context_whitespace_query_raises, test_get_chunk_whitespace_id_raises, test_get_chunk_empty_id_raises, test_resolve_repository_empty_query_raises, test_resolve_repository_empty_library_name_raises, test_resolve_repository_whitespace_query_raises, test_resolve_repository_whitespace_library_name_raises | Mock | PASS |
| ST-BNDRY-018-004 | FR-016 | verification_step[0]: tool registration (Wave 5 tools, no list_repositories) | test_mcp_server_registers_three_correct_tools, test_search_code_context_single_char_query | Mock | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 0 |
| Passed | 0 |
| Failed | 0 |
| Pending | 0 |

> All test cases for this feature use Mock (mocked DB session, QueryHandler, ES client). The MCP server tools are tested via direct function invocation against mocked dependencies.
> Any Mock test case FAIL still blocks the feature from being marked `"passing"` — must be fixed and re-executed.
