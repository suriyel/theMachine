# 测试用例集: mcp-server Docker Image

**Feature ID**: 44
**关联需求**: FR-028, NFR-012
**日期**: 2026-03-23
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

---

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 4 |
| boundary | 3 |
| ui | 0 |
| security | 0 |
| accessibility | 0 |
| performance | 0 |
| **合计** | **7** |

---

### 用例编号

ST-FUNC-044-001

### 关联需求

FR-028（mcp-server Docker Image — Build exits 0）

### 测试目标

验证 `docker build -f docker/Dockerfile.mcp -t codecontext-mcp .` 构建成功退出 0，且本地 Docker daemon 中存在 `codecontext-mcp` 镜像。

### 前置条件

- Docker daemon 正在运行
- 工作目录为项目根 `/home/machine/code/theMachine`
- `docker/Dockerfile.mcp` 文件存在
- 网络可访问 Docker Hub（用于拉取 `python:3.11-slim`），或本地缓存中已有该基础镜像

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 在项目根目录执行 `docker build -f docker/Dockerfile.mcp -t codecontext-mcp .` | 构建开始，逐层打印 Docker layer 日志 |
| 2 | 等待构建完成，检查退出码 `echo "exit:$?"` | 退出码为 `0` |
| 3 | 执行 `docker image inspect codecontext-mcp` | 命令退出码为 0，确认镜像存在于本地 registry |

### 验证点

- `docker build` 命令退出码 = 0
- `docker image inspect codecontext-mcp` 返回非空结果（退出码 0）

### 后置检查

- 构建完成后保留镜像供后续用例使用（ST-FUNC-044-002 至 ST-FUNC-044-004、ST-BNDRY-044-001 至 ST-BNDRY-044-003）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: `tests/test_feature_44_mcp_docker.py::test_t01_build_succeeds`
- **Test Type**: Real

---

### 用例编号

ST-FUNC-044-002

### 关联需求

FR-028（mcp-server Docker Image — 容器启动后 python -m src.query.mcp_server 为活动进程）

### 测试目标

验证构建的 `codecontext-mcp` 镜像的 CMD 为 `["python", "-m", "src.query.mcp_server"]`（exec-form），确保容器启动后该进程为活动进程。

### 前置条件

- `codecontext-mcp` 镜像已成功构建（ST-FUNC-044-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `docker inspect codecontext-mcp --format "{{json .Config.Cmd}}"` | 输出 JSON 数组，非 `null` |
| 2 | 检查 Cmd 数组值：验证等于 `["python", "-m", "src.query.mcp_server"]` | 精确匹配三元素数组 `["python", "-m", "src.query.mcp_server"]` |
| 3 | 确认 CMD 为 exec-form（数组第一个元素为 `"python"`，而非 `"/bin/sh"`） | `Cmd[0]` = `"python"` —— 不是 shell-form 包装 |

### 验证点

- `Config.Cmd` = `["python", "-m", "src.query.mcp_server"]`
- `Cmd[0]` 不等于 `/bin/sh`（exec-form 确认）

### 后置检查

- 无（镜像保留供后续用例使用）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: `tests/test_feature_44_mcp_docker.py::test_t02_cmd_is_mcp_server`
- **Test Type**: Real

---

### 用例编号

ST-FUNC-044-003

### 关联需求

FR-028（mcp-server Docker Image — HEALTHCHECK 指令存在且使用 pgrep -f "src.query.mcp_server"）

### 测试目标

验证构建的 `codecontext-mcp` 镜像中含有 HEALTHCHECK 指令，且该指令使用 `pgrep -f "src.query.mcp_server"` 验证进程存活。

### 前置条件

- `codecontext-mcp` 镜像已成功构建（ST-FUNC-044-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `docker inspect codecontext-mcp --format "{{json .Config.Healthcheck}}"` | 输出 JSON 对象，非 `null` |
| 2 | 从输出中提取 `Test` 数组：检查是否包含字符串 `pgrep` | `Test` 数组中包含 `pgrep` |
| 3 | 检查 `Test` 数组中是否包含字符串 `src.query.mcp_server` | 确认 HEALTHCHECK 目标为 MCP 服务器进程名 |

### 验证点

- `.Config.Healthcheck` 非 `null`
- `Healthcheck.Test` 包含 `pgrep`
- `Healthcheck.Test` 包含 `src.query.mcp_server`

### 后置检查

- 无（镜像保留供后续用例使用）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: `tests/test_feature_44_mcp_docker.py::test_t03_healthcheck_uses_pgrep`
- **Test Type**: Real

---

### 用例编号

ST-FUNC-044-004

### 关联需求

FR-028（mcp-server Docker Image — 仅含生产依赖，无 pytest/mutmut，非 root 用户）

### 测试目标

验证构建的镜像中不含开发依赖（pytest、mutmut），运行用户为非 root 的 `appuser`（UID 1000）。

### 前置条件

- `codecontext-mcp` 镜像已成功构建（ST-FUNC-044-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `docker run --rm codecontext-mcp pip list` | 退出码为 0；输出中不含 `pytest`、`mutmut`、`locust` |
| 2 | 检查 `Config.User`：`docker inspect codecontext-mcp --format "{{.Config.User}}"` | 输出为 `appuser` 或 `1000` |
| 3 | 执行 `docker run --rm codecontext-mcp pip show pytest; echo "exit:$?"` | 退出码非 0（pytest 未安装） |
| 4 | 执行 `docker run --rm codecontext-mcp pip show mutmut; echo "exit:$?"` | 退出码非 0（mutmut 未安装） |

