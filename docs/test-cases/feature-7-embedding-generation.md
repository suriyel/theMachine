# 测试用例集: Embedding Generation

**Feature ID**: 7
**关联需求**: FR-005（Embedding Generation）
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

ST-FUNC-007-001

### 关联需求

FR-005（Embedding Generation）

### 测试目标

验证 encode_batch 对10个代码块生成10个1024维float32向量

### 前置条件

- EmbeddingEncoder 已初始化（使用 mock 模型）
- 10个不同内容的代码块文本准备好

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 初始化 EmbeddingEncoder，使用 mock SentenceTransformer 模型 | 实例创建成功，batch_size=64，query_prefix 已设置 |
| 2 | 准备10个代码块文本列表 | 文本列表长度为10 |
| 3 | 调用 encode_batch(texts) | 返回长度为10的列表 |
| 4 | 检查每个向量的维度 | 每个向量形状为 (1024,) |
| 5 | 检查每个向量的数据类型 | 每个向量 dtype 为 float32 |

### 验证点

- 返回列表长度等于输入文本数量（10）
- 每个向量维度为1024
- 每个向量数据类型为float32

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_embedding_encoder.py::test_encode_batch_returns_correct_count_and_dimensions
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-007-002

### 关联需求

FR-005（Embedding Generation）

### 测试目标

验证 encode_query 对查询字符串添加指令前缀并返回单个1024维向量

### 前置条件

- EmbeddingEncoder 已初始化
- 查询字符串 "how to configure timeout" 准备好

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 encode_query("how to configure timeout") | 返回单个 ndarray |
| 2 | 检查向量维度 | 形状为 (1024,) |
| 3 | 检查向量 dtype | dtype 为 float32 |
| 4 | 检查传入模型的文本 | 文本以 "Represent this code search query: " 开头 |

### 验证点

- 返回值为单个1024维float32向量
- 模型接收到的文本包含查询指令前缀 "Represent this code search query: "

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_embedding_encoder.py::test_encode_query_prepends_prefix_and_returns_1024_dim
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-007-003

### 关联需求

FR-005（Embedding Generation）

### 测试目标

验证 write_code_chunks 将100个代码块及其嵌入向量写入 ES code_chunks 索引和 Qdrant code_embeddings 集合

### 前置条件

- IndexWriter 已初始化（使用 mock ES 和 Qdrant 客户端）
- 100个 CodeChunk 对象和对应的100个1024维嵌入向量准备好

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 准备100个 CodeChunk 和100个1024维 ndarray 向量 | 数据准备完成 |
| 2 | 调用 write_code_chunks(chunks, embeddings, repo_id) | 方法正常返回（无异常） |
| 3 | 检查 ES bulk 调用 | bulk 被调用，操作包含 "code_chunks" 索引 |
| 4 | 检查 Qdrant upsert 调用 | upsert 被调用，集合名为 "code_embeddings" |
| 5 | 检查 Qdrant payload 包含元数据 | payload 包含 repo_id, file_path, language, chunk_type, symbol, branch |

### 验证点

- ES bulk 写入目标索引为 "code_chunks"
- Qdrant upsert 目标集合为 "code_embeddings"
- 所有100个块的数据均被提交

### 后置检查

- 无需清理（mock 客户端）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_index_writer.py::test_write_code_chunks_stores_all_in_es_and_qdrant
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-007-001

### 关联需求

FR-005（Embedding Generation）

### 测试目标

验证 encode_batch 空列表输入抛出 ValueError，模型推理失败抛出 EmbeddingModelError

### 前置条件

- EmbeddingEncoder 已初始化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 encode_batch([]) | 抛出 ValueError，消息包含 "texts must be non-empty" |
| 2 | 调用 encode_query("") | 抛出 ValueError，消息包含 "query must be non-empty" |
| 3 | 模拟模型 encode 抛出 RuntimeError("CUDA out of memory") | 抛出 EmbeddingModelError，消息包含 "Model inference failed" |
| 4 | 调用 encode_batch(["single"]) 单元素列表 | 返回长度为1的列表，向量 (1024,) float32 |

