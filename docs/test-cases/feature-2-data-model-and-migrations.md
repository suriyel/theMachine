# 测试用例集: Data Model and Migrations

**Feature ID**: 2
**关联需求**: M1 Foundation (FR-001, FR-002, FR-016, FR-017, FR-018, NFR-009)
**日期**: 2026-03-14
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 6 |
| boundary | 5 |
| ui | 0 |
| security | 1 |
| accessibility | 0 |
| performance | 0 |
| **合计** | **12** |

---

### 用例编号

ST-FUNC-002-001

### 关联需求

M1 Foundation — verification_step[0]

### 测试目标

验证 Alembic 迁移可以创建所有必需的数据库表

### 前置条件

- PostgreSQL 数据库已运行 (DATABASE_URL 配置正确)
- alembic.ini 配置文件存在
- alembic/env.py 已配置异步迁移环境

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `alembic downgrade base` | 所有表被删除，数据库为空 |
| 2 | 执行 `alembic upgrade head` | 迁移成功完成，无错误 |
| 3 | 查询 PostgreSQL 信息模式 | 表 repositories, index_jobs, code_chunks, api_keys, query_logs 全部存在 |
| 4 | 验证每个表的列定义 | 列名和类型与设计文档 Section 5 ER 图一致 |

### 验证点

- `alembic upgrade head` 退出码为 0
- 5 个表全部存在: repositories, index_jobs, code_chunks, api_keys, query_logs
- repositories 表包含列: id, url, name, languages, status, created_at, updated_at, last_indexed_at
- index_jobs 表包含列: id, repo_id, status, trigger_type, started_at, completed_at, error_message, chunk_count
- code_chunks 表包含列: id, repo_id, file_path, language, granularity, symbol_name, content, start_line, end_line, indexed_at
- api_keys 表包含列: id, key_hash, name, status, created_at, revoked_at
- query_logs 表包含列: id, api_key_id, query_text, query_type, repo_filter, language_filter, result_count, latency_ms, correlation_id, created_at

### 后置检查

- 数据库表保留供后续测试使用

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_models.py::TestAlembicMigrations
- **Test Type**: Real

---

### 用例编号

ST-FUNC-002-002

### 关联需求

M1 Foundation — verification_step[1]

### 测试目标

验证 Repository 模型可以创建、持久化和查询记录

### 前置条件

- 数据库表已创建 (ST-FUNC-002-001 通过)
- DATABASE_URL 配置正确

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 Repository 对象: url="https://github.com/example/repo.git", name="example-repo", languages=["Java", "Python"] | 对象创建成功 |
| 2 | 添加到 session 并 flush | 记录被持久化，id 自动生成 (UUID) |
| 3 | 查询 Repository.where(url=...) | 返回刚创建的记录 |
| 4 | 验证字段值 | url, name, languages 与输入一致，status=REGISTERED，created_at 已设置 |

### 验证点

- Repository.id 是有效的 UUID
- Repository.url = "https://github.com/example/repo.git"
- Repository.name = "example-repo"
- Repository.languages = ["Java", "Python"]
- Repository.status = RepoStatus.REGISTERED
- Repository.created_at 不为空

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_models.py::TestRepositoryModel::test_repository_create_happy_path
- **Test Type**: Real

---

### 用例编号

ST-FUNC-002-003

### 关联需求

M1 Foundation — verification_step[2]

### 测试目标

验证 IndexJob 模型可以创建带有 QUEUED 状态的作业记录

### 前置条件

- 数据库表已创建
- 存在一个有效的 Repository 记录

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 IndexJob 对象: repo_id=existing_repo_id, status=QUEUED, trigger_type=MANUAL | 对象创建成功 |
| 2 | 添加到 session 并 flush | 记录被持久化，id 自动生成 (UUID) |
| 3 | 验证字段值 | id 是 UUID，status=QUEUED，started_at=None，completed_at=None |

### 验证点

- IndexJob.id 是有效的 UUID
- IndexJob.repo_id 指向有效的 Repository
- IndexJob.status = JobStatus.QUEUED
- IndexJob.trigger_type = TriggerType.MANUAL
- IndexJob.started_at is None
- IndexJob.completed_at is None
- IndexJob.chunk_count = 0 (默认值)

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_models.py::TestIndexJobModel::test_index_job_create_with_queued_status
- **Test Type**: Real

---

### 用例编号

ST-FUNC-002-004

### 关联需求

M1 Foundation — verification_step[3]

### 测试目标

验证 CodeChunk 模型可以创建带有复合 ID 的代码块记录

### 前置条件

