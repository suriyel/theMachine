# 测试用例集: Metrics Endpoint

**Feature ID**: 23
**关联需求**: FR-021（Metrics Endpoint）
**日期**: 2026-03-22
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 3 |
| boundary | 2 |
| security | 1 |
| **合计** | **6** |

---

### 用例编号

ST-FUNC-023-001

### 关联需求

FR-021（Metrics Endpoint）

### 测试目标

验证 GET /metrics 返回 Prometheus text 格式，包含所有必需的 metric 名称

### 前置条件

- 应用已启动，/api/v1/health 返回 200
- 无需认证头

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 GET /metrics 请求（无认证头） | HTTP 200 |
| 2 | 检查 Content-Type 头 | 包含 `text/plain` |
| 3 | 在响应体中搜索 `query_latency_seconds` | 存在 |
| 4 | 在响应体中搜索 `retrieval_latency_seconds` | 存在 |
| 5 | 在响应体中搜索 `rerank_latency_seconds` | 存在 |
| 6 | 在响应体中搜索 `index_size_chunks` | 存在 |
| 7 | 在响应体中搜索 `cache_hit_ratio` | 存在 |

### 验证点

- 响应状态码为 200
- Content-Type 包含 text/plain
- 所有 5 个必需 metric 名称均出现在响应体中：query_latency_seconds, retrieval_latency_seconds, rerank_latency_seconds, index_size_chunks, cache_hit_ratio

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_metrics.py::test_metrics_endpoint_returns_all_metric_names
- **Test Type**: Real

---

### 用例编号

ST-FUNC-023-002

### 关联需求

FR-021（Metrics Endpoint）

### 测试目标

验证查询处理后，histogram bucket 中包含观测值

### 前置条件

- 应用已启动
- 至少一个查询已被 record_query_latency 记录

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 record_query_latency(0.05, "nl", False) 记录一次查询延迟 | 无异常 |
| 2 | 发送 GET /metrics | HTTP 200 |
| 3 | 在响应体中搜索 `query_latency_seconds_count{cache_hit="false",query_type="nl"}` | 存在且值 >= 1.0 |
| 4 | 在响应体中搜索 `query_latency_seconds_sum{cache_hit="false",query_type="nl"}` | 存在且值 ≈ 0.05 |
| 5 | 在响应体中搜索 `query_total` counter | 存在且 query_type="nl" 值 >= 1.0 |

### 验证点

- histogram _count 大于等于 1
- histogram _sum 近似等于记录的延迟值（0.05s）
- query_total counter 反映查询次数

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_metrics.py::test_metrics_histogram_records_query_latency
- **Test Type**: Real

---

### 用例编号

ST-FUNC-023-003

### 关联需求

FR-021（Metrics Endpoint）

### 测试目标

验证 retrieval、rerank 延迟及 cache_hit_ratio、index_size_chunks gauge 均可正确记录和读取

### 前置条件

- 应用已启动

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 record_retrieval_latency(0.01, "es_code") | 无异常 |
| 2 | 调用 record_rerank_latency(0.02) | 无异常 |
| 3 | 调用 set_cache_hit_ratio(0.75) | 无异常 |
| 4 | 调用 set_index_size(1000, "repo1", "code") | 无异常 |
| 5 | 发送 GET /metrics | HTTP 200 |
| 6 | 检查 retrieval_latency_seconds_count{backend="es_code"} | 值 >= 1.0 |
| 7 | 检查 rerank_latency_seconds_sum | 值 ≈ 0.02 |
| 8 | 检查 cache_hit_ratio | 值 = 0.75 |
| 9 | 检查 index_size_chunks{content_type="code",repo_id="repo1"} | 值 = 1000.0 |

### 验证点

- 所有四种 metric helper 函数均正确写入 Prometheus registry
- GET /metrics 返回的值与设置值一致

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_metrics.py::test_metrics_retrieval_latency_with_backend_label, test_metrics_rerank_latency_recorded, test_metrics_cache_hit_ratio_gauge, test_metrics_index_size_chunks_gauge
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-023-001

### 关联需求

FR-021（Metrics Endpoint）

### 测试目标

验证无任何观测数据时，/metrics 仍返回所有 metric 名称（counter 为 0，histogram 有空 bucket）

### 前置条件

- 应用刚启动，未处理过任何查询
- 未调用过任何 record_* 或 set_* 函数

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 GET /metrics（应用刚启动，无历史数据） | HTTP 200 |
| 2 | 检查响应体是否包含 query_latency_seconds | 存在（TYPE 行和 HELP 行） |
| 3 | 检查响应体是否包含 query_total | 存在 |
| 4 | 检查响应体是否包含 cache_hit_ratio | 存在 |
| 5 | 检查响应体是否包含 index_size_chunks | 存在 |

### 验证点

- 所有 metric 名称在零观测状态下均可见
- Prometheus scraper 可正常采集初始化状态

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_metrics.py::test_metrics_present_without_observations
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-023-002

### 关联需求

FR-021（Metrics Endpoint）

### 测试目标

验证零延迟（0.0 秒）可被正确记录为有效观测

### 前置条件

- 应用已启动

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 record_query_latency(0.0, "nl", True) | 无异常 |
| 2 | 发送 GET /metrics | HTTP 200 |
| 3 | 检查 query_latency_seconds_count{cache_hit="true",query_type="nl"} | 值 >= 1.0 |

### 验证点

- 0.0 秒不被跳过或拒绝，而是记录为最低 bucket 的观测
- histogram count 增加

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_metrics.py::test_metrics_zero_latency_recorded
- **Test Type**: Real

---

### 用例编号

ST-SEC-023-001

### 关联需求

FR-021（Metrics Endpoint）

### 测试目标

验证 /metrics 端点无需认证即可访问（允许 Prometheus scraper 无 API key 采集）

### 前置条件

- 应用已启动，认证中间件已配置

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 GET /metrics，不包含任何 Authorization 或 X-API-Key 头 | HTTP 200 |
| 2 | 检查响应体是否为 Prometheus text 格式 | 包含 query_latency_seconds |

### 验证点

- /metrics 端点不被认证中间件拦截
- 无认证头时返回 200，非 401 或 403

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: security
- **已自动化**: Yes
- **测试引用**: tests/test_metrics.py::test_metrics_endpoint_unauthenticated
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-023-001 | FR-021 | VS-1: GET /metrics returns Prometheus text with all metric names | test_metrics_endpoint_returns_all_metric_names | Real | PASS |
| ST-FUNC-023-002 | FR-021 | VS-2: histogram buckets contain observed values after queries | test_metrics_histogram_records_query_latency | Real | PASS |
| ST-FUNC-023-003 | FR-021 | VS-1: all metric helpers record values correctly | test_metrics_retrieval_latency_with_backend_label + others | Real | PASS |
| ST-BNDRY-023-001 | FR-021 | VS-1: metrics present with zero observations | test_metrics_present_without_observations | Real | PASS |
| ST-BNDRY-023-002 | FR-021 | VS-2: zero latency recorded as valid observation | test_metrics_zero_latency_recorded | Real | PASS |
| ST-SEC-023-001 | FR-021 | VS-1: /metrics is unauthenticated | test_metrics_endpoint_unauthenticated | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 6 |
| Passed | 6 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
