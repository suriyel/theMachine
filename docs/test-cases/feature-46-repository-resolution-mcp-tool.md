# 测试用例集: Repository Resolution MCP Tool

**Feature ID**: 46
**关联需求**: FR-030 (Repository Resolution MCP Tool)
**日期**: 2026-03-25
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 5 |
| boundary | 5 |
| **合计** | **10** |

---

### 用例编号

ST-FUNC-046-001

### 关联需求

FR-030（Repository Resolution MCP Tool — 名称匹配返回索引仓库）

### 测试目标

验证 resolve_repository(query="JSON parse", libraryName="gson") 返回名称匹配的已索引仓库列表，排除不匹配和非 indexed 状态的仓库

### 前置条件

- MCP server 模块已实现
- mock session 返回 5 个仓库记录：gson (indexed), gson-fire (indexed), my-gson-lib (indexed), react (indexed), spring-framework (pending)
- FastMCP 实例已创建并注册了 resolve_repository 工具

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 MCP server 实例，配置 mock session 返回 5 个仓库（4 indexed, 1 pending） | MCP server 创建成功，工具已注册 |
| 2 | 调用 resolve_repository(query="JSON parse", libraryName="gson") | 返回 JSON 字符串 |
| 3 | 解析返回的 JSON 数组 | 数组长度为 3（仅匹配 gson 的 indexed 仓库） |
| 4 | 验证返回的仓库名称 | 包含 "gson", "gson-fire", "my-gson-lib"；不包含 "react", "spring-framework" |

### 验证点

- 返回值是合法的 JSON 数组
- 仅包含名称/URL 中含 "gson" 的 indexed 仓库
- pending 状态仓库 (spring-framework) 被排除
- 不匹配的仓库 (react) 被排除

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_resolve_repository.py::test_resolve_returns_only_matching_repos
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-046-002

### 关联需求

FR-030（Repository Resolution MCP Tool — 结果字段完整性）

### 测试目标

验证每个返回结果包含所有 7 个必需字段：id, name, url, indexed_branch, default_branch, available_branches, last_indexed_at

### 前置条件

- MCP server 模块已实现
- mock session 返回包含完整字段的 indexed 仓库

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 MCP server 实例，配置 mock 仓库数据 | MCP server 创建成功 |
| 2 | 调用 resolve_repository(query="JSON parse", libraryName="gson") | 返回 JSON 字符串 |
| 3 | 解析 JSON 数组，验证每个对象的键集合 | 每个对象恰好包含 7 个键：id, name, url, indexed_branch, default_branch, available_branches, last_indexed_at |
| 4 | 验证字段类型和非空性 | name 非空, url 以 "https://" 开头, indexed_branch 非 null, available_branches 为列表类型 |

### 验证点

- 每个结果对象恰好包含 7 个键
- 字段名称与 SRS AC-2 规范完全一致
- id 为 owner/repo 格式字符串
- available_branches 为列表类型

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_resolve_repository.py::test_resolve_result_contains_all_required_fields
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-046-003

### 关联需求

FR-030（Repository Resolution MCP Tool — 匹配质量排序）

### 测试目标

验证多个匹配仓库按名称匹配质量排序：exact match > prefix match > substring match

### 前置条件

- MCP server 模块已实现
- mock session 返回 3 个 indexed 仓库：gson（精确匹配）, gson-fire（前缀匹配）, my-gson-lib（子字符串匹配）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 MCP server 实例，配置 mock 仓库 | MCP server 创建成功 |
| 2 | 调用 resolve_repository(query="test", libraryName="gson") | 返回 JSON 字符串 |
| 3 | 解析 JSON 数组并提取仓库名称列表 | 名称顺序为 ["gson", "gson-fire", "my-gson-lib"]（exact=tier0, prefix=tier2, substring=tier4） |

### 验证点

- 精确匹配 "gson" 排在第一位 (tier 0)
- 前缀匹配 "gson-fire" 排在第二位 (tier 2)
- 子字符串匹配 "my-gson-lib" 排在最后 (tier 4)
- 排序为 tier 升序

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_resolve_repository.py::test_resolve_sorts_by_match_quality
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-046-004

### 关联需求

FR-030（Repository Resolution MCP Tool — available_branches 填充）

### 测试目标

验证有 clone_path 的仓库通过 GitCloner 填充 available_branches，无 clone_path 的仓库返回空列表

### 前置条件

