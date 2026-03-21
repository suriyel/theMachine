# 测试用例集: Repository Registration

**Feature ID**: 3
**关联需求**: FR-001（Repository Registration）[Wave 1 — branch selection]
**日期**: 2026-03-21
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 5 |
| boundary | 2 |
| **合计** | **7** |

---

### 用例编号

ST-FUNC-003-001

### 关联需求

FR-001（Repository Registration）

### 测试目标

验证通过有效 Git URL 注册仓库时（不指定分支），系统创建 Repository（indexed_branch=None）和 IndexJob（branch="main"）记录。

### 前置条件

- PostgreSQL 数据库运行中，repository 和 index_job 表已创建
- RepoManager 可访问数据库会话

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 `register("https://github.com/pallets/flask")` | 返回 Repository 对象 |
| 2 | 检查返回的 Repository 对象字段 | id 为有效 UUID，name="pallets/flask"，url="https://github.com/pallets/flask"，status="pending"，indexed_branch=None |
| 3 | 查询 IndexJob 表中 repo_id 匹配的记录 | 存在一条 IndexJob，branch="main"（占位符），status="pending" |

### 验证点

- Repository.id 是有效 UUID
- Repository.name 等于 "pallets/flask"
- Repository.status 等于 "pending"
- Repository.indexed_branch 为 None（未指定分支）
- IndexJob.repo_id 等于 Repository.id
- IndexJob.branch 等于 "main"（默认占位符）

### 后置检查

- 删除测试创建的 IndexJob 和 Repository 记录

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_repo_manager.py::test_register_valid_url
- **Test Type**: Real

---

### 用例编号

ST-FUNC-003-002

### 关联需求

FR-001（Repository Registration）

### 测试目标

验证提交有效 URL 并指定 branch="develop" 时，Repository.indexed_branch 和 IndexJob.branch 均为 "develop"。

### 前置条件

- PostgreSQL 数据库运行中
- RepoManager 可访问数据库会话

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 `register("https://github.com/pallets/flask", branch="develop")` | 返回 Repository 对象 |
| 2 | 检查 Repository.indexed_branch | 等于 "develop" |
| 3 | 查询 IndexJob 表中 repo_id 匹配的记录 | IndexJob.branch 等于 "develop" |

### 验证点

- Repository.indexed_branch 等于 "develop"
- IndexJob.branch 等于 "develop"（与指定分支一致）
- Repository.status 等于 "pending"

### 后置检查

- 删除测试创建的记录

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_repo_manager.py::test_register_with_branch
- **Test Type**: Real

---

### 用例编号

ST-FUNC-003-003

### 关联需求

FR-001（Repository Registration）

### 测试目标

验证提交无效 URL 时，系统在 2 秒内返回 ValidationError 且不创建记录。

### 前置条件

- PostgreSQL 数据库运行中
- RepoManager 可访问数据库会话

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 `register("not-a-url")` | 抛出 ValidationError |
| 2 | 调用 `register("")` | 抛出 ValidationError，消息包含 "URL must not be empty" |
| 3 | 调用 `register("ftp://example.com/repo")` | 抛出 ValidationError，消息包含 "Unsupported" |
| 4 | 查询 repository 表 | 无新记录创建 |

### 验证点

- 每种无效输入均抛出 ValidationError
- 数据库中无残留记录
- 响应时间 < 2 秒

### 后置检查

- 确认数据库中无测试残留数据

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_repo_manager.py::test_register_invalid_url_raises_validation_error, tests/test_repo_manager.py::test_register_empty_url_raises_validation_error, tests/test_repo_manager.py::test_register_unsupported_scheme_raises_validation_error
- **Test Type**: Real

---

### 用例编号

ST-FUNC-003-004

### 关联需求

FR-001（Repository Registration）

### 测试目标

验证重复提交已注册 URL 时，系统返回 ConflictError（与分支无关）。

### 前置条件

- PostgreSQL 数据库运行中
- 已通过 register() 注册 "https://github.com/pallets/flask"

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 `register("https://github.com/pallets/flask")` | 成功注册，返回 Repository |
| 2 | 再次调用 `register("https://github.com/pallets/flask")` | 抛出 ConflictError，消息包含 "already registered" |
| 3 | 调用 `register("https://github.com/pallets/flask.git")` | 抛出 ConflictError（URL 归一化后重复） |
| 4 | 调用 `register("https://github.com/pallets/flask", branch="develop")` | 抛出 ConflictError（URL 重复检测与分支无关） |

### 验证点

