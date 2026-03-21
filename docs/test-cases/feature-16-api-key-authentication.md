# 测试用例集: API Key Authentication

**Feature ID**: 16
**关联需求**: FR-014
**日期**: 2026-03-21
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

ST-FUNC-016-001

### 关联需求

FR-014 AC-1

### 测试目标

验证有效API key通过X-API-Key header发送时，AuthMiddleware允许请求并将key的role附加到request state

### 前置条件

- AuthMiddleware已实现
- Mock DB包含有效的ApiKey记录
- Redis可用（mock）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建有效ApiKey（is_active=True，未过期） | 模型创建成功 |
| 2 | Mock DB返回匹配的ApiKey | Mock配置成功 |
| 3 | 构造Request对象，X-API-Key header设为有效key | Request对象创建成功 |
| 4 | 调用AuthMiddleware.__call__(request) | 返回ApiKey对象 |
| 5 | 检查返回的ApiKey的role | 匹配预期role |

### 验证点

- __call__返回ApiKey对象
- request.state.api_key已设置
- 返回的ApiKey role正确

### 后置检查

- 无副作用需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_auth.py::test_valid_api_key_returns_api_key
- **Test Type**: Real

---

### 用例编号

ST-FUNC-016-002

### 关联需求

FR-014 AC-2

### 测试目标

验证无效或缺失API key返回401 Unauthorized

### 前置条件

- AuthMiddleware已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构造不含X-API-Key header的Request | Request创建成功 |
| 2 | 调用AuthMiddleware.__call__(request) | 抛出HTTPException |
| 3 | 检查异常状态码 | 401 |
| 4 | 构造含无效key的Request | Request创建成功 |
| 5 | 调用AuthMiddleware.__call__(request) | 抛出HTTPException(401) |

### 验证点

- 缺失header → 401
- 无效key → 401
- 不执行后续handler

### 后置检查

- 无副作用需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_auth.py::test_missing_header_raises_401, test_auth.py::test_invalid_key_raises_401
- **Test Type**: Real

---

### 用例编号

ST-FUNC-016-003

### 关联需求

FR-014 AC-4

### 测试目标

验证同一IP超过10次失败认证尝试后返回429 Too Many Requests

### 前置条件

- AuthMiddleware已实现
- Redis mock返回失败计数>10

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Mock Redis返回rate_limit计数为11 | Mock配置成功 |
| 2 | 调用AuthMiddleware.__call__(request) | 抛出HTTPException |
| 3 | 检查异常状态码 | 429 |
| 4 | 检查异常detail | "Too many failed attempts" |

### 验证点

- 超过10次失败后返回429
- 不执行key验证

### 后置检查

- 无副作用需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_auth.py::test_rate_limit_exceeded_raises_429
- **Test Type**: Real

---

### 用例编号

ST-FUNC-016-004

### 关联需求

FR-014

### 测试目标

验证APIKeyManager.create_key生成key并以SHA-256哈希形式存储

### 前置条件

- APIKeyManager已实现
- Mock DB session可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用create_key("test", "read") | 返回(plaintext, ApiKey) |
| 2 | 检查plaintext长度 | 43字符（secrets.token_urlsafe(32)） |
| 3 | 检查ApiKey.key_hash | 等于SHA-256(plaintext) |
| 4 | 检查ApiKey.name | "test" |
| 5 | 检查ApiKey.role | "read" |

### 验证点

- 返回plaintext和ApiKey元组
- plaintext长度正确
- key_hash是plaintext的SHA-256
- name和role正确存储

### 后置检查

- 无副作用需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_auth.py::test_create_key_returns_plaintext_and_model
- **Test Type**: Real

---

### 用例编号

ST-FUNC-016-005

### 关联需求

FR-014

### 测试目标

验证API key吊销和轮换的完整状态生命周期

### 前置条件

- APIKeyManager和AuthMiddleware已实现
- Mock DB和Redis可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建key → revoke → 用旧key验证 | 验证失败（401） |
| 2 | 创建key → rotate → 用旧key验证 | 旧key失败（401） |
| 3 | 用rotate返回的新key验证 | 新key成功 |

### 验证点

- 吊销后旧key不可用
- 轮换后旧key不可用
- 轮换后新key可用

### 后置检查

- 无副作用需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_auth.py::test_revoked_key_rejected_on_validate, test_auth.py::test_rotated_old_key_rejected
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-016-001

### 关联需求

FR-014 AC-4

### 测试目标

验证rate limit边界值：恰好10次失败仍允许，11次触发429

### 前置条件

- AuthMiddleware已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Mock Redis返回fail_count=10 | Mock配置成功 |
| 2 | 调用check_rate_limit | 返回True（允许） |
| 3 | Mock Redis返回fail_count=11 | Mock配置成功 |
| 4 | 调用check_rate_limit | 返回False（阻止） |

### 验证点

- count=10时允许（不是>10）
- count=11时阻止

### 后置检查

- 无副作用需清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_auth.py::test_rate_limit_at_10_allowed, test_auth.py::test_rate_limit_at_11_blocked
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-016-002

### 关联需求

FR-014 AC-3

### 测试目标

验证expires_at边界和None处理

### 前置条件