- MCP server 模块已实现
- mock GitCloner.list_remote_branches 返回 ["dev", "main"]
- mock session 返回包含 clone_path="/tmp/gson" 和 clone_path=None 的仓库

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 MCP server 实例，配置 mock GitCloner 和仓库 | MCP server 创建成功 |
| 2 | 调用 resolve_repository(query="test", libraryName="gson") | 返回 JSON 字符串 |
| 3 | 解析 JSON，检查 "gson"（有 clone_path）的 available_branches | 值为 ["dev", "main"] |
| 4 | 检查 "gson-fire"（无 clone_path）的 available_branches | 值为 [] |

### 验证点

- 有 clone_path 的仓库 available_branches 包含实际分支列表
- 无 clone_path 的仓库 available_branches 为空列表
- GitCloner 仅对有 clone_path 的仓库被调用

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_resolve_repository.py::test_resolve_populates_available_branches
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-046-005

### 关联需求

FR-030（Repository Resolution MCP Tool — 缺少参数抛出 TypeError）

### 测试目标

验证 resolve_repository 在缺少 query 或 libraryName 必填参数时由 MCP 框架抛出 TypeError

### 前置条件

- MCP server 模块已实现
- resolve_repository 函数签名中 query 和 libraryName 均为必填位置参数（无默认值）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 MCP server 实例 | 创建成功 |
| 2 | 调用 resolve_repository(libraryName="gson")，不传 query | 抛出 TypeError（缺少必填参数） |
| 3 | 调用 resolve_repository(query="test")，不传 libraryName | 抛出 TypeError（缺少必填参数） |

### 验证点

- 缺少 query 时 Python 运行时抛出 TypeError
- 缺少 libraryName 时 Python 运行时抛出 TypeError
- 不是返回 None 或空结果，而是直接抛出类型错误

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_resolve_repository.py::test_resolve_missing_query_raises_type_error, test_resolve_missing_library_name_raises_type_error
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-046-001

### 关联需求

FR-030（Repository Resolution MCP Tool — 无匹配返回空列表）

### 测试目标

验证 libraryName 无匹配任何已索引仓库时返回空 JSON 数组

### 前置条件

- MCP server 模块已实现
- mock session 返回已索引仓库但无任何名称匹配 "zzz-nonexistent-zzz"

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 MCP server 实例 | 创建成功 |
| 2 | 调用 resolve_repository(query="test", libraryName="zzz-nonexistent-zzz") | 返回 JSON 字符串 |
| 3 | 解析 JSON | 空数组 `[]` |

### 验证点

- 不匹配的 libraryName 返回空数组而非抛出错误
- 空数组是合法的 JSON (`[]`)

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_resolve_repository.py::test_resolve_no_match_returns_empty
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-046-002

### 关联需求

FR-030（Repository Resolution MCP Tool — 大小写不敏感匹配）

### 测试目标

验证 libraryName 大小写不敏感："GSON" 能匹配名为 "gson" 的仓库

### 前置条件

- MCP server 模块已实现
- mock session 返回名为 "gson" 的 indexed 仓库

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 MCP server 实例 | 创建成功 |
| 2 | 调用 resolve_repository(query="test", libraryName="GSON")（全大写） | 返回 JSON 字符串 |
| 3 | 解析 JSON 数组 | 包含名为 "gson" 的仓库 |

### 验证点

- 大写 libraryName 匹配小写仓库名
- 大小写不敏感匹配在名称和 URL 中均生效

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_resolve_repository.py::test_resolve_case_insensitive
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-046-003

### 关联需求

FR-030（Repository Resolution MCP Tool — 空/空白输入验证）

### 测试目标

验证空字符串和纯空白字符串的 query 或 libraryName 触发 ValueError

### 前置条件

- MCP server 模块已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 resolve_repository(query="", libraryName="gson") | 抛出 ValueError，消息 "query is required" |
| 2 | 调用 resolve_repository(query="test", libraryName="") | 抛出 ValueError，消息 "libraryName is required" |
| 3 | 调用 resolve_repository(query="   ", libraryName="gson")（空白 query） | 抛出 ValueError，消息 "query is required" |

### 验证点

- 空字符串被视为无效输入，触发 ValueError
- 空白字符串被视为无效输入，触发 ValueError
- 错误消息准确描述缺少的参数

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_resolve_repository.py::test_resolve_empty_query_raises_value_error, test_resolve_empty_library_name_raises_value_error, test_resolve_whitespace_query_raises_value_error
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-046-004

### 关联需求

FR-030（Repository Resolution MCP Tool — URL 尾部斜杠处理）

### 测试目标

验证 URL 末尾带斜杠（如 "https://github.com/org/gson/"）时正确提取 URL path segment 进行匹配

### 前置条件