- 第二次注册相同 URL 抛出 ConflictError
- 归一化后的变体（.git 后缀）也被检测为重复
- 相同 URL 不同分支仍被检测为重复
- 数据库中仅有一条该 URL 的 Repository 记录

### 后置检查

- 删除测试创建的记录

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_repo_manager.py::test_register_duplicate_url_raises_conflict_error, tests/test_repo_manager.py::test_register_duplicate_with_normalization, tests/test_repo_manager.py::test_register_duplicate_different_branch_raises_conflict
- **Test Type**: Real

---

### 用例编号

ST-FUNC-003-005

### 关联需求

FR-001（Repository Registration）

### 测试目标

验证不指定分支时，indexed_branch 为 None，IndexJob.branch 为 "main"（占位符，实际默认分支由 Feature #4 检测）。

### 前置条件

- PostgreSQL 数据库运行中
- RepoManager 可访问数据库会话

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 `register("https://github.com/owner/myrepo")` 不带 branch 参数 | 返回 Repository 对象 |
| 2 | 检查 Repository.indexed_branch | 值为 None |
| 3 | 查询 IndexJob | IndexJob.branch 等于 "main" |

### 验证点

- Repository.indexed_branch 为 None
- IndexJob.branch 等于 "main"（默认占位符）
- 不指定分支时不设默认值到 indexed_branch（留给 GitCloner 检测）

### 后置检查

- 删除测试创建的记录

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_repo_manager.py::test_register_without_branch_sets_null
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-003-001

### 关联需求

FR-001（Repository Registration）

### 测试目标

验证边界条件下的 URL 处理：归一化、空白字符、无路径、无主机。

### 前置条件

- PostgreSQL 数据库运行中
- RepoManager 可访问数据库会话

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 `register("https://GitHub.COM/Owner/Repo/")` | 成功，url="https://github.com/Owner/Repo"（主机小写，尾部斜杠去除） |
| 2 | 调用 `register("   https://github.com/a/b   ")` | 成功，前后空白被去除 |
| 3 | 调用 `register("http://github.com")` | 抛出 ValidationError，消息包含 "no repository path" |
| 4 | 调用 `register("http://")` | 抛出 ValidationError，消息包含 "no host" |

### 验证点

- 主机名大小写归一化正确
- 尾部斜杠和 .git 后缀被去除
- 空白字符被正确去除
- 无路径和无主机的 URL 被拒绝

### 后置检查

- 删除测试创建的记录

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_repo_manager.py::test_register_normalizes_case_and_trailing_slash, tests/test_repo_manager.py::test_register_whitespace_stripped, tests/test_repo_manager.py::test_register_no_path_raises_validation_error, tests/test_repo_manager.py::test_register_no_host_raises_validation_error
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-003-002

### 关联需求

FR-001（Repository Registration）

### 测试目标

验证 SSH 简写格式 URL 的支持。

### 前置条件

- PostgreSQL 数据库运行中
- RepoManager 可访问数据库会话

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 `register("git@github.com:owner/repo.git")` | 成功注册，URL 被归一化为标准格式 |
| 2 | 检查返回的 Repository 对象 | url 包含 "github.com" 和 "owner/repo"，不以 ".git" 结尾，name="owner/repo"，status="pending" |

### 验证点

- SSH 简写格式被正确解析
- .git 后缀被去除
- 名称正确提取为 "owner/repo"

### 后置检查

- 删除测试创建的记录

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_repo_manager.py::test_register_ssh_url
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-003-001 | FR-001 | VS-1: Given valid URL, register creates repo with status=pending, returns ID | test_register_valid_url | Real | PASS |
| ST-FUNC-003-002 | FR-001 | VS-2: Given valid URL with branch='develop', repo has indexed_branch='develop' | test_register_with_branch | Real | PASS |
| ST-FUNC-003-003 | FR-001 | VS-4: Given invalid URL, raises ValidationError within 2s | test_register_invalid_url, test_register_empty_url, test_register_unsupported_scheme | Real | PASS |
| ST-FUNC-003-004 | FR-001 | VS-5: Given already-registered URL, raises ConflictError | test_register_duplicate_url, test_register_duplicate_with_normalization, test_register_duplicate_different_branch | Real | PASS |
| ST-FUNC-003-005 | FR-001 | VS-3: Given no branch parameter, indexed_branch=None | test_register_without_branch_sets_null | Real | PASS |
| ST-BNDRY-003-001 | FR-001 | VS-1, VS-4 | test_register_normalizes_case, test_register_whitespace, test_register_no_path, test_register_no_host | Real | PASS |
| ST-BNDRY-003-002 | FR-001 | VS-1 | test_register_ssh_url | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 7 |
| Passed | 7 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
