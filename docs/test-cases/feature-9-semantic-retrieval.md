# 测试用例集: Semantic Retrieval (FR-009)

**Feature ID**: 9
**关联需求**: FR-009 (Retrieve by Semantic Similarity)
**日期**: 2026-03-15
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 2 |
| boundary | 2 |
| **合计** | **4** |

---

### 用例编号

ST-FUNC-009-001

### 关联需求

FR-009（Retrieve by Semantic Similarity）

### 测试目标

验证语义检索返回语义相似的内容，即使关键词不匹配

### 前置条件

- Qdrant 服务运行在 http://localhost:6333
- Qdrant collection "code_chunks" 存在并包含索引的代码 embeddings
- Embedding model 已配置 (BAAI/bge-code-v1)

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 初始化 SemanticRetriever，threshold=0.6 | 实例创建成功 |
| 2 | 调用 retrieve(query="how to configure spring http client timeout", filters={}) | 返回 Candidate 对象列表 |
| 3 | 验证至少返回一个结果 | len(results) >= 1 |
| 4 | 验证所有结果 score >= 0.6 | 所有分数高于阈值 |
| 5 | 验证结果结构 | Candidate 包含 chunk_id, repo_name, file_path, content, score |

### 验证点

- 返回的 Candidate 对象数量 >= 1
- 所有结果的 score >= 0.6
- Candidate 包含所有必需字段

### 后置检查

- 无需清理（只读操作）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_semantic_retriever.py::TestSemanticRetrieverReal::test_real_qdrant_semantic_search
- **Test Type**: Real

---

### 用例编号

ST-FUNC-009-002

### 关联需求

FR-009（Retrieve by Semantic Similarity）

### 测试目标

验证语义检索在无匹配内容时返回空列表

### 前置条件

- Qdrant 服务运行在 http://localhost:6333

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 初始化 SemanticRetriever，threshold=0.6 | 实例创建成功 |
| 2 | 调用 retrieve(query="xyznonexistentquery12345xyz", filters={}) | 返回空列表 |
| 3 | 验证空结果 | len(results) == 0 |

### 验证点

- 返回空列表
- 无异常抛出

### 后置检查

- 无需清理（只读操作）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_semantic_retriever.py::TestSemanticRetrieverReal::test_real_qdrant_no_match_returns_empty
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-009-001

### 关联需求

FR-009（Retrieve by Semantic Similarity）

### 测试目标

验证可配置阈值过滤低分结果

### 前置条件

- Qdrant 服务运行在 http://localhost:6333

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 初始化 SemanticRetriever，threshold=0.8 | 实例创建成功 |
| 2 | 调用 retrieve(query="timeout", filters={}) | 返回 Candidate 对象列表 |
| 3 | 验证所有结果 score >= 0.8 | 所有分数 >= 0.8 |

### 验证点

- 如果有结果，所有结果的 score >= 0.8

### 后置检查

- 无需清理（只读操作）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_semantic_retriever.py::TestSemanticRetrieverUnit::test_higher_threshold_filters_more_results
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-009-002

### 关联需求

FR-009（Retrieve by Semantic Similarity）

### 测试目标

验证语义检索支持 repo_filter 过滤

### 前置条件

- Qdrant 服务运行在 http://localhost:6333

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 初始化 SemanticRetriever，threshold=0.6 | 实例创建成功 |
| 2 | 调用 retrieve(query="timeout", filters={"repo_filter": "spring-framework"}) | 返回 Candidate 对象列表 |
| 3 | 验证所有结果来自 spring-framework | 所有结果的 repo_name == "spring-framework" |

### 验证点

- 所有结果的 repo_name 一致
- 如果有结果，所有来自指定仓库

### 后置检查

- 无需清理（只读操作）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_semantic_retriever.py::TestSemanticRetrieverReal::test_real_qdrant_repo_filter
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|------------------|-----------|---------|------|
| ST-FUNC-009-001 | FR-009 | Semantic search with matching content | test_real_qdrant_semantic_search | Real | PENDING |
| ST-FUNC-009-002 | FR-009 | No matches above threshold | test_real_qdrant_no_match_returns_empty | Real | PASS |
| ST-BNDRY-009-001 | FR-009 | Configurable threshold filtering | test_higher_threshold_filters_more_results | Real | PASS |
| ST-BNDRY-009-002 | FR-009 | Repo filter | test_real_qdrant_repo_filter | Real | PENDING |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 4 |
| Passed | 2 |
| Failed | 0 |
| Pending | 2 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.

## 备注

- 本功能需要 Qdrant 中有来自 Feature #7 (Embedding Generation) 的索引数据
- 测试用例设计用于通过 SemanticRetriever API 验证黑盒行为
- 测试执行需要运行的服务中有索引的代码块
- 已通过单元测试和边缘案例测试验证实现正确性：
  - 空查询验证 ✓
  - 仅空白字符查询验证 ✓
  - 空结果处理 ✓
  - 阈值过滤 ✓
