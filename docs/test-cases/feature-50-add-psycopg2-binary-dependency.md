# 测试用例集: Add psycopg2-binary for Celery Worker Sync DB Access

**Feature ID**: 50
**关联需求**: FR-019, FR-020
**日期**: 2026-04-03
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 3 |
| boundary | 2 |
| ui | 0 |
| security | 0 |
| accessibility | 0 |
| performance | 0 |
| **合计** | **5** |

---

### 用例编号

ST-FUNC-050-001

### 关联需求

FR-019（定时索引刷新）/ FR-020（手动重建索引）

### 测试目标

验证 psycopg2-binary 已正确安装，在 Python 环境中可成功导入且版本满足 >=2.9 要求。

### 前置条件

- `pip install -e '.[dev]'` 已成功执行
- Python 虚拟环境已激活

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 在 Python 中执行 `import psycopg2` | 导入成功，无 ImportError |
| 2 | 读取 `psycopg2.__version__` 并提取主版本号和次版本号 | 版本号格式为 `X.Y.Z`，且 (X, Y) >= (2, 9) |
| 3 | 检查 `psycopg2.connect` 属性存在 | `hasattr(psycopg2, 'connect')` 返回 True |

### 验证点

- psycopg2 模块可导入，无异常
- psycopg2 版本 >= 2.9
- psycopg2 提供标准 connect() 接口

### 后置检查

- 无清理动作

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_psycopg2_dependency.py::test_psycopg2_importable
- **Test Type**: Real

---

### 用例编号

ST-FUNC-050-002

### 关联需求

FR-019（定时索引刷新）/ FR-020（手动重建索引）

### 测试目标

验证 `_get_sync_session()` 能正确连接到真实 PostgreSQL 数据库并执行查询，确认 psycopg2 驱动在运行时可用。

### 前置条件

- PostgreSQL 容器运行中且可达 (localhost:5432)
- DATABASE_URL 环境变量已设置
- `pip install -e '.[dev]'` 已成功执行

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 验证 PostgreSQL 可达：`pg_isready -h localhost -p 5432` | 返回 "accepting connections" |
| 2 | 调用 `_get_sync_session()` 获取 Session 对象 | 返回有效的 SQLAlchemy Session，无 ImportError |
| 3 | 通过 Session 执行 `SELECT 1` | 查询返回标量值 1 |
| 4 | 关闭 Session | Session 正常关闭，无异常 |

### 验证点

- `_get_sync_session()` 不抛出 ImportError（psycopg2 驱动可用）
- `_get_sync_session()` 不抛出 OperationalError（数据库可达）
- SELECT 1 查询返回预期结果 1
- Session 可正常关闭

### 后置检查

- Session 已关闭释放连接

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_psycopg2_dependency.py::test_real_get_sync_session_db_connection_feature_50
- **Test Type**: Real

---

### 用例编号

ST-FUNC-050-003

### 关联需求

FR-019（定时索引刷新）/ FR-020（手动重建索引）

### 测试目标

验证 `_get_sync_session()` 正确将 asyncpg URL 转换为同步 postgresql:// URL 并创建 Session。

### 前置条件

- Python 虚拟环境已激活
- `src.indexing.scheduler` 模块可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 设置 DATABASE_URL 为 `postgresql+asyncpg://user:pass@localhost/db` | 环境变量已设置 |
| 2 | Mock `create_engine`，调用 `_get_sync_session()` | `create_engine` 被调用，参数为 `postgresql://user:pass@localhost/db` |
| 3 | 验证返回值为 Session 实例 | 返回 mock Session 对象 |

### 验证点

- asyncpg URL scheme 被替换为标准 postgresql://
- create_engine 使用转换后的同步 URL
- 返回有效的 Session 对象

### 后置检查

- 无清理动作

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_psycopg2_dependency.py::test_get_sync_session_returns_session_with_sync_url
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-050-001

### 关联需求

FR-019（定时索引刷新）/ FR-020（手动重建索引）

### 测试目标

验证 pyproject.toml 的 dev 可选依赖中正确声明了 `psycopg2-binary>=2.9`。

### 前置条件

- 项目根目录存在 pyproject.toml 文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 使用 tomllib 解析 pyproject.toml | 解析成功，无语法错误 |
| 2 | 读取 `[project.optional-dependencies] dev` 列表 | 列表存在且非空 |
| 3 | 在 dev 列表中查找以 `psycopg2-binary` 开头的条目 | 恰好有一个匹配条目 |
| 4 | 验证该条目包含 `>=2.9` 版本约束 | 条目为 `psycopg2-binary>=2.9` |

### 验证点

- pyproject.toml 可正确解析
- dev 可选依赖列表包含恰好一个 psycopg2-binary 条目
- 版本约束为 >=2.9

### 后置检查

- 无清理动作

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_psycopg2_dependency.py::test_pyproject_contains_psycopg2_binary
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-050-002

### 关联需求

FR-019（定时索引刷新）/ FR-020（手动重建索引）

### 测试目标

验证当 DATABASE_URL 为空字符串时，`_get_sync_session()` 不会在会话创建阶段崩溃（连接是延迟的）。

### 前置条件

- Python 虚拟环境已激活
- `src.indexing.scheduler` 模块可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 设置 DATABASE_URL 为空字符串 `""` | 环境变量已设置 |
| 2 | Mock `create_engine`，调用 `_get_sync_session()` | 函数正常返回，不抛出异常 |
| 3 | 验证 `create_engine` 被调用的参数为空字符串 | `create_engine("")` 被调用一次 |

### 验证点

- 空 DATABASE_URL 不导致 Session 创建阶段崩溃
- create_engine 接收空字符串作为参数
- 返回有效的 Session 对象（连接错误将在实际查询时延迟抛出）

### 后置检查

- 无清理动作

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_psycopg2_dependency.py::test_get_sync_session_empty_database_url
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-050-001 | FR-019, FR-020 | verification_step[0] | test_psycopg2_importable | Real | PASS |
| ST-FUNC-050-002 | FR-019, FR-020 | verification_step[1] | test_real_get_sync_session_db_connection_feature_50 | Real | PASS |
| ST-FUNC-050-003 | FR-019, FR-020 | verification_step[1] | test_get_sync_session_returns_session_with_sync_url | Mock | PASS |
| ST-BNDRY-050-001 | FR-019, FR-020 | verification_step[0] | test_pyproject_contains_psycopg2_binary | Real | PASS |
| ST-BNDRY-050-002 | FR-019, FR-020 | verification_step[1] | test_get_sync_session_empty_database_url | Mock | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 3 |
| Passed | 3 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
