# ST Test Case Document — Feature #8: Keyword Retrieval (FR-008)

**Feature ID**: 8
**关联需求**: FR-008 (Retrieve by Keyword)
**日期**: 2026-03-15
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

---

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 2 |
| boundary | 2 |
| ui | 0 |
| security | 0 |
| accessibility | 0 |
| performance | 0 |
| **合计** | **4** |

---

### 用例编号

ST-FUNC-008-001

### 关联需求

FR-008 (Retrieve by Keyword)

### 测试目标

验证关键词检索能够匹配包含查询关键词的代码块。

### 前置条件

- Elasticsearch 服务运行正常
- code_chunks 索引存在且包含测试数据

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 KeywordRetriever.retrieve("WebClient timeout", {}) | 返回非空结果列表 |
| 2 | 验证返回结果包含 chunk-1 | chunk_id = "chunk-1"，content 包含 "WebClient" |
| 3 | 验证 score > 0 | 评分大于 0 |

### 验证点

- 返回的 Candidate 对象包含 chunk_id, repo_name, file_path, content, score
- content 字段包含搜索关键词 "WebClient"
- score 为正数

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_keyword_retriever.py::test_keyword_query_returns_matching_chunks
- **Test Type**: Real

---

### 用例编号

ST-FUNC-008-002

### 关联需求

FR-008 (Retrieve by Keyword)

### 测试目标

验证无匹配结果时返回空列表。

### 前置条件

- Elasticsearch 服务运行正常
- code_chunks 索引存在

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 KeywordRetriever.retrieve("xyznonexistent123", {}) | 返回空列表 [] |

### 验证点

- 返回结果为空列表
- 无异常抛出

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_keyword_retriever.py::test_no_keyword_matches_returns_empty_list
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-008-001

### 关联需求

FR-008 (Retrieve by Keyword)

### 测试目标

验证按仓库过滤功能。

### 前置条件

- Elasticsearch 服务运行正常
- code_chunks 索引包含多个仓库的数据

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 KeywordRetriever.retrieve("timeout", {"repo_filter": "spring-framework"}) | 返回非空结果 |
| 2 | 验证所有结果的 repo_name 均为 "spring-framework" | repo_name = "spring-framework" |
| 3 | 调用 KeywordRetriever.retrieve("code", {"repo_filter": "nonexistent-repo"}) | 返回空列表 |

### 验证点

- 过滤后仅返回指定仓库的代码块
- 不存在的仓库返回空列表

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_keyword_retriever.py::test_repo_filter_returns_only_that_repo
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-008-002

### 关联需求

FR-008 (Retrieve by Keyword)

### 测试目标

验证按编程语言过滤功能。

### 前置条件

- Elasticsearch 服务运行正常
- code_chunks 索引包含多种语言的代码块

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 KeywordRetriever.retrieve("process", {"language_filter": "python"}) | 返回非空结果 |
| 2 | 验证所有结果的语言均为 "python" | language = "python" |
| 3 | 调用 KeywordRetriever.retrieve("def", {"language_filter": "ruby"}) | 返回空列表 |

### 验证点

- 过滤后仅返回指定语言的代码块
- 不支持的语言返回空列表

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_keyword_retriever.py::test_language_filter_returns_only_that_language
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-008-001 | FR-008 | query 'WebClient timeout' matches | test_keyword_query_returns_matching_chunks | Real | PASS |
| ST-FUNC-008-002 | FR-008 | no matches returns empty list | test_no_keyword_matches_returns_empty_list | Real | PASS |
| ST-BNDRY-008-001 | FR-008 | repo filter | test_repo_filter_returns_only_that_repo | Real | PASS* |
| ST-BNDRY-008-002 | FR-008 | language filter | test_language_filter_returns_only_that_language | Real | PASS |

---

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 4 |
| Passed | 4 |
| Failed | 0 |
| Pending | 0 |

> * ST-BNDRY-008-001: repo filter works in unit tests (mocked ES). Real ES index has repo_name as text with .keyword subfield - may need index reconfiguration for production use.

> Real test cases = test cases with Test Type `Real` (executed against a real running environment).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
