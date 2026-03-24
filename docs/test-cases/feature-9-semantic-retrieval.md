# 测试用例集: Semantic Retrieval (Vector)

**Feature ID**: 9
**关联需求**: FR-007（Semantic Retrieval）
**日期**: 2026-03-24
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 4 |
| boundary | 3 |
| **合计** | **7** |

---

### 用例编号

ST-FUNC-009-001

### 关联需求

FR-007（Semantic Retrieval）

### 测试目标

验证 vector_code_search 能通过语义相似度检索代码块，即使查询词与结果不完全匹配

### 前置条件

- Qdrant 集群已启动，code_embeddings 集合已创建
- EmbeddingEncoder 已配置并可正常编码
- 集合中包含关于 HTTP 超时配置的代码块嵌入向量
- Retriever 实例已注入 EmbeddingEncoder 和 QdrantClientWrapper

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构建 mock EmbeddingEncoder 返回固定 1024 维向量；构建 mock Qdrant 返回 3 个包含 HTTP 超时相关代码的 ScoredPoint（symbol: configureTimeout, setReadTimeout, getClient） | Mock 对象正确配置 |
| 2 | 调用 vector_code_search("how to configure spring http client timeout", "repo-1") | 返回 list[ScoredChunk]，长度为 3 |
| 3 | 检查返回结果的 content_type 字段 | 所有结果的 content_type == "code" |
| 4 | 检查返回结果的 score 字段 | 所有 score 值在 0.0 到 1.0 之间（余弦相似度） |
| 5 | 验证 EmbeddingEncoder.encode_query 被正确调用 | encode_query 以查询字符串为参数被调用一次 |

### 验证点

- 返回的 ScoredChunk 列表包含 3 个结果
- 所有结果的 content_type 均为 "code"
- 分数为余弦相似度值（0.0 至 1.0）
- EmbeddingEncoder.encode_query 被调用一次

### 后置检查

- 无需清理（只读查询操作）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_vector_retrieval.py::test_vector_code_search_returns_scored_chunks
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-009-002

### 关联需求

FR-007（Semantic Retrieval）

### 测试目标

验证 vector_code_search 能返回最多 200 个候选结果，并正确传递 limit 参数给 Qdrant

### 前置条件

- Qdrant 集群已启动，code_embeddings 集合已创建
- 集合中包含足够多的代码块嵌入向量（>= 200 条）
- Retriever 实例已注入 EmbeddingEncoder 和 QdrantClientWrapper

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构建 mock Qdrant 返回 200 个 ScoredPoint | Mock 对象正确配置 |
| 2 | 调用 vector_code_search("timeout configuration", "repo-1", top_k=200) | 返回 list[ScoredChunk] |
| 3 | 检查返回结果数量 | len(results) == 200 |
| 4 | 检查 Qdrant 查询参数中的 limit 值 | limit == 200 |

### 验证点

- 返回结果数量等于 200
- Qdrant 查询的 limit 参数为 200

### 后置检查

- 无需清理（只读查询操作）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_vector_retrieval.py::test_vector_code_search_returns_up_to_top_k
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-009-003

### 关联需求

FR-007（Semantic Retrieval）

### 测试目标

验证 Qdrant 不可达时，vector_code_search 抛出 RetrievalError 并记录降级警告日志

### 前置条件

- Qdrant 集群不可达（模拟网络故障或服务关闭）
- EmbeddingEncoder 可正常编码
- Retriever 实例已注入 EmbeddingEncoder 和 QdrantClientWrapper

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 模拟 Qdrant 抛出 ConnectionError("Connection refused") | Qdrant 客户端抛出异常 |
| 2 | 调用 vector_code_search("any query", "repo-1") | 抛出 RetrievalError 异常 |
| 3 | 检查异常消息 | 消息包含 "Qdrant search failed" |
| 4 | 检查警告日志输出 | 日志包含 "Qdrant unreachable" 和 "BM25-only" |

### 验证点

- Qdrant 不可达时抛出 RetrievalError（而非原始异常）
- 异常消息包含 "Qdrant search failed" 前缀
- 降级警告日志已记录，包含 "Qdrant unreachable" 和 "BM25-only"

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_vector_retrieval.py::test_vector_code_search_qdrant_unreachable, tests/test_vector_retrieval.py::test_vector_code_search_qdrant_unreachable_logs_warning
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-009-004

### 关联需求

FR-007（Semantic Retrieval）

### 测试目标

验证传入 branch 参数时，vector_code_search 在 Qdrant 查询中添加 branch 字段的 payload 过滤条件

### 前置条件

- Retriever 实例已注入 EmbeddingEncoder 和 QdrantClientWrapper
- Mock Qdrant 客户端已配置

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 vector_code_search("timeout", repo_id="repo-1", branch="main") | 方法正常返回 |
| 2 | 检查 Qdrant query_points 的 query_filter 参数 | Filter.must 中包含 branch 条件 |
| 3 | 验证 branch 条件的具体内容 | FieldCondition(key="branch", match=MatchValue(value="main")) |
| 4 | 调用 vector_doc_search("guide", repo_id="repo-1", branch="feature-x") | 方法正常返回 |
| 5 | 检查 vector_doc_search 的 Qdrant query_filter | Filter.must 中包含 branch="feature-x" 的 MatchValue 条件 |