### 验证点

- `pip list` 输出中无 `pytest`、`mutmut`、`locust`
- `Config.User` = `appuser` 或 `1000`
- `pip show pytest` 退出码 ≠ 0
- `pip show mutmut` 退出码 ≠ 0

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: `tests/test_feature_44_mcp_docker.py::test_t04_no_dev_packages_installed`, `test_t05_runtime_user_is_appuser`, `test_t09_pytest_not_installed`
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-044-001

### 关联需求

FR-028（mcp-server Docker Image — 以非 root 用户运行，UID = 1000）

### 测试目标

验证容器以非 root 用户（`appuser`，UID 1000）运行，UID 不为 0。

### 前置条件

- `codecontext-mcp` 镜像已成功构建（ST-FUNC-044-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `docker run --rm codecontext-mcp id -u` | 输出为 `1000`（非 `0`） |
| 2 | 执行 `docker run --rm codecontext-mcp id -un` | 输出为 `appuser` |
| 3 | 确认 UID 不为 0：将步骤 1 输出与 `0` 比较 | UID ≠ 0（满足 FR-028 AC-4） |

### 验证点

- `id -u` 输出 = `1000`
- `id -un` 输出 = `appuser`
- UID ≠ 0

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: `tests/test_feature_44_mcp_docker.py::test_t08_runtime_uid_is_1000`
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-044-002

### 关联需求

FR-028（mcp-server Docker Image — HEALTHCHECK 时序参数：interval=30s，timeout=5s，retries=3）

### 测试目标

验证 HEALTHCHECK 指令的时序参数精确匹配设计规范：interval=30s（30000000000 ns），timeout=5s（5000000000 ns），retries=3。

### 前置条件

- `codecontext-mcp` 镜像已成功构建（ST-FUNC-044-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `docker inspect codecontext-mcp --format "{{json .Config.Healthcheck}}"` | 输出包含 `Interval`、`Timeout`、`Retries` 字段 |
| 2 | 检查 `Interval` 值 | `Interval` = `30000000000`（30s in nanoseconds） |
| 3 | 检查 `Timeout` 值 | `Timeout` = `5000000000`（5s in nanoseconds） |
| 4 | 检查 `Retries` 值 | `Retries` = `3` |

### 验证点

- `Healthcheck.Interval` = 30000000000 ns（30s）
- `Healthcheck.Timeout` = 5000000000 ns（5s）
- `Healthcheck.Retries` = 3

### 后置检查

- 无（镜像保留供后续用例使用）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: `tests/test_feature_44_mcp_docker.py::test_t07_healthcheck_timing_values`
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-044-003

### 关联需求

FR-028（mcp-server Docker Image — 无 EXPOSE 指令，无对外暴露端口）

### 测试目标

验证构建的镜像无任何 EXPOSE 指令（ExposedPorts 为 null 或空），因为 MCP 服务器使用 stdio 模式，无需端口绑定。

### 前置条件

- `codecontext-mcp` 镜像已成功构建（ST-FUNC-044-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `docker inspect codecontext-mcp --format "{{json .Config.ExposedPorts}}"` | 输出为 `null` 或 `{}` |
| 2 | 确认值为空或 null：任何非空值均为失败 | `ExposedPorts` 不存在或为空 map `{}` |

### 验证点

- `Config.ExposedPorts` 为 `null` 或空 `{}`
- 镜像无任何对外暴露的端口（stdio 模式）

### 后置检查

- 所有测试完成后：执行清理 `docker rmi codecontext-mcp` 或保留供后续 ST 轮次使用

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: `tests/test_feature_44_mcp_docker.py::test_t10_no_exposed_ports`
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-044-001 | FR-028 | VS-1: docker build exits 0 | `test_t01_build_succeeds` | Real | PASS |
| ST-FUNC-044-002 | FR-028 | VS-2: python -m src.query.mcp_server is active process | `test_t02_cmd_is_mcp_server` | Real | PASS |
| ST-FUNC-044-003 | FR-028 | VS-3: HEALTHCHECK verifying mcp_server process alive | `test_t03_healthcheck_uses_pgrep` | Real | PASS |
| ST-FUNC-044-004 | FR-028 | VS-4: production deps only, non-root user | `test_t04_no_dev_packages_installed`, `test_t05_runtime_user_is_appuser`, `test_t09_pytest_not_installed` | Real | PASS |
| ST-BNDRY-044-001 | FR-028 | VS-4: non-root user (UID=1000) | `test_t08_runtime_uid_is_1000` | Real | PASS |
| ST-BNDRY-044-002 | FR-028 | VS-3: HEALTHCHECK timing boundary (interval/timeout/retries) | `test_t07_healthcheck_timing_values` | Real | PASS |
| ST-BNDRY-044-003 | FR-028 | VS-2: no EXPOSE (stdio-only, no port needed) | `test_t10_no_exposed_ports` | Real | PASS |

---

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 7 |
| Passed | 7 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
