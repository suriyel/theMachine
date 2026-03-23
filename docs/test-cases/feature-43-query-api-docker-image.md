# 测试用例集: query-api Docker Image

**Feature ID**: 43
**关联需求**: FR-027, NFR-012
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

ST-FUNC-043-001

### 关联需求

FR-027（query-api Docker Image — Build exits 0）

### 测试目标

验证 `docker build -f docker/Dockerfile.api -t codecontext-api .` 构建成功退出 0，且本地 Docker daemon 中存在 `codecontext-api` 镜像。

### 前置条件

- Docker daemon 正在运行
- 工作目录为项目根 `/home/machine/code/theMachine`
- `docker/Dockerfile.api` 文件存在
- 网络可访问 Docker Hub（用于拉取 `python:3.11-slim`），或本地缓存中已有该基础镜像

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 在项目根目录执行 `docker build -f docker/Dockerfile.api -t codecontext-api .` | 构建开始，逐层打印 Docker layer 日志 |
| 2 | 等待构建完成，检查退出码 `echo "exit:$?"` | 退出码为 `0` |
| 3 | 执行 `docker image ls codecontext-api --format "{{.Repository}}:{{.Tag}}"` | 输出包含 `codecontext-api:latest`（或同名镜像） |

### 验证点

- `docker build` 命令退出码 = 0
- `docker image ls codecontext-api` 返回非空结果

### 后置检查

- 构建完成后保留镜像供后续用例使用（ST-FUNC-043-002 至 ST-FUNC-043-004、ST-BNDRY-043-001 至 ST-BNDRY-043-003）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: No
- **测试引用**: N/A（Docker 集成测试，手动执行）
- **Test Type**: Real

---

### 用例编号

ST-FUNC-043-002

### 关联需求

FR-027（query-api Docker Image — 容器启动后 /api/v1/health 返回 200）

### 测试目标

验证使用所需环境变量运行 `codecontext-api` 容器后，30 秒内 `GET /api/v1/health` 返回 HTTP 200。

### 前置条件

- `codecontext-api` 镜像已成功构建（ST-FUNC-043-001 通过）
- 外部依赖服务正在运行：PostgreSQL(5432)、Elasticsearch(9200)、Qdrant(6333)、Redis(6379)
- `.env` 文件包含所有必需环境变量（`DATABASE_URL`、`ELASTICSEARCH_URL`、`QDRANT_URL`、`REDIS_URL`、`SECRET_KEY`）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 启动外部服务：`docker start postgres redis qdrant elasticsearch` | 所有容器状态为 `Up` |
| 2 | 验证外部服务健康：`pg_isready -h localhost -p 5432`；`curl -sf http://localhost:9200/_cluster/health`；`curl -sf http://localhost:6333/healthz`；`redis-cli ping` | 均返回成功/PONG |
| 3 | 运行容器（传入所有 env vars，映射 8000 端口）：`docker run -d --name test-api-43 --network host --env-file .env codecontext-api` | 容器以 detach 模式启动，打印容器 ID |
| 4 | 等待最多 30 秒轮询健康端点：`for i in $(seq 1 30); do curl -sf http://localhost:8000/api/v1/health && break || sleep 1; done` | 在 30 秒内收到 HTTP 200 响应 |
| 5 | 检查响应体：`curl -sf http://localhost:8000/api/v1/health` | 响应 HTTP 状态码为 200；响应体符合 health schema（含 `"status"` 字段或类似结构） |

### 验证点

- HTTP 200 在 30 秒内返回
- 服务正常启动（无 `SystemExit`、无 `KeyError` crash）

### 后置检查

- 测试结束后停止并删除容器：`docker stop test-api-43 && docker rm test-api-43`

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: No
- **测试引用**: N/A（Docker 集成测试，手动执行）
- **Test Type**: Real

---

### 用例编号

ST-FUNC-043-003

### 关联需求

FR-027（query-api Docker Image — HEALTHCHECK 指令存在且目标 port 8000）

### 测试目标

验证构建的 `codecontext-api` 镜像中含有 HEALTHCHECK 指令，且该指令目标为 port 8000。

### 前置条件

- `codecontext-api` 镜像已成功构建（ST-FUNC-043-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `docker inspect codecontext-api --format "{{json .Config.Healthcheck}}"` | 输出 JSON 对象，非 `null` |
| 2 | 从输出中提取 `Test` 数组：检查是否包含字符串 `8000` | `Test` 数组中包含引用 `http://localhost:8000/api/v1/health` 或 `8000` 的字符串 |
| 3 | 检查 `--interval`、`--timeout`、`--retries`：`docker inspect codecontext-api --format "{{json .Config.Healthcheck}}"` | `Interval` = 30s（30000000000ns）；`Timeout` = 10s；`Retries` = 3 |

### 验证点

- `.Config.Healthcheck` 非 `null`
- `Healthcheck.Test` 包含 `8000`
- `Healthcheck.Interval` = 30000000000（30s in nanoseconds）

### 后置检查

- 无（镜像仍保留供后续用例使用）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: No
- **测试引用**: N/A（Docker inspect，手动执行）
- **Test Type**: Real

---

### 用例编号

ST-FUNC-043-004

### 关联需求

FR-027（query-api Docker Image — 仅含生产依赖，无 pytest/mutmut）

### 测试目标

