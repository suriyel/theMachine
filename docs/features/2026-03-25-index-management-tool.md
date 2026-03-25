# 索引管理工具 — 特性设计方案

**Date**: 2026-03-25
**Status**: Pending (增量需求，待纳入下一轮开发)
**Origin**: 搜索精度分析 session 发现索引管理能力缺失
**SRS Trace**: FR-019 (Scheduled Index Refresh), FR-020 (Manual Reindex Trigger)

---

## 1. 问题背景

### 1.1 直接触发

type-fest 仓库因 chunker 修复（新增 `type_alias_declaration` 支持）需要重新索引，但系统无任何可用途径执行重新索引。

### 1.2 根因分析

| # | 问题 | 位置 | 影响 |
|---|------|------|------|
| 1 | Reindex API 只创建 IndexJob 记录，不派发 Celery 任务 | `src/query/api/v1/endpoints/repos.py:108` | API 触发的重新索引永远不会执行 |
| 2 | Celery worker 缺 `psycopg2` 同步驱动 | `pyproject.toml` + `src/indexing/scheduler.py:26` | Worker 启动后处理任何任务都会崩溃 |
| 3 | `delete_repo_index()` 是死代码 | `src/indexing/index_writer.py:179` | 已实现但无入口调用 |
| 4 | `delete_repo_index()` 对 doc/rule 索引用了错误的 branch 过滤 | `src/indexing/index_writer.py:185-188` | doc_chunks/rule_chunks 不含 branch 字段，删不掉 |
| 5 | 无 CLI 索引管理工具 | `scripts/` 目录 | 无法从命令行触发重新索引、删除、统计 |

---

## 2. 修改清单

### 2.1 新建 `scripts/manage_index.py` — 异步 CLI 索引管理工具

**5 个子命令**：

| 命令 | 用法 | 功能 |
|------|------|------|
| `reindex` | `python scripts/manage_index.py reindex --repo <name-or-uuid>` | 重新索引单个仓库 |
| `reindex-all` | `python scripts/manage_index.py reindex-all` | 重新索引所有 indexed 仓库 |
| `delete` | `python scripts/manage_index.py delete --repo <name-or-uuid>` | 仅删除索引数据（ES + Qdrant） |
| `list` | `python scripts/manage_index.py list` | 列出所有仓库及索引状态 |
| `stats` | `python scripts/manage_index.py stats [--repo <name>]` | 显示各仓库的 ES/Qdrant 文档计数 |

**reindex 执行流程**：

```
DB resolve repo → delete_repo_index() → ContentExtractor.extract()
  → Chunker.chunk() (CODE)
  → DocChunker.chunk_markdown() (DOC)
  → RuleExtractor.extract_rules() (RULE)
  → EmbeddingEncoder.encode_batch() (code + doc 向量)
  → IndexWriter.write_code_chunks() + write_doc_chunks() + write_rule_chunks()
  → DB update repo.last_indexed_at
```

**复用的现有类**（不新建任何索引逻辑）：

| 类 | 文件 | 用途 |
|---|------|------|
| `IndexWriter` | `src/indexing/index_writer.py` | ES/Qdrant 批量写入 + 删除 |
| `ContentExtractor` | `src/indexing/content_extractor.py` | 文件遍历 + 分类 |
| `Chunker` | `src/indexing/chunker.py` | 代码 AST 解析 + 分块 |
| `DocChunker` | `src/indexing/doc_chunker.py` | Markdown 文档分块 |
| `RuleExtractor` | `src/indexing/rule_extractor.py` | 规则文件提取 |
| `EmbeddingEncoder` | `src/indexing/embedding_encoder.py` | 向量生成（DashScope API） |
| `ElasticsearchClient` | `src/shared/clients/elasticsearch.py` | ES 异步客户端（需 `.connect()`） |
| `QdrantClientWrapper` | `src/shared/clients/qdrant.py` | Qdrant 异步客户端（需 `.connect()`） |
| `get_engine` / `get_session_factory` | `src/shared/database.py` | 异步 DB 会话 |

**环境处理**：脚本开头清除 `ALL_PROXY`（per `env-guide.md`），手动加载 `.env`，全部 async（`asyncio.run()`）。

### 2.2 修复 `src/indexing/index_writer.py` — `delete_repo_index` bug

**问题**：`doc_chunks` / `rule_chunks` 的 ES 文档不含 `branch` 字段（`write_doc_chunks` line 124-130 未写入），但 `delete_repo_index` 对所有 3 个 ES 索引都用 `repo_id + branch` 过滤 → doc/rule 数据永远删不掉。同理 Qdrant `doc_embeddings` 也无 `branch`。

**修复**：
- `code_chunks` + `code_embeddings` → `repo_id + branch` 过滤 ✓
- `doc_chunks` + `rule_chunks` + `doc_embeddings` → 仅 `repo_id` 过滤

### 2.3 修复 `src/query/api/v1/endpoints/repos.py` — reindex 端点派发 Celery 任务

在 `IndexJob` 提交后（line ~108）增加：
```python
try:
    from src.indexing.scheduler import reindex_repo_task
    reindex_repo_task.delay(str(repo.id))
except Exception:
    pass  # Job 记录已持久化，可由 manage_index.py 或后续 worker 处理
```

### 2.4 修复 `pyproject.toml` — 添加 `psycopg2-binary`

在 `[project.optional-dependencies] dev` 中添加 `"psycopg2-binary>=2.9"`，使 Celery worker 的 `_get_sync_session()` 能正常创建同步 PostgreSQL 会话。

---

## 3. 修改文件列表

| 文件 | 操作 | 改动量 |
|------|------|--------|
| `scripts/manage_index.py` | **新建** | ~200 行 |
| `src/indexing/index_writer.py` | 修改 `delete_repo_index` | ~15 行 |
| `src/query/api/v1/endpoints/repos.py` | 添加 Celery dispatch | ~6 行 |
| `pyproject.toml` | 添加 psycopg2-binary | 1 行 |

---

## 4. 验证步骤

```bash
# 1. 安装新依赖
pip install psycopg2-binary>=2.9

# 2. 列出仓库
python scripts/manage_index.py list

# 3. 查看索引统计
python scripts/manage_index.py stats

# 4. 重新索引 type-fest（验证 TS type alias 修复生效）
python scripts/manage_index.py reindex --repo sindresorhus/type-fest

# 5. 验证搜索质量
# 启动 query-api → 查询 "Simplify" on type-fest → 应返回 type alias 定义（而非仅 README）

# 6. 运行跨仓库集成测试
env -u ALL_PROXY pytest tests/st/test_real_integration.py::TestCrossRepoSearchPrecision -v --no-cov
```

---

## 5. 约束与风险

- **Embedding API 调用量**：type-fest 有 1760 个 chunk，每批 6 个 → ~294 次 API 调用。大仓库可能更多。需要进度日志。
- **ES 磁盘水位**：重新索引前应检查 `_cluster/health`，避免在 red/yellow 状态下写入。
- **并发安全**：reindex 期间该仓库的查询可能返回不完整结果（先删后写）。生产环境需考虑蓝绿切换。
