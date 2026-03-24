# 签收验证策略 — Code Context Retrieval MCP System

**Date**: 2026-03-24
**Version**: 0.1.0
**Status**: Go (ST Report: docs/plans/2026-03-24-st-report.md)
**目标仓库**: suriyel/githubtrends (2071 chunks, Python + TypeScript)

---

## 1. 验证环境准备

### 1.1 前置条件

| 项目 | 要求 | 验证命令 |
|------|------|----------|
| Python | ≥ 3.11 | `python3 --version` |
| Docker | 已安装 | `docker --version` |
| 外部服务 | PostgreSQL, Elasticsearch, Qdrant, Redis, RabbitMQ | 见 1.2 |
| 项目环境 | venv 已创建、依赖已安装 | `source .venv/bin/activate && python -c "import fastapi"` |
| 配置文件 | `.env` 已填写 | `cat .env | grep -c '='` (应 ≥ 15 项) |

### 1.2 启动外部服务

```bash
docker start postgres redis qdrant elasticsearch rabbitmq
```

验证：

```bash
pg_isready -h localhost -p 5432             # → accepting connections
curl -sf http://localhost:9200/_cluster/health | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])"   # → green
curl -sf http://localhost:6333/healthz       # → healthz check passed
redis-cli ping                               # → PONG
docker exec rabbitmq rabbitmqctl status 2>&1 | head -1   # → Status of node
```

### 1.3 环境配置 (.env)

以下为关键配置项，确认均已填写：

```bash
# 核心服务
DATABASE_URL=postgresql+asyncpg://...
ELASTICSEARCH_URL=http://localhost:9200
QDRANT_URL=http://localhost:6333
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=<随机32字节hex>

# Embedding (text-embedding-v3, 1024-dim)
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_API_KEY=<dashscope-key>
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# Reranker (qwen3-rerank, OpenAI-compatible)
RERANKER_MODEL=qwen3-rerank
RERANKER_API_KEY=<dashscope-key>
RERANKER_BASE_URL=https://dashscope.aliyuncs.com/compatible-api/v1
RERANKER_THRESHOLD=0.3

# 超时 (远程 API 需要更长超时)
SEARCH_TIMEOUT=5.0
PIPELINE_TIMEOUT=15.0
```

### 1.4 启动应用服务

```bash
source .venv/bin/activate
set -a && source .env && set +a

# 启动 query-api (清理代理以访问 localhost)
env -u ALL_PROXY -u all_proxy uvicorn --factory src.query.main:build_app --host 0.0.0.0 --port 8000 &

# 等待启动
sleep 5
```

### 1.5 创建 API Key

```bash
python3 -c "
import asyncio, os
from src.shared.database import get_engine, get_session_factory
from src.shared.services.api_key_manager import APIKeyManager
async def create():
    engine = get_engine(os.environ['DATABASE_URL'])
    sf = get_session_factory(engine)
    mgr = APIKeyManager(sf, redis_client=None)
    key, _ = await mgr.create_key(name='ats-key', role='admin')
    print(f'export DEMO_API_KEY={key}')
    await engine.dispose()
asyncio.run(create())
"
```

执行输出的 `export` 命令设置环境变量。

---

## 2. 签收验证项

### ATS-001 健康检查

**需求**: 系统启动后所有依赖服务连通
**对应**: FR-015, NFR-005

```bash
curl -sf http://localhost:8000/api/v1/health | python3 -m json.tool
```

**通过标准**:
- [ ] HTTP 200
- [ ] `status` = `"healthy"`
- [ ] `services.elasticsearch` = `"up"`
- [ ] `services.qdrant` = `"up"`
- [ ] `services.redis` = `"up"`
- [ ] `services.postgresql` = `"up"`

---

### ATS-002 认证拦截

**需求**: 无 API Key 的请求被拒绝
**对应**: FR-014, NFR-009

```bash
# 无 Key
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}' -w "\nHTTP %{http_code}\n"

# 错误 Key
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" -H "X-API-Key: invalid-key-xxx" \
  -d '{"query": "test"}' -w "\nHTTP %{http_code}\n"
```

**通过标准**:
- [ ] 无 Key → HTTP 401, body 含 `"Missing API key"` 或 `"Invalid API key"`
- [ ] 错误 Key → HTTP 401, body 含 `"Invalid API key"`
- [ ] 健康检查和 `/metrics` 无需认证 → HTTP 200

---

### ATS-003 仓库注册

**需求**: 注册 Git 仓库并触发索引
**对应**: FR-001, FR-002