验证构建的镜像中不含开发依赖（pytest、mutmut、dev extras），仅含生产依赖。

### 前置条件

- `codecontext-api` 镜像已成功构建（ST-FUNC-043-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `docker run --rm codecontext-api pip show pytest; echo "exit:$?"` | 退出码非 0（pytest 未安装），输出含 `WARNING: Package(s) not found: pytest` 或类似 |
| 2 | 执行 `docker run --rm codecontext-api pip show mutmut; echo "exit:$?"` | 退出码非 0（mutmut 未安装） |
| 3 | 执行 `docker run --rm codecontext-api pip show fastapi; echo "exit:$?"` | 退出码为 0（fastapi 已安装——生产依赖存在） |
| 4 | 执行 `docker run --rm codecontext-api pip show uvicorn; echo "exit:$?"` | 退出码为 0（uvicorn 已安装） |

### 验证点

- `pip show pytest` 退出码 ≠ 0
- `pip show mutmut` 退出码 ≠ 0
- `pip show fastapi` 退出码 = 0（生产依赖存在）

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: No
- **测试引用**: N/A（Docker run，手动执行）
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-043-001

### 关联需求

FR-027（query-api Docker Image — 以非 root 用户运行，UID != 0）

### 测试目标

验证容器以非 root 用户（`appuser`，UID 1000）运行，UID 不为 0。

### 前置条件

- `codecontext-api` 镜像已成功构建（ST-FUNC-043-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `docker run --rm codecontext-api id -u` | 输出为 `1000`（非 `0`） |
| 2 | 执行 `docker run --rm codecontext-api id -un` | 输出为 `appuser` |
| 3 | 确认 UID 不为 0：将步骤 1 输出与 `0` 比较 | UID ≠ 0（满足 FR-027 AC-5） |

### 验证点

- `id -u` 输出 = `1000`
- `id -un` 输出 = `appuser`
- UID ≠ 0

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: No
- **测试引用**: N/A（Docker run，手动执行）
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-043-002

### 关联需求

FR-027（query-api Docker Image — 缺少必需环境变量时容器启动失败并退出非零）

### 测试目标

验证当必需环境变量（如 `DATABASE_URL`）缺失时，容器启动失败并以非零退出码退出，不会卡住或崩溃而无提示。

### 前置条件

- `codecontext-api` 镜像已成功构建（ST-FUNC-043-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 运行容器，故意不传 `DATABASE_URL`：`docker run --rm -e ELASTICSEARCH_URL=http://localhost:9200 -e QDRANT_URL=http://localhost:6333 -e REDIS_URL=redis://localhost:6379/0 -e SECRET_KEY=testkey codecontext-api` | 容器启动后快速退出（不会永久阻塞） |
| 2 | 检查容器退出码：`echo "exit:$?"` | 退出码为 `1`（非零） |
| 3 | 检查容器日志中的错误信息（如果有输出）：`docker logs <container_id>` 或 stdout 捕获 | 日志中含有 `DATABASE_URL` 或类似的缺失变量名称信息 |

### 验证点

- 容器进程退出码 ≠ 0
- 容器不会无限期运行（应在数秒内退出）

### 后置检查

- 无（容器以 `--rm` 自动删除）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: No
- **测试引用**: N/A（Docker run，手动执行）
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-043-003

### 关联需求

FR-027（query-api Docker Image — 基础镜像为 python:3.11-slim，非 alpine/full）

### 测试目标

验证构建的镜像基于 `python:3.11-slim`，确认 Python 版本为 3.11.x 且镜像架构符合 slim 变体特征（无多余系统包）。

### 前置条件

- `codecontext-api` 镜像已成功构建（ST-FUNC-043-001 通过）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `docker run --rm codecontext-api python --version` | 输出包含 `Python 3.11.` 开头（3.11.x 系列） |
| 2 | 检查镜像 OS 标识：`docker inspect codecontext-api --format "{{.Os}}/{{.Architecture}}"` | 输出 `linux/amd64`（或宿主机架构） |
| 3 | 检查 Docker file FROM 行：`docker history codecontext-api --no-trunc` | 历史记录中含 `python:3.11-slim` 基础层 |

### 验证点

- Python 版本为 3.11.x
- OS 为 linux
- 基础镜像层可追溯至 `python:3.11-slim`

### 后置检查

- 所有测试完成后：执行清理 `docker rmi codecontext-api` 或保留供后续 ST 轮次使用

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: No
- **测试引用**: N/A（Docker inspect，手动执行）
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-043-001 | FR-027 | VS-1: docker build exits 0 | N/A | Real | PASS |
| ST-FUNC-043-002 | FR-027 | VS-2: GET /api/v1/health returns 200 within 30s | N/A | Real | PASS |
| ST-FUNC-043-003 | FR-027 | VS-3: HEALTHCHECK targeting port 8000 | N/A | Real | PASS |
| ST-FUNC-043-004 | FR-027 | VS-4: no pytest or dev extras | N/A | Real | PASS |
| ST-BNDRY-043-001 | FR-027 | VS-5: runs as non-root user (UID != 0) | N/A | Real | PASS |
| ST-BNDRY-043-002 | FR-027 | VS-2 (error path: missing env var) | N/A | Real | PASS |
| ST-BNDRY-043-003 | FR-027 | VS-1 (base image boundary: python:3.11-slim) | N/A | Real | PASS |

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
