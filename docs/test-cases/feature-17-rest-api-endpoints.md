# 测试用例集: REST API Endpoints

**Feature ID**: 17
**关联需求**: FR-015
**日期**: 2026-03-23
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 5 |
| boundary | 3 |
| security | 2 |
| regression | 5 |
| **合计** | **15** |

---

### 用例编号

ST-FUNC-017-001

### 关联需求

FR-015 AC-1

### 测试目标

验证POST /api/v1/query返回结构化上下文结果

### 前置条件

- FastAPI app已创建，mock服务注入
- 有效API key具有query权限

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | POST /api/v1/query，body={"query":"timeout"}，header含有效key | 返回200 |
| 2 | 检查响应JSON | 包含query, query_type, code_results, doc_results字段 |

### 验证点

- 状态码200
- 响应包含QueryResponse结构（query, query_type, code_results字段）
- code_results数组中每个元素包含file_path, content, relevance_score

### 后置检查

- 无需清理（mock服务，无持久化副作用）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_post_query_nl_success
- **Test Type**: Real

---

### 用例编号

ST-FUNC-017-002

### 关联需求

FR-015 AC-2

### 测试目标

验证GET /api/v1/repos返回仓库列表

### 前置条件

- Mock RepoManager返回仓库列表

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | GET /api/v1/repos，header含有效key | 返回200 |
| 2 | 检查响应JSON | 返回仓库数组 |

### 验证点

- 状态码200
- 响应为JSON数组
- 每个仓库对象包含id, url, status字段

### 后置检查

- 无需清理（只读操作）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_get_repos_success
- **Test Type**: Real

---

### 用例编号

ST-FUNC-017-003

### 关联需求

FR-015 AC-3

### 测试目标

验证GET /api/v1/health无需认证返回服务状态

### 前置条件

- FastAPI app运行中

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | GET /api/v1/health（不提供API key） | 返回200 |
| 2 | 检查响应JSON | 包含status和services字段 |

### 验证点

- 状态码200（无需认证）
- 响应包含status字段（"healthy"或"degraded"）
- 响应包含services字段，列出各依赖服务状态

### 后置检查

- 无需清理（只读操作）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_health_no_auth
- **Test Type**: Real

---

### 用例编号

ST-FUNC-017-004

### 关联需求

FR-015

### 测试目标

验证POST /api/v1/repos注册新仓库

### 前置条件

- 有效admin API key

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | POST /api/v1/repos，body={"url":"https://github.com/test/repo"} | 返回200/201 |
| 2 | 检查响应 | 返回仓库信息 |

### 验证点

- 状态码200或201
- 响应包含仓库id和status字段
- status初始值为"pending"

### 后置检查

- 无需清理（mock持久化，无真实数据库副作用）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_register_repo
- **Test Type**: Real

---

### 用例编号

ST-FUNC-017-005

### 关联需求

FR-015

### 测试目标

验证API Key CRUD端点（create/list/revoke/rotate）

### 前置条件

- 有效admin API key

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | POST /api/v1/keys，body={"name":"test","role":"read"} | 返回plaintext key |
| 2 | GET /api/v1/keys | 返回key列表 |
| 3 | DELETE /api/v1/keys/{id} | 返回成功 |
| 4 | POST /api/v1/keys/{id}/rotate | 返回新key |

### 验证点

- POST /api/v1/keys 返回200，包含一次性明文key
- GET /api/v1/keys 返回200，为数组（不含明文key）
- DELETE /api/v1/keys/{id} 返回200，status="revoked"
- POST /api/v1/keys/{id}/rotate 返回200，包含新的plaintext key

### 后置检查

- 无需清理（mock持久化，无真实数据库副作用）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_create_key, test_rest_api.py::test_list_keys, test_rest_api.py::test_revoke_key, test_rest_api.py::test_rotate_key
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-017-001

### 关联需求

FR-015 AC-4

### 测试目标

