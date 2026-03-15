# 测试用例集: REST API Endpoints

**Feature ID**: 17
**关联需求**: FR-005, FR-006, FR-007, FR-012, FR-018, NFR-008
**日期**: 2026-03-16
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 4 |
| boundary | 4 |
| security | 0 |
| **合计** | **8** |

---

### 用例编号

ST-FUNC-017-001

### 关联需求

FR-012 (Context Response Builder)

### 测试目标

验证 POST /api/v1/query 端点在使用有效 API 密钥时返回 200 和 QueryResponse

### 前置条件

- Query Service 运行在 http://localhost:8000
- 数据库中存在有效的 API 密钥

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 启动 Query Service | 服务启动成功 |
| 2 | 发送 POST 请求到 /api/v1/query，带有效 X-API-Key 头和 JSON body | HTTP 200 |
| 3 | 验证响应体包含 results 和 query_time_ms 字段 | 响应格式正确 |

### 验证点

- HTTP 状态码为 200
- 响应体为有效的 JSON
- 响应包含 results 数组字段
- 响应包含 query_time_ms 数值字段

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_query_api.py::test_post_query_with_valid_api_key_returns_200
- **Test Type**: Real

---

### 用例编号

ST-FUNC-017-002

### 关联需求

FR-012 (Context Response Builder)

### 测试目标

验证 GET /api/v1/query 端点在使用有效 API 密钥时返回 200 和 QueryResponse

### 前置条件

- Query Service 运行在 http://localhost:8000

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 GET 请求到 /api/v1/query?query=test，带有效 X-API-Key 头 | HTTP 200 |
| 2 | 验证响应体包含 results 和 query_time_ms 字段 | 响应格式正确 |

### 验证点

- HTTP 状态码为 200
- 响应体为有效的 JSON
- 响应包含 results 数组字段

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_query_api.py::test_get_query_with_valid_api_key_returns_200
- **Test Type**: Real

---

### 用例编号

ST-FUNC-017-003

### 关联需求

NFR-005 (Service Availability)

### 测试目标

验证 GET /api/v1/health 端点无需认证即可访问

### 前置条件

- Query Service 运行在 http://localhost:8000

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 GET 请求到 /api/v1/health，不需要任何认证头 | HTTP 200 |
| 2 | 验证响应体为 {"status": "healthy"} | 响应正确 |

### 验证点

- HTTP 状态码为 200
- 响应体包含 status 字段且值为 "healthy"

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_query_api.py::test_health_endpoint_no_auth_required
- **Test Type**: Real

---

### 用例编号

ST-FUNC-017-004

### 关联需求

NFR-008 (Metrics Endpoint)

### 测试目标

验证 GET /api/v1/metrics 端点无需认证即可访问并返回 Prometheus 格式

### 前置条件

- Query Service 运行在 http://localhost:8000

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 GET 请求到 /api/v1/metrics，不需要任何认证头 | HTTP 200 |
| 2 | 验证响应内容类型为 text/plain; version=0.0.4 | 内容类型正确 |
| 3 | 验证响应包含 "# HELP" 或 "# TYPE" (Prometheus 格式) | 格式正确 |

### 验证点

- HTTP 状态码为 200
- Content-Type 为 text/plain
- 响应包含 Prometheus 格式指标

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_query_api.py::test_metrics_endpoint_no_auth_required
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-017-001

### 关联需求

FR-005 (Query Handler - Natural Language)

### 测试目标

验证 POST /api/v1/query 端点在请求体为空时返回 422

### 前置条件

- Query Service 运行在 http://localhost:8000

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 POST 请求到 /api/v1/query，带有效 X-API-Key 头，body 为 {"query": ""} | HTTP 422 |

### 验证点

- HTTP 状态码为 422
- 响应包含验证错误信息

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_query_api.py::test_post_query_with_empty_query_returns_422
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-017-002

### 关联需求

FR-005 (Query Handler - Natural Language)

### 测试目标

验证 GET /api/v1/query 端点在缺少 query 参数时返回 422

### 前置条件

- Query Service 运行在 http://localhost:8000

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 GET 请求到 /api/v1/query，不带 query 参数，带有效 X-API-Key 头 | HTTP 422 |

### 验证点

- HTTP 状态码为 422

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_query_api.py::test_get_query_with_missing_query_param_returns_422
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-017-003

### 关联需求

FR-018 (API Key Authentication)

### 测试目标

验证 POST /api/v1/query 端点在提供无效 API 密钥时返回 401

### 前置条件

- Query Service 运行在 http://localhost:8000

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 POST 请求到 /api/v1/query，带无效 X-API-Key 头 "invalid-key" | HTTP 401 |

### 验证点

- HTTP 状态码为 401

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_query_api.py::test_post_query_with_invalid_api_key_returns_401
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-017-004

### 关联需求

FR-018 (API Key Authentication)

### 测试目标

验证 POST /api/v1/query 端点在缺少 API 密钥时返回 401

### 前置条件

- Query Service 运行在 http://localhost:8000

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 POST 请求到 /api/v1/query，不带 X-API-Key 头 | HTTP 401 |

### 验证点

- HTTP 状态码为 401

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_query_api.py::test_post_query_without_api_key_returns_401
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-017-001 | FR-012 | POST /api/v1/query with valid API key | test_post_query_with_valid_api_key_returns_200 | Real | PASS |
| ST-FUNC-017-002 | FR-012 | GET /api/v1/query with valid API key | test_get_query_with_valid_api_key_returns_200 | Real | PASS |
| ST-FUNC-017-003 | NFR-005 | GET /api/v1/health (no auth) | test_health_endpoint_no_auth_required | Real | PASS |
| ST-FUNC-017-004 | NFR-008 | GET /api/v1/metrics (no auth) | test_metrics_endpoint_no_auth_required | Real | PASS |
| ST-BNDRY-017-001 | FR-005 | POST with empty query | test_post_query_with_empty_query_returns_422 | Real | PASS |
| ST-BNDRY-017-002 | FR-005 | GET without query param | test_get_query_with_missing_query_param_returns_422 | Real | PASS |
| ST-BNDRY-017-003 | FR-018 | POST with invalid API key | test_post_query_with_invalid_api_key_returns_401 | Real | PASS |
| ST-BNDRY-017-004 | FR-018 | POST without API key | test_post_query_without_api_key_returns_401 | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 8 |
| Passed | 8 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