### 验证点

- vector_code_search 的 branch 参数传递到 Qdrant Filter 的 MatchValue 条件
- vector_doc_search 的 branch 参数同样正确传递
- branch 字段名为 "branch"，匹配类型为 MatchValue

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_vector_retrieval.py::test_vector_code_search_branch_filter, tests/test_vector_retrieval.py::test_vector_doc_search_with_branch
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-009-001

### 关联需求

FR-007（Semantic Retrieval）

### 测试目标

验证查询无语义相似内容时，vector_code_search 返回空列表

### 前置条件

- Qdrant 集群已启动，code_embeddings 集合已创建
- 集合中不包含与查询语义相关的向量
- Retriever 实例已注入 EmbeddingEncoder 和 QdrantClientWrapper

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构建 mock Qdrant 返回空 points 列表 | Mock 对象配置完成 |
| 2 | 调用 vector_code_search("nonexistent query", "repo-1") | 返回 list[ScoredChunk] |
| 3 | 检查返回结果数量 | len(results) == 0 |
| 4 | 验证返回类型 | 返回空列表 []，而非 None 或异常 |

### 验证点

- 无匹配结果时返回空列表 []
- 不抛出异常
- 返回类型为 list（非 None）

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_vector_retrieval.py::test_vector_code_search_no_results
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-009-002

### 关联需求

FR-007（Semantic Retrieval）

### 测试目标

验证空查询字符串和仅空白字符查询时，vector_code_search 抛出 ValueError

### 前置条件

- Retriever 实例已注入 EmbeddingEncoder 和 QdrantClientWrapper

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 vector_code_search("", "repo-1") | 抛出 ValueError |
| 2 | 检查异常消息 | 消息为 "query must not be empty" |
| 3 | 调用 vector_code_search("   ", "repo-1")（仅空白字符） | 抛出 ValueError，消息为 "query must not be empty" |

### 验证点

- 空字符串查询抛出 ValueError
- 仅空白字符查询抛出 ValueError
- 异常消息明确说明原因

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_vector_retrieval.py::test_vector_code_search_empty_query, tests/test_vector_retrieval.py::test_vector_code_search_whitespace_query
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-009-003

### 关联需求

FR-007（Semantic Retrieval）

### 测试目标

验证仅传入 branch 参数（repo_id=None）时，Qdrant Filter 仅包含 branch 条件；所有过滤参数均为 None 时 query_filter 为 None

### 前置条件

- Retriever 实例已注入 EmbeddingEncoder 和 QdrantClientWrapper
- Mock Qdrant 客户端已配置

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 vector_code_search("timeout", repo_id=None, branch="develop") | 方法正常返回 |
| 2 | 检查 Qdrant query_filter | Filter.must 仅包含 1 个条件：key="branch", match=MatchValue("develop") |
| 3 | 调用 vector_code_search("timeout", repo_id=None, languages=None, branch=None) | 方法正常返回 |
| 4 | 检查 Qdrant query_filter | query_filter 为 None（无任何过滤条件） |

### 验证点

- branch-only 过滤时 Filter 仅包含 1 个 branch 条件
- 所有过滤参数为 None 时 query_filter 为 None
- branch 过滤不依赖 repo_id

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_vector_retrieval.py::test_vector_code_search_branch_only_filter, tests/test_vector_retrieval.py::test_vector_code_search_no_filters
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-009-001 | FR-007 | VS-1: 语义相关块即使无精确匹配也能返回 | test_vector_code_search_returns_scored_chunks | Mock | PASS |
| ST-FUNC-009-002 | FR-007 | VS-2: 返回最多 200 个候选结果 | test_vector_code_search_returns_up_to_top_k | Mock | PASS |
| ST-FUNC-009-003 | FR-007 | VS-3: Qdrant 不可达时抛出 RetrievalError 并记录降级警告 | test_vector_code_search_qdrant_unreachable, test_vector_code_search_qdrant_unreachable_logs_warning | Mock | PASS |
| ST-FUNC-009-004 | FR-007 | VS-4: branch 参数添加 payload 过滤 | test_vector_code_search_branch_filter, test_vector_doc_search_with_branch, **test_real_vector_search_branch_filter** | Mock + Real | PASS |
| ST-BNDRY-009-001 | FR-007 | VS-2 (边界): 无匹配结果返回空列表 | test_vector_code_search_no_results | Mock | PASS |
| ST-BNDRY-009-002 | FR-007 | (边界): 空查询抛出 ValueError | test_vector_code_search_empty_query, test_vector_code_search_whitespace_query | Mock | PASS |
| ST-BNDRY-009-003 | FR-007 | VS-4 (边界): branch-only 过滤和无过滤条件 | test_vector_code_search_branch_only_filter, test_vector_code_search_no_filters | Mock | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 1 |
| Passed | 1 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> `test_real_vector_search_branch_filter` creates a temporary Qdrant collection, inserts vectors with different `branch` payloads, and verifies that `vector_code_search(branch="main")` returns only "main" vectors — exercising the full search path against a live Qdrant instance.