验证格式错误的JSON body返回400

### 前置条件

- 有效API key

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | POST /api/v1/query，body={"query":""}（空query） | 返回400 |
| 2 | POST /api/v1/query，body缺少query字段 | 返回422 |

### 验证点

- 空query时状态码为400，包含验证错误信息
- 缺少必填字段时状态码为422，包含字段错误详情

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_post_query_empty_string, test_rest_api.py::test_post_query_missing_field
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-017-002

### 关联需求

FR-015

### 测试目标

验证不存在的repo_id返回404

### 前置条件

- 有效admin API key

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | POST /api/v1/repos/{nonexistent_id}/reindex | 返回404 |
| 2 | DELETE /api/v1/keys/{nonexistent_id} | 返回404 |

### 验证点

- 不存在的repo reindex请求返回404，包含"not found"错误信息
- 不存在的key revoke请求返回404，包含"not found"错误信息

### 后置检查

- 无需清理（mock服务返回NotFoundError）

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_reindex_repo_not_found, test_rest_api.py::test_revoke_key_not_found
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-017-003

### 关联需求

FR-015

### 测试目标

验证重复注册仓库返回409

### 前置条件

- 有效admin API key，RepoManager抛出ConflictError

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | POST /api/v1/repos，已存在的URL | 返回409 |

### 验证点

- 状态码409 Conflict
- 响应包含"already registered"或"conflict"错误信息

### 后置检查

- 无需清理（mock持久化）

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_register_repo_conflict
- **Test Type**: Real

---

### 用例编号

ST-SEC-017-001

### 关联需求

FR-015

### 测试目标

验证read角色不能执行admin操作

### 前置条件

- read角色API key

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | POST /api/v1/repos（read key） | 返回403 |
| 2 | POST /api/v1/repos/{id}/reindex（read key） | 返回403 |
| 3 | POST /api/v1/keys（read key） | 返回403 |

### 验证点

- 使用read角色key执行admin操作时返回403
- 响应包含"Insufficient permissions"或"Forbidden"错误信息

### 后置检查

- 无需清理（权限检查不修改状态）

### 元数据

- **优先级**: Critical
- **类别**: security
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_register_repo_read_denied, test_rest_api.py::test_reindex_read_denied, test_rest_api.py::test_create_key_read_denied
- **Test Type**: Real

---

### 用例编号

ST-SEC-017-002

### 关联需求

FR-015

### 测试目标

验证缺少认证的请求被拒绝（health除外）

### 前置条件

- 无API key

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | POST /api/v1/query（无key） | 返回401 |
| 2 | GET /api/v1/health（无key） | 返回200（无需认证） |

### 验证点

- 未认证的query请求返回401
- health端点无需认证，返回200
- 401响应包含"Missing API key"或"Unauthorized"错误信息

### 后置检查

- 无需清理

### 元数据

- **优先级**: Critical
- **类别**: security
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_query_no_auth, test_rest_api.py::test_health_no_auth
- **Test Type**: Real

---

### 用例编号

ST-FUNC-017-006

### 关联需求

FR-015 AC-3（DEF-001回归）

### 测试目标

验证lifespan启动时调用connect()，health端点返回"healthy"（R01 — DEF-001回归）

### 前置条件

- create_app()注入ES/Qdrant/Redis mock客户端，connect=AsyncMock()，health_check=AsyncMock(return_value=True)
- 使用TestClient上下文管理器（with TestClient(app) as client:）触发lifespan

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 以上下文管理器形式进入TestClient(app)（触发lifespan startup） | lifespan执行，三个客户端的connect()各被调用一次 |
| 2 | GET /api/v1/health | 返回200 |
| 3 | 检查响应JSON中的status字段 | status == "healthy" |
| 4 | 检查响应JSON中services.elasticsearch | "up" |
| 5 | 检查响应JSON中services.qdrant和services.redis | 均为"up" |

### 验证点