```bash
# 注册
curl -s -X POST http://localhost:8000/api/v1/repos \
  -H "Content-Type: application/json" -H "X-API-Key: $DEMO_API_KEY" \
  -d '{"url": "https://github.com/suriyel/githubtrends"}' | python3 -m json.tool

# 重复注册
curl -s -X POST http://localhost:8000/api/v1/repos \
  -H "Content-Type: application/json" -H "X-API-Key: $DEMO_API_KEY" \
  -d '{"url": "https://github.com/suriyel/githubtrends"}' -w "\nHTTP %{http_code}\n"

# 无效 URL
curl -s -X POST http://localhost:8000/api/v1/repos \
  -H "Content-Type: application/json" -H "X-API-Key: $DEMO_API_KEY" \
  -d '{"url": "not-a-url"}' -w "\nHTTP %{http_code}\n"

# 查看仓库列表
curl -s http://localhost:8000/api/v1/repos \
  -H "X-API-Key: $DEMO_API_KEY" | python3 -m json.tool
```

**通过标准**:
- [ ] 首次注册 → HTTP 200, 返回含 `id`, `name`, `status="pending"` 的 JSON
- [ ] 重复注册 → HTTP 409, 含 `"already registered"`
- [ ] 无效 URL → HTTP 400, 含错误描述
- [ ] 仓库列表 → HTTP 200, 含已注册仓库

---

### ATS-004 索引管线（Clone → Extract → Chunk → Embed → Write）

**需求**: 仓库内容被完整索引到 ES + Qdrant
**对应**: FR-002, FR-003, FR-004, FR-005, CON-001, CON-009, CON-010

> 注意: 当前版本索引通过手动脚本触发，生产环境由 Celery Worker 自动处理。

索引完成后验证：

```bash
# ES 代码块数量
curl -sf "http://localhost:9200/code_chunks/_count" | python3 -c "import sys,json; print(f'code_chunks: {json.load(sys.stdin)[\"count\"]}')"

# ES 文档块数量
curl -sf "http://localhost:9200/doc_chunks/_count" | python3 -c "import sys,json; print(f'doc_chunks: {json.load(sys.stdin)[\"count\"]}')"

# Qdrant 向量数量
curl -sf "http://localhost:6333/collections/code_embeddings" | python3 -c "import sys,json; d=json.load(sys.stdin)['result']; print(f'code_embeddings: {d[\"points_count\"]} points, dim={d[\"config\"][\"params\"][\"vectors\"][\"size\"]}')"
curl -sf "http://localhost:6333/collections/doc_embeddings" | python3 -c "import sys,json; d=json.load(sys.stdin)['result']; print(f'doc_embeddings: {d[\"points_count\"]} points')"
```

**通过标准** (以 suriyel/githubtrends 为例):
- [ ] `code_chunks` ≥ 500 (实测 564)
- [ ] `doc_chunks` ≥ 1000 (实测 1506)
- [ ] `code_embeddings` points = `code_chunks` count
- [ ] `doc_embeddings` points = `doc_chunks` count
- [ ] 向量维度 = 1024

---

### ATS-005 自然语言检索（全管线）

**需求**: BM25 + Vector + RRF + qwen3-rerank 端到端工作
**对应**: FR-006, FR-007, FR-008, FR-009, FR-010, FR-011

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" -H "X-API-Key: $DEMO_API_KEY" \
  -d '{"query": "weekly report generation"}' | python3 -m json.tool
```

**通过标准**:
- [ ] `degraded` = `false` (四路检索全通，未降级)
- [ ] `query_type` = `"nl"`
- [ ] `code_results` 非空，Top-1 为 `_generate_report` 函数
- [ ] `doc_results` 非空，含 report generation 相关文档
- [ ] 每条结果含 `file_path`, `content`, `relevance_score`
- [ ] `relevance_score` 合理 (Top-1 > 0.5)

---

### ATS-006 语言过滤检索

**需求**: 按编程语言过滤检索结果
**对应**: FR-018, CON-001

```bash
# Python only
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" -H "X-API-Key: $DEMO_API_KEY" \
  -d '{"query": "github API rate limit retry", "languages": ["python"]}' | python3 -c "
import sys,json; d=json.load(sys.stdin)
for r in d['code_results']:
    print(f'{r[\"language\"]}  {r[\"file_path\"]}::{r.get(\"symbol\",\"-\")}')
"

# TypeScript only
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" -H "X-API-Key: $DEMO_API_KEY" \
  -d '{"query": "React dashboard component", "languages": ["typescript"]}' | python3 -c "
