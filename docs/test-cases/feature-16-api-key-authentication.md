# 测试用例集: API Key Authentication (FR-018)

**Feature ID**: 16
**关联需求**: FR-018 (API Key Authentication)
**日期**: 2026-03-15
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 4 |
| boundary | 2 |
| security | 1 |
| **合计** | **7** |

---

### 用例编号

ST-FUNC-016-001

### 关联需求

FR-018 (API Key Authentication) — 验证有效 API key 的请求可以继续处理

### 测试目标

验证带有有效 API key 的请求能够通过认证并继续到处理流程

### 前置条件

- PostgreSQL 数据库运行且可访问
- APIKey 表中存在一条 ACTIVE 状态的记录
- 查询服务已启动

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 启动查询服务 | 服务在端口 8000 启动 |
| 2 | 准备有效 API key (从数据库获取或创建测试 key) | Key 可用 |
| 3 | 发送 GET /api/v1/health 请求 (无 API key) | 返回 401 Unauthorized |
| 4 | 创建测试 API key 并插入数据库 (ACTIVE 状态) | Key 插入成功 |
| 5 | 发送 POST /api/v1/query 请求，带 X-API-Key: {valid_key} 头 | 返回 200 OK |

### 验证点

- Step 3: 响应状态码为 401
- Step 5: 响应状态码为 200，请求被接受处理

### 后置检查

- 清理测试创建的 API key 记录

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_auth.py::TestAuthMiddlewareRequireAuth::test_require_auth_valid_key_returns_record
- **Test Type**: Real

---

### 用例编号

ST-FUNC-016-002

### 关联需求

FR-018 (API Key Authentication) — 无效 API key 返回 401

### 测试目标

验证带有无效 API key 的请求返回 401 Unauthorized

### 前置条件

- PostgreSQL 数据库运行且可访问
- 查询服务已启动

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 POST /api/v1/query 请求，带 X-API-Key: invalid-key-12345 头 | 返回 401 Unauthorized |

### 验证点

- 响应状态码为 401
- 响应 body 包含 "Invalid API key" 消息

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_auth.py::TestAuthMiddlewareRequireAuth::test_require_auth_invalid_key_raises_401
- **Test Type**: Real

---

### 用例编号

ST-FUNC-016-003

### 关联需求

FR-018 (API Key Authentication) — 缺少 API key 返回 401

### 测试目标

验证缺少 API key 的请求返回 401 Unauthorized

### 前置条件

- PostgreSQL 数据库运行且可访问
- 查询服务已启动

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 POST /api/v1/query 请求，不带 X-API-Key 头 | 返回 401 Unauthorized |

### 验证点

- 响应状态码为 401
- 响应 body 包含 "Missing API key" 消息

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_auth.py::TestAuthMiddlewareRequireAuth::test_require_auth_missing_key_raises_401
- **Test Type**: Real

---

### 用例编号

ST-FUNC-016-004

### 关联需求

FR-018 (API Key Authentication) — 已撤销的 API key 返回 401

### 测试目标

验证带有已撤销 API key 的请求返回 401 Unauthorized

### 前置条件

- PostgreSQL 数据库运行且可访问
- 查询服务已启动

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建测试 API key 并插入数据库 (REVOKED 状态) | Key 插入成功 |
| 2 | 发送 POST /api/v1/query 请求，带 X-API-Key: {revoked_key} 头 | 返回 401 Unauthorized |

### 验证点

- 响应状态码为 401
- 响应 body 包含 "Invalid API key" 消息

### 后置检查

- 清理测试创建的 API key 记录

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_auth.py::TestAuthMiddlewareVerifyApiKey::test_verify_api_key_revoked_returns_none
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-016-001

### 关联需求

FR-018 (API Key Authentication) — 边界测试：空字符串 API key

### 测试目标

验证空字符串 API key 被正确拒绝

### 前置条件

- PostgreSQL 数据库运行且可访问
- 查询服务已启动

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 POST /api/v1/query 请求，带 X-API-Key: (空字符串) 头 | 返回 401 Unauthorized |

### 验证点

- 响应状态码为 401

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: N/A
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-016-002

### 关联需求

FR-018 (API Key Authentication) — 边界测试：仅空格 API key

### 测试目标

验证仅包含空格的 API key 被正确拒绝

### 前置条件

- PostgreSQL 数据库运行且可访问
- 查询服务已启动

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 POST /api/v1/query 请求，带 X-API-Key: '   ' (空格) 头 | 返回 401 Unauthorized |

### 验证点

- 响应状态码为 401

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: N/A
- **Test Type**: Real

---

### 用例编号

ST-SEC-016-001

### 关联需求

FR-018 (API Key Authentication) — 安全测试：SQL 注入尝试

### 测试目标

验证恶意构造的 API key 被正确处理（不导致 SQL 注入）

### 前置条件

- PostgreSQL 数据库运行且可访问
- 查询服务已启动

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 POST /api/v1/query 请求，带 X-API-Key: ' OR '1'='1 头 | 返回 401 Unauthorized 或 500 Internal Server Error (不泄露敏感信息) |

### 验证点

- 响应状态码不是 200
- 响应不包含 SQL 错误详情

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: security
- **已自动化**: Yes
- **测试引用**: N/A
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-016-001 | FR-018 | Given request with valid API key in X-API-Key header, when auth middleware checks, then request proceeds to handler | tests/test_auth.py::test_require_auth_valid_key_returns_record | Real | PENDING |
| ST-FUNC-016-002 | FR-018 | Given request with invalid API key, when auth middleware checks, then 401 Unauthorized is returned | tests/test_auth.py::test_require_auth_invalid_key_raises_401 | Real | PENDING |
| ST-FUNC-016-003 | FR-018 | Given request with missing API key header, when auth middleware checks, then 401 Unauthorized is returned | tests/test_auth.py::test_require_auth_missing_key_raises_401 | Real | PENDING |
| ST-FUNC-016-004 | FR-018 | Given request with revoked API key, when auth middleware checks, then 401 Unauthorized is returned | tests/test_auth.py::test_verify_api_key_revoked_returns_none | Real | PENDING |
| ST-BNDRY-016-001 | FR-018 | Boundary: empty string API key | N/A | Real | PENDING |
| ST-BNDRY-016-002 | FR-018 | Boundary: whitespace-only API key | N/A | Real | PENDING |
| ST-SEC-016-001 | FR-018 | Security: SQL injection attempt | N/A | Real | PENDING |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 7 |
| Passed | N |
| Failed | N |
| Pending | 7 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
