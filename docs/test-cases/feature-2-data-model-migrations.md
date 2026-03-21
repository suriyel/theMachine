# 测试用例集: Data Model & Migrations

**Feature ID**: 2
**关联需求**: FR-001 (Repository Registration — data model context)
**日期**: 2026-03-21
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 3 |
| boundary | 2 |
| **合计** | **5** |

---

### 用例编号

ST-FUNC-002-001

### 关联需求

FR-001（Repository Registration — data model layer）

### 测试目标

验证 Alembic 迁移在测试数据库上创建所有 5 张核心表，且列和约束正确。

### 前置条件

- 项目已安装（`pip install -e .[dev]`）
- SQLite 异步引擎可用（aiosqlite 已安装）
- Base.metadata 包含所有模型

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 从 `src.shared.models.base` 导入 Base | 导入成功 |
| 2 | 创建 in-memory SQLite 异步引擎并执行 `Base.metadata.create_all` | 无异常，所有表创建成功 |
| 3 | 通过 `inspect(conn).get_table_names()` 获取所有表名 | 返回集合包含 `repository`, `index_job`, `api_key`, `api_key_repo_access`, `query_log` |
| 4 | 检查 `repository` 表的列 | 包含 id, name, url, default_branch, indexed_branch, clone_path, status, last_indexed_at, created_at |
| 5 | 检查 `api_key_repo_access` 表的主键约束 | 复合主键为 (api_key_id, repo_id) |

### 验证点

- 5 张表全部存在且名称正确
- repository 表有 9 列，类型匹配设计文档 §5
- api_key_repo_access 使用复合主键

### 后置检查

- 执行 `Base.metadata.drop_all` 清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_feature_2_models.py::test_migration_creates_all_tables, test_repository_table_columns, test_api_key_repo_access_composite_pk
- **Test Type**: Real

---

### 用例编号

ST-FUNC-002-002

### 关联需求

FR-001（Repository Registration — data persistence）

### 测试目标

验证 Repository 模型创建记录时自动生成 UUID id、设置 status='pending' 和 created_at 时间戳。

### 前置条件

- 数据库表已创建（Base.metadata.create_all）
- 异步会话可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 `Repository(name='test-repo', url='https://github.com/test/repo')` | 实例创建成功 |
| 2 | 将实例添加到会话并 commit | 无异常 |
| 3 | 刷新实例 (refresh) | 从数据库加载最新值 |
| 4 | 检查 `repo.id` | 非 None，类型为 uuid.UUID |
| 5 | 检查 `repo.status` | 等于 `"pending"` |
| 6 | 检查 `repo.created_at` | 非 None |
| 7 | 检查 `repo.name` 和 `repo.url` | 分别等于 `"test-repo"` 和 `"https://github.com/test/repo"` |

### 验证点

- id 是自动生成的 UUID（非 None）
- status 默认为 "pending"
- created_at 自动设置（非 None）
- name 和 url 与输入一致

### 后置检查

- 回滚或清理测试数据

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_feature_2_models.py::test_repository_create_with_defaults, test_repository_round_trip
- **Test Type**: Real

---

### 用例编号

ST-FUNC-002-003

### 关联需求

FR-001（Storage clients interface）

### 测试目标

验证 ElasticsearchClient、QdrantClientWrapper、RedisClient 均可导入，且具有 connect、health_check、close 异步方法。

### 前置条件

- 项目已安装
- elasticsearch, qdrant-client, redis 库已安装

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `from src.shared.clients import ElasticsearchClient, QdrantClientWrapper, RedisClient` | 导入成功，三个类均非 None |
| 2 | 创建 `ElasticsearchClient(url="http://localhost:9200")` | 实例创建成功 |
| 3 | 验证实例具有 `connect`, `health_check`, `close` 方法 | 三个方法均存在且为协程函数 |
| 4 | 对 QdrantClientWrapper 和 RedisClient 重复步骤 2-3 | 同样验证通过 |

### 验证点

- 三个客户端类均可从 `src.shared.clients` 导入
- 每个客户端都有 connect, health_check, close 三个异步方法
- 方法均为 `asyncio.iscoroutinefunction` == True

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_feature_2_clients.py::test_all_clients_importable, test_elasticsearch_client_methods, test_qdrant_client_methods, test_redis_client_methods
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-002-001

### 关联需求

FR-001（Data integrity constraints）

### 测试目标

验证 Repository 表的 NOT NULL 和 UNIQUE 约束在数据层正确拒绝非法数据。

### 前置条件

- 数据库表已创建
- 异步会话可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 `Repository(name=None, url='https://github.com/test/null')` 并 commit | 抛出 IntegrityError（NOT NULL 约束） |
| 2 | 回滚会话 | 会话恢复正常 |
| 3 | 创建 `Repository(name='repo1', url='https://github.com/test/dup')` 并 commit | 成功 |
| 4 | 创建 `Repository(name='repo2', url='https://github.com/test/dup')` 并 commit | 抛出 IntegrityError（UNIQUE 约束） |
| 5 | 回滚会话 | 会话恢复正常 |

### 验证点

- name=None 时触发 NOT NULL 约束
- url=None 时触发 NOT NULL 约束
- 重复 url 时触发 UNIQUE 约束
- 约束违反后会话可回滚恢复

### 后置检查

- 回滚所有未提交事务

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_feature_2_models.py::test_repository_null_name_raises, test_repository_null_url_raises, test_repository_duplicate_url_raises
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-002-002

### 关联需求

FR-001（Client input validation）

### 测试目标

验证存储客户端在接收空或 None URL 时正确抛出 ValueError。

### 前置条件

- 项目已安装

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `ElasticsearchClient(url='')` | 抛出 ValueError，消息包含 "url must not be empty" |
| 2 | `ElasticsearchClient(url=None)` | 抛出 ValueError，消息包含 "url must not be empty" |
| 3 | `QdrantClientWrapper(url='')` | 抛出 ValueError |
| 4 | `QdrantClientWrapper(url=None)` | 抛出 ValueError |
| 5 | `RedisClient(url='')` | 抛出 ValueError |
| 6 | `RedisClient(url=None)` | 抛出 ValueError |

### 验证点

- 空字符串 URL 触发 ValueError
- None URL 触发 ValueError
- 错误消息为 "url must not be empty"
- 所有三个客户端行为一致

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_feature_2_clients.py::test_elasticsearch_client_empty_url_raises, test_elasticsearch_client_none_url_raises, test_qdrant_client_empty_url_raises, test_qdrant_client_none_url_raises, test_redis_client_empty_url_raises, test_redis_client_none_url_raises
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-002-001 | FR-001 | VS-1: Alembic migration creates 5 tables | test_migration_creates_all_tables, test_repository_table_columns, test_api_key_repo_access_composite_pk | Real | PASS |
| ST-FUNC-002-002 | FR-001 | VS-2: Repository persists with UUID, status, created_at | test_repository_create_with_defaults, test_repository_round_trip | Real | PASS |
| ST-FUNC-002-003 | FR-001 | VS-3: Clients importable with connection/health methods | test_all_clients_importable, test_elasticsearch_client_methods, test_qdrant_client_methods, test_redis_client_methods | Real | PASS |
| ST-BNDRY-002-001 | FR-001 | VS-1: Constraints enforced | test_repository_null_name_raises, test_repository_null_url_raises, test_repository_duplicate_url_raises | Real | PASS |
| ST-BNDRY-002-002 | FR-001 | VS-3: Client validation | test_elasticsearch_client_empty_url_raises, test_qdrant_client_empty_url_raises, test_redis_client_empty_url_raises + None variants | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 5 |
| Passed | 5 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