import sys,json; d=json.load(sys.stdin)
for r in d['code_results']:
    print(f'{r[\"language\"]}  {r[\"file_path\"]}::{r.get(\"symbol\",\"-\")}')
"
```

**通过标准**:
- [ ] Python 查询 → `code_results` 中所有 `language` = `"python"`
- [ ] TypeScript 查询 → `code_results` 中所有 `language` = `"typescript"`
- [ ] 两次查询均 `degraded` = `false`

---

### ATS-007 符号查询（自动检测）

**需求**: 类名/函数名自动识别为符号查询，走 BM25 优先路径
**对应**: FR-012

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" -H "X-API-Key: $DEMO_API_KEY" \
  -d '{"query": "GitHubService"}' | python3 -m json.tool
```

**通过标准**:
- [ ] `query_type` = `"symbol"` (PascalCase 自动检测)
- [ ] Top-1 结果为 `class GitHubService` 定义 (file: `github_service.py`)
- [ ] `relevance_score` > 0.8 (精确匹配应有高分)

---

### ATS-008 仓库作用域检索

**需求**: 按仓库名限定检索范围
**对应**: FR-013

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" -H "X-API-Key: $DEMO_API_KEY" \
  -d '{"query": "deploy docker", "repo_id": "suriyel/githubtrends"}' | python3 -m json.tool
```

**通过标准**:
- [ ] 所有结果的 `file_path` 均来自 githubtrends 仓库
- [ ] 返回 Docker 部署相关文档

---

### ATS-009 文档检索

**需求**: README、设计文档、部署文档可被检索
**对应**: FR-003, FR-010

```bash
curl -s -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" -H "X-API-Key: $DEMO_API_KEY" \
  -d '{"query": "how to deploy with Docker"}' | python3 -c "
import sys,json; d=json.load(sys.stdin)
print(f'code={len(d[\"code_results\"])} doc={len(d[\"doc_results\"])}')
for r in d['doc_results'][:3]:
    print(f'  {r[\"file_path\"]}  score={r[\"relevance_score\"]:.4f}')
    print(f'    {r[\"content\"][:80]}...')
"
```

**通过标准**:
- [ ] `doc_results` 非空
- [ ] Top-1 含 Feature 29 Docker deployment 文档
- [ ] 文档内容包含 Dockerfile / docker-compose 相关描述

---

### ATS-010 MCP 工具调用

**需求**: MCP Server 暴露与 REST 相同的检索能力
**对应**: FR-016, IFR-001, CON-004

```bash
python3 examples/46-live-retrieval-demo.py --mcp
```

或手动验证 MCP 三个工具:

```python
# search_code_context — 与 REST /api/v1/query 相同管线
# list_repositories   — 列出已注册仓库
# get_chunk           — 按 chunk_id 获取完整内容
```

**通过标准**:
- [ ] `list_repositories()` 返回已注册仓库列表
- [ ] `search_code_context("weekly report")` 返回代码 + 文档结果
- [ ] `search_code_context("", ...)` 空查询 → ValueError
- [ ] MCP 与 REST 使用同一 QueryHandler 实例

---

### ATS-011 Prometheus 指标

**需求**: 暴露运维监控指标
**对应**: FR-021

```bash
curl -s http://localhost:8000/metrics | grep -E "^(query_latency|retrieval_latency|rerank_latency|cache_hit|index_size|query_total)" | head -10
```

**通过标准**:
- [ ] HTTP 200, 无需认证
- [ ] 含 `query_latency_seconds` (Histogram)
- [ ] 含 `retrieval_latency_seconds` (Histogram)
- [ ] 含 `rerank_latency_seconds` (Histogram)
- [ ] 含 `cache_hit_ratio` (Gauge)
- [ ] 含 `query_total` (Counter)

---

### ATS-012 Web UI

**需求**: 浏览器可访问搜索界面
**对应**: FR-017, IFR-002

```bash
# 首页可访问
curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:8000/

# 搜索页可访问
curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:8000/search
```

**通过标准**:
- [ ] `GET /` → HTTP 200, 返回 HTML 含 `<form>` 搜索表单
- [ ] `GET /search` → HTTP 200
- [ ] HTML 包含仓库下拉框、语言过滤复选框

---

### ATS-013 Docker 镜像

**需求**: 三个模块独立打包为 Docker 镜像
**对应**: FR-027, FR-028, FR-029, NFR-012

```bash
# 构建三个镜像
docker build -f docker/Dockerfile.api -t codecontext-api .
docker build -f docker/Dockerfile.mcp -t codecontext-mcp .
docker build -f docker/Dockerfile.worker -t codecontext-worker .

