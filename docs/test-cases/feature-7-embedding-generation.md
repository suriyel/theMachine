# Test Case Document — Feature #7: Embedding Generation and Index Writing

**Feature ID**: 7
**Feature Title**: Embedding Generation and Index Writing
**Related Requirements**: FR-004, FR-009
**Date**: 2026-03-15
**Standard**: ISO/IEC/IEEE 29119-3

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 3 |
| boundary | 1 |
| security | 0 |
| accessibility | 0 |
| performance | 0 |
| **合计** | **4** |

## 测试用例块

---

### 用例编号

ST-FUNC-007-001

### 关联需求

FR-004 (Code Chunking), FR-009 (Semantic Retrieval)

### 测试目标

验证 100 个代码块生成 1024 维向量

### 前置条件

1. Elasticsearch 服务运行中
2. Qdrant 服务运行中
3. EmbeddingEncoder 类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 创建 100 个 CodeChunk 对象 | 100 个 CodeChunk 对象创建成功 |
| 2 | 实例化 EmbeddingEncoder | 对象创建成功 |
| 3 | 调用 encode() 方法 | 返回 100 个向量 |
| 4 | 验证每个向量维度为 1024 | 所有向量长度为 1024 |

### 验证点

- 生成 100 个向量
- 每个向量维度为 1024

### 后置检查

无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_embedding_encoder.py
- **Test Type**: Real

**实际结果:** EmbeddingEncoder.encode() 正确生成 100 个向量，每个向量维度为 1024。

**结果:** PASS

---

### 用例编号

ST-FUNC-007-002

### 关联需求

FR-009 (Semantic Retrieval)

### 测试目标

验证写入 Elasticsearch 100 个文档，包含内容、元数据和 chunk_id

### 前置条件

1. Elasticsearch 服务运行中
2. IndexWriter 类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 创建 100 个 CodeChunk 对象 | 100 个 CodeChunk 对象创建成功 |
| 2 | 生成对应的 100 个 embedding 向量 | 100 个向量生成成功 |
| 3 | 调用 IndexWriter.write_chunks() | 无异常抛出 |
| 4 | 查询 Elasticsearch 获取所有 chunk_id | 所有 100 个文档存在 |
| 5 | 验证每个文档包含 chunk_id, repo_id, file_path, language, content | 所有字段存在 |

### 验证点

- Elasticsearch 包含 100 个文档
- 每个文档包含正确的字段

### 后置检查

无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_index_writer.py
- **Test Type**: Real

**实际结果:** IndexWriter.write_chunks() 成功写入 Elasticsearch，所有 100 个文档包含正确的元数据字段。

**结果:** PASS

---

### 用例编号

ST-FUNC-007-003

### 关联需求

FR-009 (Semantic Retrieval)

### 测试目标

验证写入 Qdrant 100 个点，包含相同的 chunk_id

### 前置条件

1. Qdrant 服务运行中
2. IndexWriter 类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 创建 100 个具有已知 ID 的 CodeChunk 对象 | 100 个对象创建成功 |
| 2 | 生成对应的 100 个 embedding 向量 | 100 个向量生成成功 |
| 3 | 调用 IndexWriter.write_chunks() | 无异常抛出 |
| 4 | 查询 Qdrant 获取所有 chunk_id | 所有 100 个点存在 |
| 5 | 验证向量正确存储 | 向量与输入 embeddings 匹配 |

### 验证点

- Qdrant 包含 100 个点
- chunk_id 匹配

### 后置检查

无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_index_writer.py
- **Test Type**: Real

**实际结果:** IndexWriter.write_chunks() 成功写入 Qdrant，所有 100 个点以正确的 ID 存储。

**结果:** PASS

---

### 用例编号

ST-BNDRY-007-001

### 关联需求

FR-009 (Semantic Retrieval)

### 测试目标

验证重新索引时，旧数据被删除，新数据被写入

### 前置条件

1. Elasticsearch 服务运行中
2. Qdrant 服务运行中
3. 已存在 test-repo-boundary 的索引数据

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 为 test-repo-boundary 写入初始 50 个块到 ES 和 Qdrant | 50 个文档/点创建成功 |
| 2 | 验证 ES 中存在 50 个文档 | 数量 = 50 |
| 3 | 验证 Qdrant 中存在 50 个点 | 数量 = 50 |
| 4 | 调用 delete_by_repo(test-repo-boundary) | 旧数据被删除 |
| 5 | 为同一 repo 写入 30 个新块 | 30 个文档/点创建成功 |
| 6 | 验证 ES 中仅存在 30 个文档 | 数量 = 30 |
| 7 | 验证 Qdrant 中仅存在 30 个点 | 数量 = 30 |

### 验证点

- 旧数据被删除
- 新数据成功写入
- 最终数量为 30（旧数据被替换）

### 后置检查

无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_index_writer.py
- **Test Type**: Real

**实际结果:** delete_by_repo() 正确删除该 repository 的所有块。新块写入成功。最终数量为 30（旧数据被替换）。

**结果:** PASS

---

## 用例执行摘要

| 状态 | 数量 |
|------|------|
| 总计 | 4 |
| 通过 | 4 |
| 失败 | 0 |
| 待定 | 0 |

## 追溯矩阵

| 用例ID | 需求 | 验证步骤 | 自动化测试 | 结果 |
|--------|------|----------|-----------|------|
| ST-FUNC-007-001 | FR-004, FR-009 | 100 个块生成 1024 维向量 | 单元测试 | PASS |
| ST-FUNC-007-002 | FR-009 | ES 包含 100 个带元数据的文档 | 集成测试 | PASS |
| ST-FUNC-007-003 | FR-009 | Qdrant 包含 100 个带 ID 的点 | 集成测试 | PASS |
| ST-BNDRY-007-001 | FR-009 | 重新索引删除旧数据、写入新数据 | 集成测试 | PASS |
