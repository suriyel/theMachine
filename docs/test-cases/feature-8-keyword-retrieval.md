# 测试用例集: Keyword Retrieval (BM25)

**Feature ID**: 8
**关联需求**: FR-006（Keyword Retrieval）
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

ST-FUNC-008-001

### 关联需求

FR-006（Keyword Retrieval）

### 测试目标

验证 BM25 搜索能根据查询关键字返回匹配的代码块，结果按 BM25 分数降序排列

### 前置条件

- Elasticsearch 集群已启动，code_chunks 索引已创建
- 索引中包含多个代码块，其中至少 2 个包含 "getUserName" 符号
- Retriever 实例已连接到 ES 客户端

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 bm25_code_search("getUserName", "r1") | 返回 list[ScoredChunk]，非空 |
| 2 | 检查返回结果中的 content_type 字段 | 所有结果的 content_type == "code" |
| 3 | 检查返回结果的排序顺序 | 结果按 score 降序排列（results[0].score >= results[1].score） |
| 4 | 检查返回结果的 symbol 字段 | 包含 "getUserName" 符号的块排名靠前 |

### 验证点

- 返回的 ScoredChunk 列表非空
- 所有结果的 content_type 均为 "code"
- 结果按 BM25 分数降序排列
- 包含匹配符号的块在结果中排名较高

### 后置检查

- 无需清理（只读查询操作）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_retriever.py::test_bm25_code_search_returns_matching_chunks
- **Test Type**: Real

---

### 用例编号

ST-FUNC-008-002

### 关联需求

FR-006（Keyword Retrieval）

### 测试目标

验证同义词过滤器：搜索 "auth" 时返回包含 "authentication" 和 "authorization" 的块

### 前置条件

- Elasticsearch 集群已启动，code_chunks 索引已创建并配置了同义词过滤器
- 索引中包含分别含有 "authentication" 和 "authorization" 内容的代码块

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 bm25_code_search("auth", "r1") | 返回 list[ScoredChunk]，非空 |
| 2 | 检查返回结果的内容 | 结果包含含 "authentication" 的块 |
| 3 | 检查返回结果的内容 | 结果包含含 "authorization" 的块 |

### 验证点

- 搜索 "auth" 能匹配到 "authentication" 相关的代码块
- 搜索 "auth" 能匹配到 "authorization" 相关的代码块
- 同义词扩展在 ES 分析器层面生效

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_retriever.py::test_bm25_code_search_synonym_expansion
- **Test Type**: Real

---

### 用例编号

ST-FUNC-008-003

### 关联需求

FR-006（Keyword Retrieval）

### 测试目标

验证 Elasticsearch 不可达时，bm25_search 抛出 RetrievalError，调用方处理降级

### 前置条件

- Elasticsearch 客户端配置为一个不可达的地址（如端口错误）
- Retriever 实例已创建

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 bm25_code_search("test", "r1")，ES 不可达 | 抛出 RetrievalError |
| 2 | 检查异常消息 | 消息包含 "Elasticsearch search failed" |

### 验证点

- 当 ES 不可达时抛出 RetrievalError（不是原始的 ConnectionError）
- 异常消息描述性清晰，便于调用方日志记录

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_retriever.py::test_bm25_code_search_raises_retrieval_error_on_connection_error
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-008-001

### 关联需求

FR-006（Keyword Retrieval）

### 测试目标

验证无匹配结果时返回空列表，不抛出异常

### 前置条件

- Elasticsearch 集群已启动
- 索引中不包含与查询相关的任何文档

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 bm25_code_search("nonexistent_symbol_xyz_999", "r1") | 返回空列表 [] |
| 2 | 检查返回类型 | 返回值为 list 类型，长度为 0 |

### 验证点

- 返回空列表 []，非 None
- 无异常抛出
- 返回类型正确（list[ScoredChunk]）

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_retriever.py::test_bm25_code_search_returns_empty_on_no_match
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-008-002

### 关联需求

FR-006（Keyword Retrieval）

### 测试目标

验证空查询和空白查询被正确拒绝

### 前置条件

- Retriever 实例已创建并连接到 ES 客户端

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 bm25_code_search("", "r1") | 抛出 ValueError |
| 2 | 检查异常消息 | 消息为 "query must not be empty" |
| 3 | 调用 bm25_code_search("   ", "r1") | 抛出 ValueError |
| 4 | 检查异常消息 | 消息为 "query must not be empty" |

### 验证点

- 空字符串查询抛出 ValueError
- 纯空白查询抛出 ValueError
- 异常消息明确指示原因

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_retriever.py::test_bm25_code_search_raises_value_error_on_empty_query, tests/test_retriever.py::test_bm25_code_search_whitespace_only_query
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-008-001 | FR-006 | VS-1: Given indexed code chunks containing 'getUserName', when bm25_search('getUserName') runs, then results include chunks containing that symbol, ranked by BM25 score | test_bm25_code_search_returns_matching_chunks | Real | PASS |
| ST-FUNC-008-002 | FR-006 | VS-2: Given the code_analyzer with synonym filter, when searching 'auth', then results also include chunks containing 'authentication' and 'authorization' | test_bm25_code_search_synonym_expansion | Real | PASS |
| ST-FUNC-008-003 | FR-006 | VS-4: Given Elasticsearch is unreachable, when bm25_search() runs, then it raises a retrieval error | test_bm25_code_search_raises_retrieval_error_on_connection_error | Mock | PASS |
| ST-BNDRY-008-001 | FR-006 | VS-3: Given a query with no matching terms, when bm25_search() runs, then it returns an empty list without error | test_bm25_code_search_returns_empty_on_no_match | Real | PASS |
| ST-BNDRY-008-002 | FR-006 | Input validation boundary | test_bm25_code_search_raises_value_error_on_empty_query, test_bm25_code_search_whitespace_only_query | Mock | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 3 |
| Passed | 3 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