### 验证点

- 空输入正确抛出 ValueError
- 模型错误正确包装为 EmbeddingModelError
- 单元素边界条件正常工作

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_embedding_encoder.py::test_encode_batch_empty_texts_raises_value_error, tests/test_embedding_encoder.py::test_encode_query_empty_string_raises_value_error, tests/test_embedding_encoder.py::test_encode_batch_model_failure_raises_embedding_model_error, tests/test_embedding_encoder.py::test_encode_batch_single_text_returns_one_vector
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-007-002

### 关联需求

FR-005（Embedding Generation）

### 测试目标

验证 IndexWriter 在 ES/Qdrant 不可达时重试3次后抛出 IndexWriteError，以及空列表和长度不匹配的边界处理

### 前置条件

- IndexWriter 已初始化（使用 mock 客户端）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Qdrant upsert 连续抛出3次 ConnectionError | 抛出 IndexWriteError，消息包含 "failed after 3 retries" |
| 2 | ES bulk 连续抛出3次 ConnectionError | 抛出 IndexWriteError，消息包含 "failed after 3 retries" |
| 3 | Qdrant upsert 失败2次后第3次成功 | 方法正常返回，无异常 |
| 4 | 调用 write_code_chunks([], []) 空列表 | 无操作，ES/Qdrant 均未被调用 |
| 5 | 调用 write_code_chunks(chunks_5, embeddings_3) 长度不匹配 | 抛出 ValueError，消息包含 "same length" |
| 6 | 重试使用指数退避延迟 | sleep 调用参数为 1.0s 和 2.0s |

### 验证点

- 3次重试后抛出 IndexWriteError
- 重试使用指数退避（2^attempt * 0.5）
- 空列表正确处理为无操作
- 长度不匹配正确抛出 ValueError

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_index_writer.py::test_write_code_chunks_qdrant_unreachable_retries_and_fails, tests/test_index_writer.py::test_write_code_chunks_es_unreachable_retries_and_fails, tests/test_index_writer.py::test_write_code_chunks_qdrant_succeeds_on_third_retry, tests/test_index_writer.py::test_write_code_chunks_empty_is_noop, tests/test_index_writer.py::test_write_code_chunks_length_mismatch_raises_value_error, tests/test_index_writer.py::test_retry_write_uses_exponential_backoff
- **Test Type**: Mock

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-007-001 | FR-005 | Given a list of 10 code chunks, when encode_documents() runs in batch, then it produces 10 vectors of 1024 dimensions each as float32 arrays | test_encode_batch_returns_correct_count_and_dimensions | Mock | PASS |
| ST-FUNC-007-002 | FR-005 | Given a query string 'how to configure timeout', when encode_query() runs, then it prepends 'Represent this code search query: ' and returns a single 1024-dim vector | test_encode_query_prepends_prefix_and_returns_1024_dim | Mock | PASS |
| ST-FUNC-007-003 | FR-005 | Given 100 chunks with embeddings, when IndexWriter.write_code_chunks() runs, then all 100 vectors are stored in the Qdrant 'code_embeddings' collection with correct payload metadata | test_write_code_chunks_stores_all_in_es_and_qdrant | Mock | PASS |
| ST-BNDRY-007-001 | FR-005 | Error handling: empty input, model failure, single element boundary | test_encode_batch_empty_texts_raises_value_error + 3 more | Mock | PASS |
| ST-BNDRY-007-002 | FR-005 | Error handling: retry, backoff, empty list no-op, length mismatch | test_write_code_chunks_qdrant_unreachable_retries_and_fails + 5 more | Mock | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 0 |
| Passed | 0 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Feature #7 is an internal indexing component — acceptance tests verify via unit test execution against mocked external services. Real integration tests exist separately (@pytest.mark.real) for Qdrant connectivity and sentence-transformers encoding.
