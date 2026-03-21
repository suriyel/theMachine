# 测试用例集: Semantic Retrieval (Vector)

**Feature ID**: 9
**关联需求**: FR-007（Semantic Retrieval）
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

ST-FUNC-009-001

### 关联需求

FR-007（Semantic Retrieval）

### 测试目标

验证 vector_code_search 能通过语义相似度检索代码块，即使查询词与结果不完全匹配

### 前置条件

- Qdrant 集群已启动，code_embeddings 集合已创建
- EmbeddingEncoder 已配置 DashScope API 密钥并可正常编码
- 集合中包含关于 HTTP 超时配置的代码块嵌入向量
- Retriever 实例已注入 EmbeddingEncoder 和 QdrantClientWrapper

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 vector_code_search("how to configure spring http client timeout", "repo-1") | 返回 list[ScoredChunk]，非空 |
| 2 | 检查返回结果的 content_type 字段 | 所有结果的 content_type == "code" |
| 3 | 检查返回结果的 score 字段 | 所有 score 值在 0.0 到 1.0 之间（余弦相似度） |
| 4 | 检查返回结果中是否包含语义相关的代码块 | 即使查询词 "spring http client timeout" 未出现在代码中，语义相关的块（如 WebClient.Builder, responseTimeout）仍然出现在结果中 |

### 验证点

- 返回的 ScoredChunk 列表非空
- 所有结果的 content_type 均为 "code"
- 分数为余弦相似度值（0.0 至 1.0）
- 返回结果包含语义相关但非关键词匹配的代码块

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

验证 vector_code_search 能返回最多 200 个候选结果，按余弦相似度降序排列

### 前置条件

- Qdrant 集群已启动，code_embeddings 集合已创建
- 集合中包含足够多的代码块嵌入向量（>= 200 条）
- Retriever 实例已注入 EmbeddingEncoder 和 QdrantClientWrapper

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 vector_code_search("timeout configuration", "repo-1", top_k=200) | 返回 list[ScoredChunk] |
| 2 | 检查返回结果数量 | len(results) <= 200 |
| 3 | 检查 Qdrant 查询参数中的 limit 值 | limit == 200 |
| 4 | 检查每个结果的必要字段 | chunk_id, repo_id, file_path, content, score 均非空 |

### 验证点

- 返回结果数量不超过 top_k=200
- Qdrant 查询的 limit 参数正确传递
- 每个 ScoredChunk 包含所有必要字段

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

验证 Qdrant 不可达时，vector_code_search 抛出 RetrievalError 以便调用方降级到 BM25

### 前置条件

- Qdrant 集群不可达（模拟网络故障或服务关闭）
- EmbeddingEncoder 可正常编码
- Retriever 实例已注入 EmbeddingEncoder 和 QdrantClientWrapper

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 模拟 Qdrant 连接错误（ConnectionError / RpcError / UnexpectedResponse） | Qdrant 客户端抛出异常 |
| 2 | 调用 vector_code_search("any query", "repo-1") | 抛出 RetrievalError 异常 |
| 3 | 检查异常消息 | 消息包含 "Qdrant search failed" |
| 4 | 验证异常链 | RetrievalError 的 __cause__ 是原始 Qdrant 异常 |

### 验证点

- Qdrant 不可达时抛出 RetrievalError（而非原始异常）
- 异常消息包含 "Qdrant search failed" 前缀
- 调用方可根据 RetrievalError 类型进行降级处理

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_vector_retrieval.py::test_vector_code_search_qdrant_unreachable
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
| 1 | 调用 vector_code_search("completely irrelevant gibberish query xyz", "repo-1") | 返回 list[ScoredChunk] |
| 2 | 检查返回结果数量 | len(results) == 0 |
| 3 | 验证返回类型 | 返回空列表 []，而非 None 或异常 |

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

验证空查询字符串时，vector_code_search 抛出 ValueError

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

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-009-001 | FR-007 | VS-1: 语义相关块即使无精确匹配也能返回 | test_vector_code_search_returns_scored_chunks | Mock | PASS |
| ST-FUNC-009-002 | FR-007 | VS-2: 返回最多 200 个候选结果 | test_vector_code_search_returns_up_to_top_k | Mock | PASS |
| ST-FUNC-009-003 | FR-007 | VS-3: Qdrant 不可达时抛出 RetrievalError | test_vector_code_search_qdrant_unreachable | Mock | PASS |
| ST-BNDRY-009-001 | FR-007 | VS-2 (边界): 无匹配结果返回空列表 | test_vector_code_search_no_results | Mock | PASS |
| ST-BNDRY-009-002 | FR-007 | (边界): 空查询抛出 ValueError | test_vector_code_search_empty_query | Mock | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 0 |
| Passed | 0 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Note: Feature #9 is a pure retrieval module with no direct service endpoint. All test cases exercise the Retriever class with mocked external dependencies (Qdrant, EmbeddingEncoder). Real connectivity is verified by the integration test `test_qdrant_connectivity_real` in the unit test suite.
