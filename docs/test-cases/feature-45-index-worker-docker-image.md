# 测试用例集: index-worker Docker Image

**Feature ID**: 45
**关联需求**: FR-029, NFR-012
**日期**: 2026-03-23
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

---

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 4 |
| boundary | 5 |
| ui | 0 |
| security | 0 |
| accessibility | 0 |
| performance | 0 |
| **合计** | **9** |

---

### 用例编号

ST-FUNC-045-001

### 关联需求

FR-029（index-worker Docker Image — Build exits 0）

### 测试目标

验证 `docker build -f docker/Dockerfile.worker -t codecontext-worker .` 构建成功退出 0，且本地 Docker daemon 中存在 `codecontext-worker-test` 镜像。

### 前置条件

- Docker daemon 正在运行
- 工作目录为项目根 `/home/machine/code/theMachine`
- `docker/Dockerfile.worker` 文件存在
- 网络可访问 Docker Hub（用于拉取 `python:3.11-slim`），或本地缓存中已有该基础镜像

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 在项目根目录执行 `docker build -f docker/Dockerfile.worker -t codecontext-worker-test .` | 构建开始，逐层打印 Docker layer 日志 |
| 2 | 等待构建完成，检查退出码 | 退出码为 `0` |
| 3 | 执行 `docker image inspect codecontext-worker-test` | 命令退出码为 0，确认镜像存在于本地 registry |

### 验证点

- `docker build` 命令退出码 = 0
- `docker image inspect codecontext-worker-test` 返回非空结果（退出码 0）

### 后置检查

- 构建完成后保留镜像供后续用例使用（ST-FUNC-045-002 至 ST-FUNC-045-004、ST-BNDRY-045-001 至 ST-BNDRY-045-005）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: `tests/test_feature_45_worker_docker.py::test_t01_build_succeeds`
- **Test Type**: Real

---

### 用例编号

ST-FUNC-045-002

### 关联需求

FR-029（index-worker Docker Image — 容器启动后 celery -A src.indexing.celery_app worker 为活动进程）

### 测试目标

验证构建的 `codecontext-worker-test` 镜像的 CMD 为 `["celery", "-A", "src.indexing.celery_app", "worker", "--loglevel=info"]`（exec-form），确保容器启动后该 Celery 进程为活动进程。

### 前置条件

- `codecontext-worker-test` 镜像已成功构建（ST-FUNC-045-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `docker inspect codecontext-worker-test --format "{{json .Config.Cmd}}"` | 输出 JSON 数组，非 `null` |
| 2 | 检查 Cmd 数组值：验证等于 `["celery", "-A", "src.indexing.celery_app", "worker", "--loglevel=info"]` | 精确匹配五元素数组 |
| 3 | 确认 CMD 为 exec-form（数组第一个元素为 `"celery"`，而非 `"/bin/sh"`） | `Cmd[0]` = `"celery"` —— 不是 shell-form 包装 |

### 验证点

- `Config.Cmd` = `["celery", "-A", "src.indexing.celery_app", "worker", "--loglevel=info"]`
- `Cmd[0]` 不等于 `/bin/sh`（exec-form 确认）

### 后置检查

- 无（镜像保留供后续用例使用）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: `tests/test_feature_45_worker_docker.py::test_t02_cmd_is_celery_worker`
- **Test Type**: Real

---

### 用例编号

ST-FUNC-045-003

### 关联需求

FR-029（index-worker Docker Image — HEALTHCHECK 指令存在且使用 celery inspect ping）

### 测试目标

验证构建的 `codecontext-worker-test` 镜像中含有 HEALTHCHECK 指令，且该指令使用 `celery -A src.indexing.celery_app inspect ping` 通过 broker 往返验证 worker 响应能力。

### 前置条件

- `codecontext-worker-test` 镜像已成功构建（ST-FUNC-045-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `docker inspect codecontext-worker-test --format "{{json .Config.Healthcheck}}"` | 输出 JSON 对象，非 `null` |
| 2 | 从输出中提取 `Test` 数组：检查是否包含字符串 `celery` | `Test` 数组中包含 `celery` |
| 3 | 检查 `Test` 数组中是否包含字符串 `inspect` 和 `ping` | 确认 HEALTHCHECK 使用 celery inspect ping 命令 |
| 4 | 检查 `Test` 数组中是否包含字符串 `src.indexing.celery_app` | 确认 HEALTHCHECK 目标为 worker Celery 应用 |

### 验证点

- `.Config.Healthcheck` 非 `null`
- `Healthcheck.Test` 包含 `celery`
- `Healthcheck.Test` 包含 `inspect` 和 `ping`
- `Healthcheck.Test` 包含 `src.indexing.celery_app`