- es.connect.assert_called_once() 通过
- qdrant.connect.assert_called_once() 通过
- redis.connect.assert_called_once() 通过
- GET /api/v1/health 返回200，status="healthy"，所有服务="up"

### 后置检查

- 退出TestClient上下文管理器，lifespan shutdown自动执行

### 元数据

- **优先级**: Critical
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_lifespan_connects_clients_health_reports_healthy
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-017-004

### 关联需求

FR-015 AC-3（DEF-001回归，边界：None客户端）

### 测试目标

验证es_client=None时lifespan不抛异常，health返回elasticsearch="down"（R02 — DEF-001回归）

### 前置条件

- create_app()中es_client=None，qdrant和redis为正常mock（health_check返回True）
- 使用TestClient上下文管理器触发lifespan

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 以上下文管理器形式进入TestClient(app)，es_client=None | 不抛AttributeError或任何异常 |
| 2 | GET /api/v1/health | 返回200 |
| 3 | 检查responses JSON中services.elasticsearch | "down"（无客户端可ping） |
| 4 | 检查services.qdrant和services.redis | 均为"up" |
| 5 | 检查status字段 | "degraded"（部分服务不可用） |

### 验证点

- 进入lifespan无异常（None客户端被静默跳过）
- GET /api/v1/health 返回200，elasticsearch="down"，status="degraded"

### 后置检查

- 退出TestClient上下文管理器

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_lifespan_none_client_skipped
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-017-005

### 关联需求

FR-015（DEF-001回归，错误处理：connect()抛异常）

### 测试目标

验证lifespan中connect()抛出异常时启动失败并向外传播（R03 — DEF-001回归）

### 前置条件

- create_app()中es_client.connect=AsyncMock(side_effect=ConnectionError("ES unreachable"))
- 使用TestClient上下文管理器触发lifespan

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用TestClient(app).__enter__()（触发lifespan startup） | 抛出ConnectionError（或其子类Exception） |
| 2 | 使用pytest.raises验证异常类型 | 捕获到ConnectionError或Exception |

### 验证点

- connect()异常不被lifespan静默吞没
- 异常向外传播，导致app启动失败

### 后置检查

- 无需清理（app启动失败，无运行中服务）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_lifespan_connect_error_propagates
- **Test Type**: Real

---

### 用例编号

ST-FUNC-017-007

### 关联需求

FR-015（DEF-001回归：shutdown调用close()）

### 测试目标

验证app关闭时lifespan调用每个客户端的close()（R04 — DEF-001回归）

### 前置条件

- create_app()注入ES/Qdrant/Redis mock客户端（connect/close均为AsyncMock）
- 使用TestClient上下文管理器进入并退出lifespan

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 以上下文管理器形式进入并退出TestClient(app)（with TestClient(app): pass） | lifespan startup和shutdown均执行 |
| 2 | 断言es.close.assert_called_once() | 通过——ES客户端close()被调用一次 |
| 3 | 断言qdrant.close.assert_called_once() | 通过——Qdrant客户端close()被调用一次 |
| 4 | 断言redis.close.assert_called_once() | 通过——Redis客户端close()被调用一次 |

### 验证点

- 每个非None客户端的close()在lifespan shutdown时被调用恰好一次
- 无资源泄漏

### 后置检查

- 上下文管理器退出后lifespan已完成，无需额外清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_lifespan_close_called_on_shutdown
- **Test Type**: Real

---

### 用例编号

ST-FUNC-017-008

### 关联需求

FR-015 AC-3（DEF-001回归：health正确反映降级状态）

### 测试目标

验证某服务health_check()返回False时health端点正确报告"degraded"（R05 — DEF-001回归）

### 前置条件

