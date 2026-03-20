# 测试用例集: Project Skeleton & CI

**Feature ID**: 1
**关联需求**: Infrastructure（无专属 FR，支撑所有 FR）
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

ST-FUNC-001-001

### 关联需求

Infrastructure — VS-1（pip install -e .[dev] 成功安装）

### 测试目标

验证项目可从零安装，所有依赖正确声明，pytest 可用。

### 前置条件

- 项目源码已克隆
- Python 3.11+ 可用
- 虚拟环境已创建并激活

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `pip install -e .[dev]` | 退出码 0，无错误输出 |
| 2 | 执行 `python -c "import pytest; print(pytest.__version__)"` | 输出 pytest 版本号（8.3.4） |
| 3 | 执行 `python -c "import fastapi; import sqlalchemy; import alembic"` | 无 ImportError |

### 验证点

- pip install 退出码为 0
- pytest 可导入且版本 >= 8.3.0
- FastAPI, SQLAlchemy, Alembic 均可导入

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: No（环境安装验证）
- **测试引用**: N/A
- **Test Type**: Real

---

### 用例编号

ST-FUNC-001-002

### 关联需求

Infrastructure — VS-2, VS-3（测试通过 + 包可导入）

### 测试目标

验证项目结构正确，所有核心包可导入，基础测试通过。

### 前置条件

- 项目已通过 `pip install -e .[dev]` 安装
- 虚拟环境已激活

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `pytest tests/test_skeleton.py -v` | 2 个测试全部通过 |
| 2 | 执行 `python -c "import src.shared; import src.indexing; import src.query"` | 无 ImportError |
| 3 | 执行 `pytest tests/test_feature_1_skeleton.py -v` | 13 个测试全部通过 |

### 验证点

- test_skeleton.py 中 test_src_packages_importable 和 test_project_structure 均 PASS
- src.shared, src.indexing, src.query 三个顶层包均可导入
- test_feature_1_skeleton.py 中 13 个测试均 PASS

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_skeleton.py::test_src_packages_importable, tests/test_skeleton.py::test_project_structure
- **Test Type**: Real

---

### 用例编号

ST-FUNC-001-003

### 关联需求

Infrastructure — VS-4（Alembic 配置正确）

### 测试目标

验证 Alembic 迁移基础设施已配置，env.py 支持异步引擎。

### 前置条件

- 项目已安装
- alembic.ini 存在于项目根目录

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 检查 `alembic.ini` 文件存在 | 文件存在，包含 `script_location = alembic` |
| 2 | 检查 `alembic/env.py` 文件存在 | 文件存在，包含 `async_engine_from_config` |
| 3 | 检查 `alembic/versions/` 目录存在 | 目录存在（当前为空，无迁移文件——Feature #2 将创建首个迁移） |

### 验证点

- alembic.ini 中 script_location 指向 alembic 目录
- env.py 使用异步引擎（async_engine_from_config）
- versions 目录已创建，可接收迁移文件

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: No（文件结构验证）
- **测试引用**: N/A
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-001-001

### 关联需求

Infrastructure — 健康检查端点边界行为

### 测试目标

验证健康检查端点在错误路径和错误方法下的行为正确。

### 前置条件

- 项目已安装
- FastAPI 应用可通过 TestClient 访问

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | GET `/api/v1/health` | 200, body = `{"status": "ok", "service": "code-context-retrieval"}` |
| 2 | GET `/health`（错误路径） | 404 |
| 3 | POST `/api/v1/health`（错误方法） | 405 |
| 4 | GET `/api/v2/health`（不存在的版本） | 404 |

### 验证点

- 正确路径返回 200 和正确 JSON
- 错误路径返回 404
- 不支持的 HTTP 方法返回 405

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_feature_1_skeleton.py::test_health_wrong_path_returns_404, tests/test_feature_1_skeleton.py::test_health_endpoint_rejects_post
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-001-002

### 关联需求

Infrastructure — 配置与数据库引擎边界行为

### 测试目标

验证 Settings 和 get_engine 在缺失/无效输入下的错误处理。

### 前置条件

- 项目已安装

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构造 Settings 时不提供 DATABASE_URL（`_env_file=None`） | 抛出 ValidationError，错误信息包含 "database_url" |
| 2 | 调用 `get_engine("")` | 抛出 ValueError，错误信息包含 "must not be empty" |
| 3 | 调用 `get_engine("sqlite+aiosqlite:///test.db")` | 返回 AsyncEngine 实例，URL 包含 "test.db" |

### 验证点

- 缺失必需配置时抛出明确异常
- 空 URL 被拒绝并给出有意义的错误消息
- 有效 URL 返回正确类型的引擎实例

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_feature_1_skeleton.py::test_settings_missing_database_url_raises, tests/test_feature_1_skeleton.py::test_get_engine_empty_url_raises
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-001-001 | Infrastructure | VS-1: pip install -e .[dev] succeeds | N/A | Real | PASS |
| ST-FUNC-001-002 | Infrastructure | VS-2: pytest tests/test_skeleton.py passes; VS-3: imports succeed | test_skeleton.py, test_feature_1_skeleton.py | Real | PASS |
| ST-FUNC-001-003 | Infrastructure | VS-4: alembic check confirms migrations in sync | N/A | Real | PASS |
| ST-BNDRY-001-001 | Infrastructure | Health endpoint boundary behavior | test_health_wrong_path_returns_404, test_health_endpoint_rejects_post | Real | PASS |
| ST-BNDRY-001-002 | Infrastructure | Config/engine boundary behavior | test_settings_missing_database_url_raises, test_get_engine_empty_url_raises | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 5 |
| Passed | 5 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
