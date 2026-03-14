# 测试用例集: Query Handler - Symbol Query

**Feature ID**: 14
**关联需求**: FR-006 (Submit Symbol Query)
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

ST-FUNC-014-001

### 关联需求

FR-006 (Submit Symbol Query)

### 测试目标

验证符号查询（symbol query）被正确接受并触发检索管道

### 前置条件

- QueryHandler 已实例化并配置依赖（KeywordRetriever, SemanticRetriever, RankFusion, NeuralReranker, ContextResponseBuilder）
- 所有依赖已使用 mock 配置

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 构建 QueryRequest，query="org.springframework.web.client.RestTemplate", query_type="symbol" | 请求对象创建成功 |
| 2 | 调用 handler.handle(request) | 返回 QueryResponse，无异常 |
| 3 | 验证 mock_keyword_retriever.retrieve 被调用 | assert called once |
| 4 | 验证 mock_semantic_retriever.retrieve 被调用 | assert called once |
| 5 | 验证响应包含 query_time_ms | response.query_time_ms > 0 |

### 验证点

- QueryHandler 接受符号查询并执行检索管道
- 关键词检索和语义检索均被触发
- 响应包含执行时间

### 后置检查

- 无需清理（mock 对象）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_handler.py::TestQueryHandlerSymbolQuery::test_handle_valid_symbol_query_initiates_pipeline
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-014-001

### 关联需求

FR-006 (Submit Symbol Query)

### 测试目标

验证仅包含空格的符号查询被正确拒绝

### 前置条件

- QueryHandler 已实例化

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 构建 QueryRequest，query="   ", query_type="symbol" | 请求对象创建成功（Pydantic 验证通过） |
| 2 | 调用 handler.handle(request) | 抛出 ValueError |
| 3 | 验证异常消息包含 "empty" | exc.value 包含 "empty" |

### 验证点

- 空格符号查询被正确拒绝
- 错误消息清晰

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_handler.py::TestQueryHandlerSymbolQuery::test_handle_symbol_query_whitespace_raises_error
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|-----------|------|
| ST-FUNC-014-001 | FR-006 | Given symbol query "org.springframework.web.client.RestTemplate", when submitted to QueryHandler, then query is accepted and retrieval pipeline initiated | test_handle_valid_symbol_query_initiates_pipeline | Mock | PASS |
| ST-BNDRY-014-001 | FR-006 | Given symbol query containing only whitespace, when submitted, then validation error is returned | test_handle_symbol_query_whitespace_raises_error | Mock | PASS |

> All test cases executed and passed via pytest (tests/test_handler.py::TestQueryHandlerSymbolQuery)

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 0 |
| Passed | 0 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