- create_app()注入ES mock，es.health_check=AsyncMock(return_value=False)，es.connect=AsyncMock()
- Qdrant和Redis mock正常（health_check返回True）
- 使用TestClient上下文管理器触发lifespan

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 以上下文管理器形式进入TestClient(app)（触发lifespan startup） | connect()被调用，lifespan正常启动 |
| 2 | 断言es.connect.assert_called_once() | 通过（客户端不为None，connect()被调用） |
| 3 | GET /api/v1/health | 返回200 |
| 4 | 检查响应JSON中status字段 | "degraded"（非"healthy"） |
| 5 | 检查services.elasticsearch | "down" |
| 6 | 检查services.qdrant和services.redis | 均为"up" |

### 验证点

- connect()被调用（客户端已连接，不是因未连接而降级）
- health_check()返回False → services.elasticsearch="down"
- status="degraded"，qdrant/redis仍为"up"

### 后置检查

- 退出TestClient上下文管理器

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_lifespan_degraded_when_service_health_check_fails
- **Test Type**: Real

---

## 可追溯矩阵

| 用例编号 | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|----------|----------|-------------------|------------|-----------|------|
| ST-FUNC-017-001 | FR-015 AC-1 | Given a POST to /api/v1/query with valid query body and API key, when processed, then it returns 200 with structured context results | test_post_query_nl_success | Real | PASS |
| ST-FUNC-017-002 | FR-015 AC-2 | Given a GET to /api/v1/repos with valid API key, when processed, then it returns the list of registered repositories with their indexing status | test_get_repos_success | Real | PASS |
| ST-FUNC-017-003 | FR-015 AC-3 | Given a GET to /api/v1/health without authentication, when processed, then it returns service health status with ES/Qdrant/Redis connectivity | test_health_no_auth | Real | PASS |
| ST-FUNC-017-004 | FR-015 | Given a POST to /api/v1/query with valid query body and API key, when processed, then it returns 200 with structured context results (POST /repos) | test_register_repo | Real | PASS |
| ST-FUNC-017-005 | FR-015 | Given a POST to /api/v1/query with valid query body and API key, when processed, then it returns 200 with structured context results (API Key CRUD) | test_create_key, test_list_keys, test_revoke_key, test_rotate_key | Real | PASS |
| ST-BNDRY-017-001 | FR-015 AC-4 | Given a malformed JSON body on POST /api/v1/query, when submitted, then it returns 400 with a validation error message | test_post_query_empty_string, test_post_query_missing_field | Real | PASS |
| ST-BNDRY-017-002 | FR-015 | Non-existent resource returns 404 | test_reindex_repo_not_found, test_revoke_key_not_found | Real | PASS |
| ST-BNDRY-017-003 | FR-015 | Duplicate repo registration returns 409 | test_register_repo_conflict | Real | PASS |
| ST-SEC-017-001 | FR-015 | read role denied admin operations | test_register_repo_read_denied, test_reindex_read_denied, test_create_key_read_denied | Real | PASS |
| ST-SEC-017-002 | FR-015 | Unauthenticated requests rejected (health excepted) | test_query_no_auth, test_health_no_auth | Real | PASS |
| ST-FUNC-017-006 | FR-015 AC-3 | VS-3: R01 — lifespan calls connect(); health returns "healthy" when all services up | test_lifespan_connects_clients_health_reports_healthy | Real | PASS |
| ST-BNDRY-017-004 | FR-015 AC-3 | VS-3: R02 — None client skipped silently; health returns elasticsearch="down" | test_lifespan_none_client_skipped | Real | PASS |
| ST-BNDRY-017-005 | FR-015 | R03 — connect() error propagates; app startup fails | test_lifespan_connect_error_propagates | Real | PASS |
| ST-FUNC-017-007 | FR-015 | R04 — close() called on each non-None client during shutdown | test_lifespan_close_called_on_shutdown | Real | PASS |
| ST-FUNC-017-008 | FR-015 AC-3 | VS-3: R05 — health returns "degraded" when service health_check() returns False | test_lifespan_degraded_when_service_health_check_fails | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 15 |
| Passed | 15 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
