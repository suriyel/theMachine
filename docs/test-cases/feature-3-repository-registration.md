# 测试用例集: Repository Registration (FR-001)

**Feature ID**: 3
**关联需求**: FR-001
**日期**: 2026-03-14
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 3 |
| boundary | 1 |
| **合计** | **4** |

---

### 用例编号

ST-FUNC-003-001

### 关联需求

FR-001 (Register Repository)

### 测试目标

验证有效的 Git 仓库 URL 可以成功注册，返回 201 状态码

### 前置条件

- PostgreSQL 数据库正在运行且可访问
- 应用程序可以连接到数据库

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | -------------- | ---------------- |
| 1 | POST /api/v1/repos?skip_validation=true with JSON: {"url": "https://github.com/test/repo.git", "name": "Test Repo", "languages": ["Python"]} | 请求发送成功 |
| 2 | 验证响应状态码 | 201 (Created) |
| 3 | 验证响应体包含 repository 对象 | status: "registered" |
| 4 | 验证数据库中记录存在 | 仓库记录已保存 |

### 验证点

- 响应状态码为 201
- 响应体包含 url, name, languages, status 字段
- status 值为 "registered"
- 数据库中存在对应记录

### 后置检查

- 清理测试数据（删除创建的仓库记录）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_repos_api.py::test_real_api_register_repository
- **Test Type**: Real

---

### 用例编号

ST-FUNC-003-002

### 关联需求

FR-001 (Register Repository)

### 测试目标

验证重复的仓库 URL 返回 409 冲突错误

### 前置条件

- PostgreSQL 数据库正在运行
- 存在 URL 为 "https://github.com/duplicate-api-test/repo.git" 的仓库

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | -------------- | ---------------- |
| 1 | POST /api/v1/repos?skip_validation=true with 已存在的 URL | 请求发送成功 |
| 2 | 验证响应状态码 | 409 (Conflict) |
| 3 | 验证错误消息包含 "already" 或 "duplicate" | 错误消息正确 |

### 验证点

- 响应状态码为 409
- 错误消息包含 "already registered" 或类似文本

### 后置检查

- 清理测试数据

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_repos_api.py::test_real_api_duplicate_url_returns_409
- **Test Type**: Real

---

### 用例编号

ST-FUNC-003-003

### 关联需求

FR-001 (Register Repository)

### 测试目标

验证获取仓库列表返回 200 状态码

### 前置条件

- PostgreSQL 数据库正在运行
- 至少存在一个仓库记录

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | -------------- | ---------------- |
| 1 | GET /api/v1/repos | 请求发送成功 |
| 2 | 验证响应状态码 | 200 (OK) |
| 3 | 验证响应体是 JSON 数组 | 数组包含仓库对象 |

### 验证点

- 响应状态码为 200
- 响应体是数组类型
- 数组包含预期的仓库记录

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_repos_api.py::test_real_api_list_repositories
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-003-001

### 关联需求

FR-001 (Register Repository)

### 测试目标

验证空 URL 和空名称被正确拒绝，返回 422 验证错误

### 前置条件

- 无

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | -------------- | ---------------- |
| 1 | POST with empty URL "" | 响应状态码 422 |
| 2 | POST with empty name "" | 响应状态码 422 |
| 3 | POST without URL field | 响应状态码 422 |
| 4 | POST with invalid URL scheme (ftp://) | 响应状态码 422 |

### 验证点

- 所有验证错误返回 422
- 错误消息指示 URL 或名称验证失败

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_repos_api.py::test_api_create_repo_empty_url_returns_422, test_api_create_repo_empty_name_returns_422
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-003-001 | FR-001 | Valid repository registration returns 201 | test_real_api_register_repository | Real | PASS |
| ST-FUNC-003-002 | FR-001 | Duplicate URL returns 409 | test_real_api_duplicate_url_returns_409 | Real | PASS |
| ST-FUNC-003-003 | FR-001 | List repositories returns 200 | test_real_api_list_repositories | Real | PASS |
| ST-BNDRY-003-001 | FR-001 | Empty URL/name validation returns 422 | test_api_create_repo_empty_url_returns_422 | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 4 |
| Passed | 4 |
| Failed | 0 |
| Pending | 0 |