# 验证非 root 运行
docker run --rm codecontext-api whoami      # → appuser
docker run --rm codecontext-mcp whoami      # → appuser
docker run --rm codecontext-worker whoami   # → appuser

# 验证无开发依赖
docker run --rm codecontext-api pip list 2>&1 | grep -i "pytest\|mutmut" || echo "PASS: no dev deps"

# 验证 API 镜像健康检查
docker run -d --rm -p 18001:8000 \
  -e DATABASE_URL=postgresql+asyncpg://x:x@localhost/x \
  -e ELASTICSEARCH_URL=http://localhost:9200 \
  -e QDRANT_URL=http://localhost:6333 \
  -e REDIS_URL=redis://localhost:6379 \
  -e SECRET_KEY=test \
  codecontext-api
sleep 8
curl -sf http://localhost:18001/api/v1/health    # → {"status":"degraded",...} (200 OK)
docker stop $(docker ps -q --filter ancestor=codecontext-api)
```

**通过标准**:
- [ ] 三个镜像均构建成功 (exit 0)
- [ ] 均以 `appuser` (非 root) 运行
- [ ] 无 pytest/mutmut 等开发依赖
- [ ] API 镜像启动后 `/api/v1/health` 返回 HTTP 200

---

### ATS-014 安全扫描

**需求**: 无已知高危漏洞
**对应**: NFR-009, NFR-010

```bash
source .venv/bin/activate
pip-audit --local
bandit -r src/ -ll
```

**通过标准**:
- [ ] `pip-audit`: `No known vulnerabilities found`
- [ ] `bandit`: 0 High severity findings
- [ ] API Key 存储为 SHA-256 哈希 (非明文)

---

### ATS-015 自动化测试

**需求**: 全部测试通过，覆盖率达标
**对应**: NFR-011

```bash
source .venv/bin/activate
set -a && source .env && set +a
env -u ALL_PROXY -u all_proxy pytest tests/ --tb=short -q
```

**通过标准**:
- [ ] 0 failures
- [ ] ≥ 1100 tests passed
- [ ] Line coverage ≥ 90%
- [ ] Branch coverage ≥ 80%

---

## 3. 签收检查单

| 编号 | 验证项 | 对应需求 | 状态 |
|------|--------|----------|------|
| ATS-001 | 健康检查 — 全部服务 UP | FR-015, NFR-005 | ☐ |
| ATS-002 | 认证拦截 — 401 | FR-014, NFR-009 | ☐ |
| ATS-003 | 仓库注册 — CRUD + 冲突检测 | FR-001, FR-002 | ☐ |
| ATS-004 | 索引管线 — ES + Qdrant 数据完整 | FR-002~005, CON-001,9,10 | ☐ |
| ATS-005 | NL 检索 — 全管线 degraded=false | FR-006~011 | ☐ |
| ATS-006 | 语言过滤 — Python / TypeScript | FR-018, CON-001 | ☐ |
| ATS-007 | 符号查询 — 自动检测 + 精确匹配 | FR-012 | ☐ |
| ATS-008 | 仓库作用域 — 结果限定 | FR-013 | ☐ |
| ATS-009 | 文档检索 — README/设计文档 | FR-003, FR-010 | ☐ |
| ATS-010 | MCP 工具 — 3 tools 可用 | FR-016, IFR-001, CON-004 | ☐ |
| ATS-011 | Prometheus 指标 — 6 项 | FR-021 | ☐ |
| ATS-012 | Web UI — 搜索页可访问 | FR-017, IFR-002 | ☐ |
| ATS-013 | Docker 镜像 — 构建+非root+无dev | FR-027~029, NFR-012 | ☐ |
| ATS-014 | 安全扫描 — 0 CVE + 0 High | NFR-009, NFR-010 | ☐ |
| ATS-015 | 自动化测试 — 全绿 + 覆盖率达标 | NFR-011 | ☐ |

**签收标准**: 全部 15 项通过 → **签收通过**。任一项不通过需记录问题并修复后重验。

---

## 4. 快速验证脚本

一键执行全部验证 (需服务已启动、API Key 已设置):

```bash
export DEMO_API_KEY=<your-key>
python3 examples/46-live-retrieval-demo.py
```

该脚本覆盖 ATS-001, ATS-005~009，输出所有查询的 `degraded` 状态和 Top 结果。
