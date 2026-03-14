# 测试用例集: Query Handler - Repository Scoped

**Feature ID**: 15
**关联需求**: FR-007 (Submit Repository-Scoped Query)
**日期**: 2026-03-15
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 1 |
| boundary | 1 |
| ui | 0 |
| security | 0 |
| accessibility | 0 |
| performance | 0 |
| **合计** | **2** |

---

### 用例编号

ST-FUNC-015-001

### 关联需求

FR-007 (Submit Repository-Scoped Query)

### 测试目标

验证查询在指定仓库范围内执行，仅返回该仓库的结果

### 前置条件

- QueryHandler 已实例化并配置依赖（KeywordRetriever, SemanticRetriever, RankFusion, NeuralReranker, ContextResponseBuilder）
- 所有依赖已使用 mock 配置
- KeywordRetriever 和 SemanticRetriever 配置为返回来自 spring-framework 的结果

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 构建 QueryRequest，query="timeout", query_type="natural_language", repo="spring-framework" | 请求对象创建成功 |
| 2 | 调用 handler.handle(request) | 返回 QueryResponse，无异常 |
| 3 | 验证 mock_keyword_retriever.retrieve 被调用，且 filters 包含 repo_filter="spring-framework" | assert filters.get('repo_filter') == 'spring-framework' |
| 4 | 验证 mock_semantic_retriever.retrieve 被调用，且 filters 包含 repo_filter="spring-framework" | assert filters.get('repo_filter') == 'spring-framework' |
| 5 | 验证响应包含 query_time_ms | response.query_time_ms > 0 |

### 验证点

- QueryHandler 接受带仓库过滤器的查询
- repo_filter 被正确传递给关键词检索器
- repo_filter 被正确传递给语义检索器
- 检索仅返回指定仓库的结果

### 后置检查

- 无需清理（mock 对象）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_handler.py::TestQueryHandlerRepoScoped::test_repo_scoped_query_restricts_to_specified_repo
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-015-001

### 关联需求

FR-007 (Submit Repository-Scoped Query)

### 测试目标

验证查询不存在的仓库时返回空结果，无异常

### 前置条件

- QueryHandler 已实例化并配置依赖
- KeywordRetriever 和 SemanticRetriever 配置为返回空结果（模拟不存在的仓库）

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 构建 QueryRequest，query="timeout", query_type="natural_language", repo="non-existent-repo-12345" | 请求对象创建成功 |
| 2 | 配置 mock 返回空列表 | mock_keyword_retriever.retrieve.return_value = []; mock_semantic_retriever.retrieve.return_value = [] |
| 3 | 调用 handler.handle(request) | 返回 QueryResponse，无异常 |
| 4 | 验证响应结果为空列表 | response.results == [] |

### 验证点

- 不存在的仓库不会导致错误
- 返回空结果集
- 系统正常处理边界情况

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_handler.py::TestQueryHandlerRepoScoped::test_non_existent_repo_returns_empty_results_no_error
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|-----------|------|
| ST-FUNC-015-001 | FR-007 | Given query 'timeout' scoped to repository 'spring-framework', when retrieval executes, then only chunks from spring-framework are processed | test_repo_scoped_query_restricts_to_specified_repo | Mock | PASS |
| ST-BNDRY-015-001 | FR-007 | Given query scoped to non-existent repository, when retrieval executes, then empty result set is returned with no error | test_non_existent_repo_returns_empty_results_no_error | Mock | PASS |

> All test cases executed and passed via pytest (tests/test_handler.py::TestQueryHandlerRepoScoped)

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 0 |
| Passed | 0 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