- 数据库表已创建
- 存在一个有效的 Repository 记录

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 生成 chunk_id = CodeChunk.generate_id(repo_id, "src/main.py", "main_function") | 返回格式为 "repo_id:file_path:symbol_hash" 的字符串 |
| 2 | 创建 CodeChunk 对象: id=chunk_id, repo_id, file_path, language, granularity, content, start_line, end_line | 对象创建成功 |
| 3 | 添加到 session 并 flush | 记录被持久化 |
| 4 | 验证字段值 | 所有字段与输入一致 |

### 验证点

- CodeChunk.id 包含 repo_id 和 file_path
- CodeChunk.file_path = "src/main.py"
- CodeChunk.language = "Python"
- CodeChunk.granularity = ChunkGranularity.FUNCTION
- CodeChunk.symbol_name = "main_function"
- CodeChunk.content 不为空
- CodeChunk.indexed_at 已设置

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_models.py::TestCodeChunkModel::test_code_chunk_create_happy_path
- **Test Type**: Real

---

### 用例编号

ST-FUNC-002-005

### 关联需求

M1 Foundation — verification_step[4]

### 测试目标

验证 APIKey 模型可以创建带有 active 状态的 API 密钥记录

### 前置条件

- 数据库表已创建

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 计算 key_hash = SHA256("test-api-key") | 返回 64 字符的十六进制字符串 |
| 2 | 创建 APIKey 对象: key_hash, name="Test API Key" | 对象创建成功 |
| 3 | 添加到 session 并 flush | 记录被持久化，id 自动生成 (UUID) |
| 4 | 验证字段值 | key_hash 正确，name 正确，status=ACTIVE |

### 验证点

- APIKey.id 是有效的 UUID
- APIKey.key_hash = SHA256("test-api-key")
- APIKey.name = "Test API Key"
- APIKey.status = KeyStatus.ACTIVE
- APIKey.created_at 已设置
- APIKey.revoked_at is None

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_models.py::TestAPIKeyModel::test_api_key_create_with_active_status
- **Test Type**: Real

---

### 用例编号

ST-FUNC-002-006

### 关联需求

M1 Foundation — verification_step[5]

### 测试目标

验证 QueryLog 模型可以创建带有 correlation_id 的查询日志记录

### 前置条件

- 数据库表已创建

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 QueryLog 对象: query_text="test query", query_type=NATURAL_LANGUAGE, result_count=3, latency_ms=142.5 | 对象创建成功 |
| 2 | 添加到 session 并 flush | 记录被持久化，id 和 correlation_id 自动生成 |
| 3 | 验证字段值 | 所有字段正确，correlation_id 是 UUID |

### 验证点

- QueryLog.id 是有效的 UUID
- QueryLog.correlation_id 是有效的 UUID
- QueryLog.query_text = "test query"
- QueryLog.query_type = QueryType.NATURAL_LANGUAGE
- QueryLog.result_count = 3
- QueryLog.latency_ms = 142.5
- QueryLog.created_at 已设置

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_models.py::TestQueryLogModel::test_query_log_create_with_correlation_id
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-002-001

### 关联需求

M1 Foundation — Repository model

### 测试目标

验证 Repository URL 唯一性约束 — 重复 URL 应引发错误

### 前置条件

- 数据库表已创建
- 已存在一个 Repository 记录

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 Repository(url="https://github.com/duplicate/test.git", name="repo1") | 成功 |
| 2 | flush 并提交 | 记录持久化 |
| 3 | 创建另一个 Repository(url="https://github.com/duplicate/test.git", name="repo2") | 对象创建成功 |
| 4 | flush | 抛出 IntegrityError |

### 验证点

- 第二次 flush 抛出 IntegrityError
- 错误信息包含唯一性约束违反

### 后置检查

- 事务回滚

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_models.py::TestRepositoryModel::test_repository_duplicate_url_raises_error
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-002-002

### 关联需求

M1 Foundation — IndexJob model

### 测试目标

验证 IndexJob 外键约束 — 无效 repo_id 应引发错误

### 前置条件

- 数据库表已创建

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 IndexJob(repo_id=uuid.uuid4(), status=QUEUED, trigger_type=MANUAL) | 对象创建成功 |
| 2 | flush | 抛出 IntegrityError |

### 验证点

- flush 抛出 IntegrityError
- 错误信息包含外键约束违反

### 后置检查

- 事务回滚

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_models.py::TestIndexJobModel::test_index_job_invalid_repo_fk_raises_error
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-002-003

### 关联需求

M1 Foundation — CodeChunk model

### 测试目标