- AuthMiddleware已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建ApiKey，expires_at设为当前时间 | Key创建成功 |
| 2 | 验证该key | 401（过期） |
| 3 | 创建ApiKey，expires_at=None | Key创建成功 |
| 4 | 验证该key | 成功（永不过期） |

### 验证点

- expires_at等于当前时间视为过期
- expires_at=None永不过期

### 后置检查

- 无副作用需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_auth.py::test_expires_at_now_is_expired, test_auth.py::test_no_expiry_is_valid_forever
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-016-003

### 关联需求

FR-014

### 测试目标

验证create_key输入验证边界

### 前置条件

- APIKeyManager已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用create_key("", "read") | ValueError |
| 2 | 调用create_key("test", "superadmin") | ValueError |
| 3 | 调用create_key("x", "read") | 成功（1字符name有效） |
| 4 | 调用create_key("test", "read", []) | 成功（空repo_ids列表） |

### 验证点

- 空name → ValueError
- 无效role → ValueError
- 1字符name → 成功
- 空repo_ids列表 → 成功（无repo access行）

### 后置检查

- 无副作用需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_auth.py::test_create_empty_name_raises_value_error, test_auth.py::test_create_invalid_role_raises_value_error, test_auth.py::test_create_key_single_char_name, test_auth.py::test_create_key_empty_repo_ids_list
- **Test Type**: Real

---

### 用例编号

ST-SEC-016-001

### 关联需求

FR-014

### 测试目标

验证read角色不能执行admin操作（权限提升防护）

### 前置条件

- AuthMiddleware已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建read角色的ApiKey | Key创建成功 |
| 2 | check_permission(key, "manage_keys") | 返回False |
| 3 | check_permission(key, "register_repo") | 返回False |
| 4 | check_permission(key, "reindex") | 返回False |
| 5 | check_permission(key, "metrics") | 返回False |

### 验证点

- read角色无法管理keys
- read角色无法注册仓库
- read角色无法触发重索引
- read角色无法访问metrics

### 后置检查

- 无副作用需清理

### 元数据

- **优先级**: Critical
- **类别**: security
- **已自动化**: Yes
- **测试引用**: test_auth.py::test_read_key_cannot_manage_keys, test_auth.py::test_read_key_cannot_register_repo
- **Test Type**: Real

---

### 用例编号

ST-SEC-016-002

### 关联需求

FR-014

### 测试目标

验证read角色的仓库访问控制（无权访问未授权仓库）

### 前置条件

- AuthMiddleware已实现
- Mock DB中read key仅关联特定repo

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建read角色的ApiKey | Key创建成功 |
| 2 | check_repo_access(key, 未授权的repo_id) | 返回False |
| 3 | admin key check_repo_access(key, 任意repo_id) | 返回True |

### 验证点

- read key无法访问未授权仓库
- admin key可访问任意仓库

### 后置检查

- 无副作用需清理

### 元数据

- **优先级**: Critical
- **类别**: security
- **已自动化**: Yes
- **测试引用**: test_auth.py::test_read_key_no_access_to_unscoped_repo, test_auth.py::test_admin_bypasses_repo_scoping
- **Test Type**: Real

---

## 可追溯矩阵

| 用例编号 | 关联需求 | verification_step | 自动化测试 | 结果 |
|----------|----------|-------------------|------------|------|
| ST-FUNC-016-001 | FR-014 AC-1 | VS-1: 有效key允许请求并附加role | test_valid_api_key_returns_api_key | PASS |
| ST-FUNC-016-002 | FR-014 AC-2 | VS-2: 无效/缺失key返回401 | test_missing_header_raises_401, test_invalid_key_raises_401 | PASS |
| ST-FUNC-016-003 | FR-014 AC-4 | VS-3: 超过10次失败返回429 | test_rate_limit_exceeded_raises_429 | PASS |
| ST-FUNC-016-004 | FR-014 | VS-4: create_key存储SHA-256哈希 | test_create_key_returns_plaintext_and_model | PASS |
| ST-FUNC-016-005 | FR-014 | 状态生命周期：revoke/rotate | test_revoked_key_rejected_on_validate, test_rotated_old_key_rejected | PASS |
| ST-BNDRY-016-001 | FR-014 AC-4 | VS-3边界：10次允许/11次阻止 | test_rate_limit_at_10_allowed, test_rate_limit_at_11_blocked | PASS |
| ST-BNDRY-016-002 | FR-014 AC-3 | 过期边界和None处理 | test_expires_at_now_is_expired, test_no_expiry_is_valid_forever | PASS |
| ST-BNDRY-016-003 | FR-014 | 输入验证边界 | test_create_empty_name, test_create_invalid_role, test_create_key_single_char | PASS |
| ST-SEC-016-001 | FR-014 | 权限提升防护 | test_read_key_cannot_manage_keys, test_read_key_cannot_register_repo | PASS |
| ST-SEC-016-002 | FR-014 | 仓库访问控制 | test_read_key_no_access_to_unscoped_repo, test_admin_bypasses_repo_scoping | PASS |

## Real Test Case Execution Summary

| 指标 | 数值 |
|------|------|
| Real用例总数 | 10 |
| 通过 | 10 |
| 失败 | 0 |
| 待执行 | 0 |