### 后置检查

- 无（镜像保留供后续用例使用）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: `tests/test_feature_45_worker_docker.py::test_t03_healthcheck_uses_celery_inspect_ping`
- **Test Type**: Real

---

### 用例编号

ST-FUNC-045-004

### 关联需求

FR-029（index-worker Docker Image — 仅含生产依赖，无 pytest/mutmut，非 root 用户）

### 测试目标

验证构建的镜像中不含开发依赖（pytest、mutmut、locust），运行用户为非 root 的 `appuser`（UID 1000），且 celery CLI 可用（生产依赖安装正确）。

### 前置条件

- `codecontext-worker-test` 镜像已成功构建（ST-FUNC-045-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `docker run --rm codecontext-worker-test pip list` | 退出码为 0；输出中不含 `pytest`、`mutmut`、`locust` |
| 2 | 检查 `Config.User`：`docker inspect codecontext-worker-test --format "{{.Config.User}}"` | 输出为 `appuser` 或 `1000` |
| 3 | 执行 `docker run --rm codecontext-worker-test pip show pytest; echo "exit:$?"` | 退出码非 0（pytest 未安装） |
| 4 | 执行 `docker run --rm codecontext-worker-test pip show mutmut; echo "exit:$?"` | 退出码非 0（mutmut 未安装） |
| 5 | 执行 `docker run --rm codecontext-worker-test celery --version` | 退出码为 0；输出含版本数字（celery 已作为生产依赖安装） |

### 验证点

- `pip list` 输出中无 `pytest`、`mutmut`、`locust`
- `Config.User` = `appuser` 或 `1000`
- `pip show pytest` 退出码 ≠ 0
- `pip show mutmut` 退出码 ≠ 0
- `celery --version` 退出码 = 0

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: `tests/test_feature_45_worker_docker.py::test_t04_no_dev_packages_installed`, `test_t05_runtime_user_is_appuser`, `test_t09_pytest_not_installed`, `test_t13_celery_cli_is_installed`
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-045-001

### 关联需求

FR-029（index-worker Docker Image — 以非 root 用户运行，UID = 1000）

### 测试目标

验证容器以非 root 用户（`appuser`，UID 1000）运行，UID 不为 0。

### 前置条件

- `codecontext-worker-test` 镜像已成功构建（ST-FUNC-045-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `docker run --rm codecontext-worker-test id -u` | 输出为 `1000`（非 `0`） |
| 2 | 执行 `docker run --rm codecontext-worker-test id -un` | 输出为 `appuser` |
| 3 | 确认 UID 不为 0：将步骤 1 输出与 `0` 比较 | UID ≠ 0（满足 FR-029 AC-4） |

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
- **测试引用**: `tests/test_feature_45_worker_docker.py::test_t08_runtime_uid_is_1000`
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-045-002

### 关联需求

FR-029（index-worker Docker Image — HEALTHCHECK 时序参数：interval=60s，timeout=30s，retries=3）

### 测试目标

验证 HEALTHCHECK 指令的时序参数精确匹配设计规范：interval=60s（60000000000 ns），timeout=30s（30000000000 ns），retries=3。与 Feature #44 MCP 镜像不同（30s/5s），worker 镜像采用更宽松的时序以适应 broker 往返延迟。

### 前置条件

- `codecontext-worker-test` 镜像已成功构建（ST-FUNC-045-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `docker inspect codecontext-worker-test --format "{{json .Config.Healthcheck}}"` | 输出包含 `Interval`、`Timeout`、`Retries` 字段 |
| 2 | 检查 `Interval` 值 | `Interval` = `60000000000`（60s in nanoseconds） |
| 3 | 检查 `Timeout` 值 | `Timeout` = `30000000000`（30s in nanoseconds） |
| 4 | 检查 `Retries` 值 | `Retries` = `3` |

### 验证点

- `Healthcheck.Interval` = 60000000000 ns（60s）
- `Healthcheck.Timeout` = 30000000000 ns（30s）
- `Healthcheck.Retries` = 3

### 后置检查

- 无（镜像保留供后续用例使用）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: `tests/test_feature_45_worker_docker.py::test_t07_healthcheck_timing_values`
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-045-003

### 关联需求

FR-029（index-worker Docker Image — 无 EXPOSE 指令，无对外暴露端口）

### 测试目标

验证构建的镜像无任何 EXPOSE 指令（ExposedPorts 为 null 或空），因为 Celery worker 通过 broker（AMQP/Redis）通信，不监听入站端口。

### 前置条件

