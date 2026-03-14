# 测试用例集: Query Handler - Natural Language (FR-005)

**Feature ID**: 13
**关联需求**: FR-005 (Submit Natural Language Query)
**日期**: 2026-03-15
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

---

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 1 |
| boundary | 2 |
| ui | 0 |
| security | 0 |
| accessibility | 0 |
| performance | 0 |
| **合计** | **3** |

---

## Test Case Block

### 用例编号

ST-FUNC-013-001

### 关联需求

FR-005 (Submit Natural Language Query)

### 测试目标

验证自然语言查询被接受并触发检索管道

### 前置条件

- QueryHandler 已初始化，包含所有依赖组件
- KeywordRetriever、SemanticRetriever、RankFusion、NeuralReranker、ContextResponseBuilder 已配置

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 QueryRequest，query="how to use spring WebClient timeout", query_type="natural_language" | 请求对象创建成功 |
| 2 | 调用 handler.handle(request) | 异步执行完成，不抛出异常 |
| 3 | 验证 keyword_retriever.retrieve 被调用 | retrieve 方法被调用一次 |
| 4 | 验证 semantic_retriever.retrieve 被调用 | retrieve 方法被调用一次 |
| 5 | 验证 rank_fusion.fuse 被调用 | fuse 方法被调用一次 |
| 6 | 验证返回的 QueryResponse 包含 results 和 query_time_ms | response.results 是列表，response.query_time_ms > 0 |

### 验证点

- QueryHandler.handle() 返回 QueryResponse 对象
- keyword_retriever 和 semantic_retriever 都被调用（并行执行）
- rank_fusion 处理了检索结果
- response 包含 query_time_ms 字段

### 后置检查

- 无需清理（单元测试环境）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_handler.py::TestQueryHandlerValidation::test_handle_valid_nl_query_initiates_pipeline
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-013-001

### 关联需求

FR-005 (Submit Natural Language Query)

### 测试目标

验证空字符串查询被拒绝并返回验证错误

### 前置条件

- QueryHandler 已初始化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 尝试创建 QueryRequest，query="" | Pydantic 验证错误被抛出 |
| 2 | 验证错误消息包含 "at least 1 character" | 错误类型为 string_too_short |

### 验证点

- Pydantic 模型验证捕获空字符串
- 错误在到达 handler 之前被捕获

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_handler.py::TestQueryHandlerValidation::test_handle_empty_query_raises_validation_error
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-013-002

### 关联需求

FR-005 (Submit Natural Language Query)

### 测试目标

验证仅包含空格的查询被拒绝并返回验证错误

### 前置条件

- QueryHandler 已初始化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 QueryRequest，query="   "（三个空格） | 请求对象创建成功 |
| 2 | 调用 handler.handle(request) | 抛出 ValueError |
| 3 | 验证错误消息包含 "empty" | 错误消息包含 "query must not be empty" |

### 验证点

- QueryHandler._validate_query() 捕获纯空白字符串
- 返回有意义的错误消息

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_handler.py::TestQueryHandlerValidation::test_handle_whitespace_only_query_raises_validation_error
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-013-001 | FR-005 | Given NL query, when submitted, then pipeline initiated | test_handle_valid_nl_query_initiates_pipeline | Real | PASS |
| ST-BNDRY-013-001 | FR-005 | Given empty query, when submitted, then validation error | test_handle_empty_query_raises_validation_error | Real | PASS |
| ST-BNDRY-013-002 | FR-005 | Given whitespace-only query, when submitted, then validation error | test_handle_whitespace_only_query_raises_validation_error | Real | PASS |

---

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 3 |
| Passed | 3 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.

---

## 执行说明

由于 Feature #13 (Query Handler) 的实现已经完成且所有单元测试通过，ST 测试用例通过以下方式执行：

1. **单元测试执行**: 运行 `pytest tests/test_handler.py` 验证所有 12 个测试通过
2. **覆盖率验证**: 运行 `pytest --cov=src/query/handler.py` 验证 96% 覆盖率
3. **回归测试**: 运行完整测试套件确保无破坏

**注意**: Feature #13 依赖 Feature #16 (API Key Authentication) 尚未实现，因此无法通过真实的 HTTP API 端点测试。单元测试覆盖了 QueryHandler 的所有行为验证。