- MCP server 模块已实现
- mock session 返回 URL 带尾部斜杠的 indexed 仓库

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 MCP server 实例，仓库 URL 为 "https://github.com/org/gson/"（尾部斜杠） | 创建成功 |
| 2 | 调用 resolve_repository(query="test", libraryName="gson") | 返回 JSON 字符串 |
| 3 | 解析 JSON 数组 | 包含 1 个匹配仓库（尾部斜杠被正确剥离后提取 "gson" 段） |

### 验证点

- 尾部斜杠不影响 URL segment 提取
- URL segment 正确提取为 "gson"（非空字符串）
- 仓库被正确匹配并返回

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_resolve_repository.py::test_resolve_url_trailing_slash
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-046-005

### 关联需求

FR-030（Repository Resolution MCP Tool — GitCloner 错误和边界条件）

### 测试目标

验证 GitCloner 错误、git_cloner=None、clone_path=None/空 等边界条件下 available_branches 优雅降级为空列表

### 前置条件

- MCP server 模块已实现
- 测试不同的 GitCloner 和 clone_path 边界条件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 配置 GitCloner.list_remote_branches 抛出 Exception("git error")，仓库有 clone_path | available_branches 为 [] |
| 2 | 创建 MCP server 不传 git_cloner（默认 None），仓库有 clone_path | available_branches 为 [] |
| 3 | 配置仓库 clone_path=None，传入正常的 git_cloner | available_branches 为 []，git_cloner.list_remote_branches 未被调用 |
| 4 | 配置仓库 clone_path=""（空字符串），传入正常的 git_cloner | available_branches 为 []，git_cloner.list_remote_branches 未被调用 |

### 验证点

- GitCloner 异常不传播到 resolve_repository 调用方
- git_cloner=None 时优雅降级
- clone_path 为 None 或空字符串时不调用 GitCloner
- 所有边界条件均返回空列表而非抛出异常

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_resolve_repository.py::test_resolve_git_cloner_error_returns_empty_branches, test_resolve_no_git_cloner_returns_empty_branches, test_resolve_none_clone_path_empty_branches, test_resolve_empty_clone_path_empty_branches
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-046-001 | FR-030 | verification_step[0]: resolve_repository(query='JSON parse', libraryName='gson') returns indexed repos with name match | test_resolve_returns_only_matching_repos | Mock | PASS |
| ST-FUNC-046-002 | FR-030 | verification_step[1]: Each result includes id, name, url, indexed_branch, default_branch, available_branches, last_indexed_at | test_resolve_result_contains_all_required_fields | Mock | PASS |
| ST-FUNC-046-003 | FR-030 | verification_step[4]: Results sorted by name match quality (exact > prefix > substring) | test_resolve_sorts_by_match_quality | Mock | PASS |
| ST-FUNC-046-004 | FR-030 | verification_step[1]: Each result includes available_branches (populated from GitCloner) | test_resolve_populates_available_branches | Mock | PASS |
| ST-FUNC-046-005 | FR-030 | verification_step[3]: Missing query or libraryName parameter raises TypeError | test_resolve_missing_query_raises_type_error, test_resolve_missing_library_name_raises_type_error | Mock | PASS |
| ST-BNDRY-046-001 | FR-030 | verification_step[2]: libraryName matching no indexed repo returns empty list | test_resolve_no_match_returns_empty | Mock | PASS |
| ST-BNDRY-046-002 | FR-030 | verification_step[0]: resolve_repository matching (case-insensitive) | test_resolve_case_insensitive | Mock | PASS |
| ST-BNDRY-046-003 | FR-030 | verification_step[3]: Missing/empty query or libraryName validation | test_resolve_empty_query_raises_value_error, test_resolve_empty_library_name_raises_value_error, test_resolve_whitespace_query_raises_value_error | Mock | PASS |
| ST-BNDRY-046-004 | FR-030 | verification_step[0]: resolve_repository URL matching with trailing slash | test_resolve_url_trailing_slash | Mock | PASS |
| ST-BNDRY-046-005 | FR-030 | verification_step[1]: available_branches graceful degradation (git error, no cloner, no clone_path) | test_resolve_git_cloner_error_returns_empty_branches, test_resolve_no_git_cloner_returns_empty_branches, test_resolve_none_clone_path_empty_branches, test_resolve_empty_clone_path_empty_branches | Mock | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 0 |
| Passed | 0 |
| Failed | 0 |
| Pending | 0 |

> All test cases for this feature use Mock (mocked DB session, GitCloner, ES client). The resolve_repository tool is tested via direct function invocation against mocked dependencies.
> Any Mock test case FAIL still blocks the feature from being marked `"passing"` — must be fixed and re-executed.
