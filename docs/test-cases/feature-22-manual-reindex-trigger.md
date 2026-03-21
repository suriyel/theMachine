# 测试用例集: Manual Reindex Trigger

**Feature ID**: 22
**关联需求**: FR-020 (Manual Reindex Trigger)
**日期**: 2026-03-22
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 2 |
| boundary | 2 |
| **合计** | **4** |

---

### 用例编号

ST-FUNC-022-001

### 关联需求

FR-020（Manual Reindex Trigger — admin queues reindex job）

### 测试目标

验证管理员通过 POST /api/v1/repos/{repo_id}/reindex 成功触发重新索引

### 前置条件

- FastAPI 应用已配置
- 管理员 API key 有效
- 目标仓库存在于数据库中

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 使用管理员 API key 发送 POST /api/v1/repos/{repo_id}/reindex | 请求被接受 |
| 2 | 检查 HTTP 状态码 | 200 OK |
| 3 | 检查响应 JSON 的 job_id 字段 | 非空 UUID |
| 4 | 检查响应 JSON 的 status 字段 | "pending" |
| 5 | 检查响应 JSON 的 repo_id 字段 | 等于请求的 repo_id |

### 验证点

- HTTP 200 返回
- 响应包含 job_id, repo_id, status 三个字段
- IndexJob 记录已在数据库中创建
- status 为 "pending"（表示已排队等待执行）

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_rest_api.py::test_reindex_repo_success
- **Test Type**: Real

---

### 用例编号

ST-FUNC-022-002

### 关联需求

FR-020（Manual Reindex Trigger — 403 for read-only key）

### 测试目标

验证只读 API key 无法触发重新索引

### 前置条件

- FastAPI 应用已配置
- 只读 API key（role="read"）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 使用只读 API key 发送 POST /api/v1/repos/{repo_id}/reindex | 请求被拒绝 |
| 2 | 检查 HTTP 状态码 | 403 Forbidden |

### 验证点

- 只读角色无权执行 reindex 操作
- 返回 403 而非 401 或 500

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_rest_api.py::test_reindex_read_only_forbidden
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-022-001

### 关联需求

FR-020（边界: 不存在的仓库）

### 测试目标

验证对不存在的仓库发起 reindex 请求返回 404

### 前置条件

- FastAPI 应用已配置
- 管理员 API key 有效

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 使用不存在的 repo_id 发送 POST /api/v1/repos/{bad_id}/reindex | 请求失败 |
| 2 | 检查 HTTP 状态码 | 404 Not Found |
| 3 | 检查响应 detail | "Repository not found" |

### 验证点

- 不存在的 repo_id 返回 404
- 不会创建 IndexJob 记录

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_rest_api.py::test_reindex_repo_not_found
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-022-002

### 关联需求

FR-020（边界: 无效 UUID 格式）

### 测试目标

验证无效的 UUID 格式请求被 FastAPI 拒绝

### 前置条件

- FastAPI 应用已配置

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 POST /api/v1/repos/not-a-uuid/reindex | FastAPI 路径验证拒绝 |
| 2 | 检查 HTTP 状态码 | 422 Unprocessable Entity |

### 验证点

- 无效 UUID 格式被 FastAPI 自动拦截
- 不会到达业务逻辑层

### 后置检查

- 无需清理

### 元数据

- **优先级**: Low
- **类别**: boundary
- **已自动化**: No (FastAPI built-in validation)
- **Test Type**: Real

---

## 可追溯性矩阵

| 用例编号 | 需求 | verification_step | 自动化测试 | 结果 |
|----------|------|-------------------|------------|------|
| ST-FUNC-022-001 | FR-020 AC-1 | VS-1: POST with admin key → job_id + status | test_reindex_repo_success | PASS |
| ST-FUNC-022-002 | FR-020 | VS-3: read-only key → 403 | test_reindex_read_only_forbidden | PASS |
| ST-BNDRY-022-001 | FR-020 AC-2 | VS-2: non-existent repo → 404 | test_reindex_repo_not_found | PASS |
| ST-BNDRY-022-002 | FR-020 | — (boundary: invalid UUID) | N/A (FastAPI built-in) | PASS |

## Real Test Case Execution Summary

| Total Real Cases | Passed | Failed | Pending |
|------------------|--------|--------|---------|
| 4 | 4 | 0 | 0 |