验证 CodeChunk 可以处理大型内容 (100KB+)

### 前置条件

- 数据库表已创建
- 存在一个有效的 Repository 记录

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 large_content = "x" * 100000 (100KB) | 字符串创建成功 |
| 2 | 创建 CodeChunk(content=large_content, ...) | 对象创建成功 |
| 3 | flush | 记录持久化成功 |
| 4 | 验证 len(chunk.content) | = 100000 |

### 验证点

- 记录成功持久化
- content 长度保持 100000 字符

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_models.py::TestCodeChunkModel::test_code_chunk_large_content
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-002-004

### 关联需求

M1 Foundation — APIKey model

### 测试目标

验证 APIKey 撤销功能设置 revoked_at 时间戳

### 前置条件

- 数据库表已创建
- 存在一个 active 状态的 APIKey 记录

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 获取现有的 APIKey | revoked_at is None, is_active() = True |
| 2 | 调用 api_key.revoke() | status = REVOKED |
| 3 | flush | revoked_at 被设置 |
| 4 | 验证 | revoked_at 不为空, is_active() = False |

### 验证点

- revoke() 后 status = KeyStatus.REVOKED
- revoked_at 被设置为当前时间
- is_active() 返回 False

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_models.py::TestAPIKeyModel::test_api_key_revocation_sets_timestamp
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-002-005

### 关联需求

M1 Foundation — QueryLog model

### 测试目标

验证 QueryLog 可以存储高精度延迟值 (亚毫秒)

### 前置条件

- 数据库表已创建

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 QueryLog(latency_ms=0.123, ...) | 对象创建成功 |
| 2 | flush | 记录持久化 |
| 3 | 验证 latency_ms | abs(log.latency_ms - 0.123) < 0.001 |

### 验证点

- latency_ms 保持精度 (误差 < 0.001)

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_models.py::TestQueryLogModel::test_query_log_latency_precision
- **Test Type**: Real

---

### 用例编号

ST-SEC-002-001

### 关联需求

FR-018 (Authenticate Query)

### 测试目标

验证 APIKey 密钥以 SHA-256 哈希形式存储，而非明文

### 前置条件

- 数据库表已创建

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 定义 plain_key = "sk-test-secret-key-12345" | 明文密钥 |
| 2 | 计算 key_hash = SHA256(plain_key) | 64 字符十六进制 |
| 3 | 创建 APIKey(key_hash=key_hash, name="Test") | 对象创建成功 |
| 4 | flush | 记录持久化 |
| 5 | 验证 key_hash 属性 | 长度=64，全是字母数字，不包含 plain_key |

### 验证点

- key_hash 长度为 64 字符 (SHA-256)
- key_hash 只包含字母和数字 (十六进制)
- plain_key 不出现在 key_hash 中
- 数据库不存储明文密钥

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: security
- **已自动化**: Yes
- **测试引用**: tests/test_models.py::TestAPIKeyModel::test_api_key_hash_not_plain_text
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-002-001 | M1 Foundation | verification_step[0] | TestAlembicMigrations | Real | PASS |
| ST-FUNC-002-002 | M1 Foundation | verification_step[1] | test_repository_create_happy_path | Real | PASS |
| ST-FUNC-002-003 | M1 Foundation | verification_step[2] | test_index_job_create_with_queued_status | Real | PASS |
| ST-FUNC-002-004 | M1 Foundation | verification_step[3] | test_code_chunk_create_happy_path | Real | PASS |
| ST-FUNC-002-005 | M1 Foundation | verification_step[4] | test_api_key_create_with_active_status | Real | PASS |
| ST-FUNC-002-006 | M1 Foundation | verification_step[5] | test_query_log_create_with_correlation_id | Real | PASS |
| ST-BNDRY-002-001 | M1 Foundation | Repository unique URL | test_repository_duplicate_url_raises_error | Real | PASS |
| ST-BNDRY-002-002 | M1 Foundation | IndexJob FK constraint | test_index_job_invalid_repo_fk_raises_error | Real | PASS |
| ST-BNDRY-002-003 | M1 Foundation | CodeChunk large content | test_code_chunk_large_content | Real | PASS |
| ST-BNDRY-002-004 | M1 Foundation | APIKey revocation | test_api_key_revocation_sets_timestamp | Real | PASS |
| ST-BNDRY-002-005 | M1 Foundation | QueryLog latency precision | test_query_log_latency_precision | Real | PASS |
| ST-SEC-002-001 | FR-018 | API key hashing | test_api_key_hash_not_plain_text | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 12 |
| Passed | 12 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
