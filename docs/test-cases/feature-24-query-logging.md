# 测试用例集: Query Logging

**Feature ID**: 24
**关联需求**: FR-022（Query Logging）
**日期**: 2026-03-22
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

ST-FUNC-024-001

### 关联需求

FR-022（Query Logging）

### 测试目标

验证完成查询后，结构化 JSON 日志写入 stdout，包含所有必需字段

### 前置条件

- QueryLogger 已实例化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 log_query(query="find auth", query_type="nl", api_key_id="key-1", result_count=5, retrieval_ms=12.3, rerank_ms=4.5, total_ms=18.0) | 无异常 |
| 2 | 捕获 stdout 输出并解析 JSON | 有效 JSON 对象 |
| 3 | 检查 JSON 包含 query="find auth" | 匹配 |
| 4 | 检查 JSON 包含 query_type, api_key_id, result_count, retrieval_ms, rerank_ms, total_ms | 所有字段存在且值正确 |
| 5 | 检查 JSON 包含 timestamp 字段 | ISO 8601 格式 |

### 验证点

- JSON 包含所有 8 个必需字段：query, query_type, api_key_id, result_count, retrieval_ms, rerank_ms, total_ms, timestamp
- 字段值与传入参数一致
- timestamp 为 ISO 8601 UTC 格式

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_query_logger.py::TestQueryLoggerHappyPath::test_log_query_produces_json_with_all_required_fields
- **Test Type**: Real

---

### 用例编号

ST-FUNC-024-002

### 关联需求

FR-022（Query Logging）

### 测试目标

验证多次查询产生多条独立 JSON 日志条目

### 前置条件

- QueryLogger 已实例化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 log_query 两次，不同参数 | 无异常 |
| 2 | 捕获 stdout 输出，按行解析 | 两条独立 JSON 行 |
| 3 | 验证第一条 query="q1"，第二条 query="q2" | 匹配 |

### 验证点

- 每次调用产生一条独立 JSON 日志行
- 各条目字段值独立且正确

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_query_logger.py::TestQueryLoggerHappyPath::test_multiple_queries_produce_multiple_log_entries
- **Test Type**: Real

---

### 用例编号

ST-FUNC-024-003

### 关联需求

FR-022（Query Logging）

### 测试目标

验证日志 I/O 失败时不阻塞或延迟查询响应（非致命）

### 前置条件

- QueryLogger 已实例化
- 日志 handler 模拟 IOError

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 模拟 logger.info 抛出 IOError("disk full") | 模拟就绪 |
| 2 | 调用 log_query(...) | 无异常抛出 |
| 3 | 验证调用正常返回 | 方法返回 None，无 traceback |

### 验证点

- IOError 被 try/except 静默捕获
- 调用方不受日志失败影响

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_query_logger.py::TestQueryLoggerErrorHandling::test_io_failure_does_not_raise
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-024-001

### 关联需求

FR-022（Query Logging）

### 测试目标

验证所有参数为 None 时不抛异常且产生有效 JSON

### 前置条件

- QueryLogger 已实例化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 log_query(query=None, query_type=None, api_key_id=None, result_count=None, retrieval_ms=None, rerank_ms=None, total_ms=None) | 无异常 |
| 2 | 解析 stdout 输出 | 有效 JSON，字段值为 null |

### 验证点

- None 值序列化为 JSON null
- 不抛 TypeError 或 ValueError

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_query_logger.py::TestQueryLoggerErrorHandling::test_none_and_empty_values_handled_gracefully
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-024-002

### 关联需求

FR-022（Query Logging）

### 测试目标

验证零值和超长查询字符串可正确记录

### 前置条件

- QueryLogger 已实例化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 log_query 使用 10000 字符 query 和 0 值时间字段 | 无异常 |
| 2 | 解析 stdout 输出 | 有效 JSON |
| 3 | 验证 query 长度 = 10000 | 匹配 |
| 4 | 验证 result_count=0, retrieval_ms=0.0, rerank_ms=0.0, total_ms=0.0 | 匹配 |

### 验证点

- 超长字符串不被截断
- 零值不被过滤或替换

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_query_logger.py::TestQueryLoggerBoundary::test_very_long_query_string, test_zero_values_for_timing_fields
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-024-001 | FR-022 | VS-1: JSON log entry with all fields | test_log_query_produces_json_with_all_required_fields | Real | PASS |
| ST-FUNC-024-002 | FR-022 | VS-1: multiple queries produce entries | test_multiple_queries_produce_multiple_log_entries | Real | PASS |
| ST-FUNC-024-003 | FR-022 | VS-2: I/O failure does not block query | test_io_failure_does_not_raise | Mock | PASS |
| ST-BNDRY-024-001 | FR-022 | VS-1: None values handled | test_none_and_empty_values_handled_gracefully | Real | PASS |
| ST-BNDRY-024-002 | FR-022 | VS-1: zero/long values handled | test_very_long_query_string + test_zero_values | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 4 |
| Passed | 4 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
