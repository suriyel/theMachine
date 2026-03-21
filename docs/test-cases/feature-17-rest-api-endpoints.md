# 测试用例集: REST API Endpoints

**Feature ID**: 17
**关联需求**: FR-015
**日期**: 2026-03-22
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 5 |
| boundary | 3 |
| security | 2 |
| **合计** | **10** |

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
- 响应包含QueryResponse结构

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_post_query_valid
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

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_list_repos
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

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_post_query_empty, test_rest_api.py::test_post_query_missing_field
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

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_reindex_not_found, test_rest_api.py::test_revoke_key_not_found
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

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_register_duplicate_repo
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

### 元数据

- **优先级**: Critical
- **类别**: security
- **已自动化**: Yes
- **测试引用**: test_rest_api.py::test_query_no_auth, test_rest_api.py::test_health_no_auth
- **Test Type**: Real

---

## 可追溯矩阵

| 用例编号 | 关联需求 | verification_step | 自动化测试 | 结果 |
|----------|----------|-------------------|------------|------|
| ST-FUNC-017-001 | FR-015 AC-1 | VS-1: POST /query返回200结构化结果 | test_post_query_valid | PASS |
| ST-FUNC-017-002 | FR-015 AC-2 | VS-2: GET /repos返回仓库列表 | test_list_repos | PASS |
| ST-FUNC-017-003 | FR-015 AC-3 | VS-3: GET /health无需认证 | test_health_no_auth | PASS |
| ST-FUNC-017-004 | FR-015 | POST /repos注册仓库 | test_register_repo | PASS |
| ST-FUNC-017-005 | FR-015 | Key CRUD端点 | test_create_key, test_list_keys | PASS |
| ST-BNDRY-017-001 | FR-015 AC-4 | VS-4: 格式错误body返回400 | test_post_query_empty | PASS |
| ST-BNDRY-017-002 | FR-015 | 不存在资源返回404 | test_reindex_not_found | PASS |
| ST-BNDRY-017-003 | FR-015 | 重复注册返回409 | test_register_duplicate_repo | PASS |
| ST-SEC-017-001 | FR-015 | read角色禁止admin操作 | test_register_repo_read_denied | PASS |
| ST-SEC-017-002 | FR-015 | 无认证请求被拒绝 | test_query_no_auth | PASS |

## Real Test Case Execution Summary

| 指标 | 数值 |
|------|------|
| Real用例总数 | 10 |
| 通过 | 10 |
| 失败 | 0 |
| 待执行 | 0 |