- `codecontext-worker-test` 镜像已成功构建（ST-FUNC-045-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `docker inspect codecontext-worker-test --format "{{json .Config.ExposedPorts}}"` | 输出为 `null` 或 `{}` |
| 2 | 确认值为空或 null：任何非空值均为失败 | `ExposedPorts` 不存在或为空 map `{}` |

### 验证点

- `Config.ExposedPorts` 为 `null` 或空 `{}`
- 镜像无任何对外暴露的端口（broker 通信模式）

### 后置检查

- 无（镜像保留供后续用例使用）

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: `tests/test_feature_45_worker_docker.py::test_t10_no_exposed_ports`
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-045-004

### 关联需求

FR-029（index-worker Docker Image — HEALTHCHECK 使用 -d celery@$HOSTNAME 定向本地 worker）

### 测试目标

验证 HEALTHCHECK 命令包含 `-d celery@$HOSTNAME` 标志，确保 inspect ping 定向到当前容器的 worker，而非集群中所有 worker。

### 前置条件

- `codecontext-worker-test` 镜像已成功构建（ST-FUNC-045-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `docker inspect codecontext-worker-test --format "{{json .Config.Healthcheck.Test}}"` | 输出 Test 数组，包含完整的 celery inspect ping 命令 |
| 2 | 检查 Test 数组中是否包含 `-d` 标志 | `-d` 存在于 HEALTHCHECK 命令中 |
| 3 | 检查 Test 数组中是否包含 `celery@$HOSTNAME` | `celery@$HOSTNAME` 存在，定向本地 worker |

### 验证点

- `Healthcheck.Test` 包含 `-d`
- `Healthcheck.Test` 包含 `celery@$HOSTNAME`

### 后置检查

- 无（镜像保留供后续用例使用）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: `tests/test_feature_45_worker_docker.py::test_t12_healthcheck_targets_local_worker`
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-045-005

### 关联需求

FR-029（index-worker Docker Image — docker build 缺少 Dockerfile.worker 时失败）

### 测试目标

验证当 Dockerfile.worker 文件不存在时，`docker build` 退出码非 0，并输出包含文件未找到相关错误信息，确保测试环境完整性。

### 前置条件

- Docker daemon 正在运行
- 工作目录为项目根 `/home/machine/code/theMachine`

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 以不存在的路径执行 `docker build -f /tmp/nonexistent_dockerfile -t test-should-fail .` | 构建命令立即失败 |
| 2 | 检查退出码 | 退出码 ≠ 0 |
| 3 | 检查 stderr/stdout 内容 | 输出含 "no such file"、"unable to prepare context"、"does not exist" 或 "not found" 中至少一条 |

### 验证点

- `docker build` 退出码 ≠ 0
- 错误输出包含文件不存在相关信息

### 后置检查

- 无（失败构建不产生镜像，无需清理）

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: `tests/test_feature_45_worker_docker.py::test_t06_build_fails_without_dockerfile`
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-045-001 | FR-029 | VS-1: docker build exits 0 | `test_t01_build_succeeds` | Real | PASS |
| ST-FUNC-045-002 | FR-029 | VS-2: celery worker is active process | `test_t02_cmd_is_celery_worker` | Real | PASS |
| ST-FUNC-045-003 | FR-029 | VS-3: HEALTHCHECK uses celery inspect ping | `test_t03_healthcheck_uses_celery_inspect_ping` | Real | PASS |
| ST-FUNC-045-004 | FR-029 | VS-4: production deps only, non-root user | `test_t04_no_dev_packages_installed`, `test_t05_runtime_user_is_appuser`, `test_t09_pytest_not_installed`, `test_t13_celery_cli_is_installed` | Real | PASS |
| ST-BNDRY-045-001 | FR-029 | VS-4: non-root user (UID=1000) | `test_t08_runtime_uid_is_1000` | Real | PASS |
| ST-BNDRY-045-002 | FR-029 | VS-3: HEALTHCHECK timing boundary (interval/timeout/retries) | `test_t07_healthcheck_timing_values` | Real | PASS |
| ST-BNDRY-045-003 | FR-029 | VS-2: no EXPOSE (broker-only, no inbound ports) | `test_t10_no_exposed_ports` | Real | PASS |
| ST-BNDRY-045-004 | FR-029 | VS-3: HEALTHCHECK targets local worker (-d celery@$HOSTNAME) | `test_t12_healthcheck_targets_local_worker` | Real | PASS |
| ST-BNDRY-045-005 | FR-029 | VS-1: build fails when Dockerfile absent | `test_t06_build_fails_without_dockerfile` | Real | PASS |

---

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 9 |
| Passed | 9 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
