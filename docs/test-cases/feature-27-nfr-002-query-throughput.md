# 测试用例集: NFR-002: Query Throughput >= 1000 QPS

**Feature ID**: 27
**关联需求**: NFR-002
**日期**: 2026-03-23
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 5 |
| boundary | 4 |
| performance | 1 |
| **合计** | **10** |

---

### 用例编号

ST-FUNC-027-001

### 关联需求

NFR-002（Query throughput >= 1000 QPS sustained）

### 测试目标

验证ThroughputReportAnalyzer.analyze()在QPS高于阈值且error_rate低于阈值时返回passed=True并正确提取所有指标

### 前置条件

- ThroughputReportAnalyzer类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Locust格式CSV文件，包含Aggregated行：Requests/s=1500.0, Request Count=450000, Failure Count=100 | CSV文件创建成功 |
| 2 | 调用ThroughputReportAnalyzer().analyze(csv_path) | 返回ThroughputVerificationResult对象 |
| 3 | 检查result.passed | passed=True（QPS=1500 >= 1000且error_rate~0.000222 < 0.01） |
| 4 | 检查result.qps, total_requests | qps=1500.0, total_requests=450000 |
| 5 | 检查result.error_rate | error_rate ≈ 100/450000 ≈ 0.000222 |

### 验证点

- ThroughputVerificationResult.passed == True
- qps == 1500.0
- total_requests == 450000
- error_rate ≈ 0.000222
- qps_threshold == 1000.0, error_rate_threshold == 0.01

### 后置检查

- 临时CSV文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_002_query_throughput.py::test_analyze_csv_high_qps_passes
- **Test Type**: Real

---

### 用例编号

ST-FUNC-027-002

### 关联需求

NFR-002（Query throughput >= 1000 QPS sustained）

### 测试目标

验证ThroughputReportAnalyzer.analyze()在QPS低于阈值时返回passed=False

### 前置条件

- ThroughputReportAnalyzer类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Locust格式CSV文件，包含Aggregated行：Requests/s=800.0 | CSV文件创建成功 |
| 2 | 调用ThroughputReportAnalyzer().analyze(csv_path) | 返回ThroughputVerificationResult对象 |
| 3 | 检查result.passed | passed=False（800 < 1000阈值） |
| 4 | 检查result.qps | qps=800.0 |

### 验证点

- ThroughputVerificationResult.passed == False
- qps == 800.0（低于默认阈值1000.0）

### 后置检查

- 临时CSV文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_002_query_throughput.py::test_analyze_csv_low_qps_fails
- **Test Type**: Real

---

### 用例编号

ST-FUNC-027-003

### 关联需求

NFR-002（Query throughput >= 1000 QPS sustained with < 1% error rate）

### 测试目标

验证当QPS超过阈值但error_rate超过阈值时，analyze()返回passed=False（双条件检查）

### 前置条件

- ThroughputReportAnalyzer类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Locust格式CSV文件：Requests/s=1200.0, Request Count=10000, Failure Count=200（error_rate=2%） | CSV文件创建成功 |
| 2 | 调用ThroughputReportAnalyzer().analyze(csv_path) | 返回ThroughputVerificationResult对象 |
| 3 | 检查result.passed | passed=False（QPS通过但error_rate=0.02 >= 0.01） |
| 4 | 检查result.qps和result.error_rate | qps=1200.0, error_rate≈0.02 |

### 验证点

- ThroughputVerificationResult.passed == False
- qps == 1200.0（通过QPS检查）
- error_rate ≈ 0.02（未通过error_rate检查）
- 双条件逻辑正确：QPS通过+error_rate失败 → 总体FAIL

### 后置检查

- 临时CSV文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_002_query_throughput.py::test_analyze_csv_high_qps_high_error_rate_fails
- **Test Type**: Real

---

### 用例编号

ST-FUNC-027-004

### 关联需求

NFR-002（Query throughput >= 1000 QPS sustained）

### 测试目标

验证analyze_from_stats()正确聚合多个统计条目的QPS和error_rate

### 前置条件

- ThroughputReportAnalyzer类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 准备stats列表：[{qps:600, total_requests:180000, failure_count:50}, {qps:500, total_requests:150000, failure_count:30}] | 数据准备完成 |
| 2 | 调用ThroughputReportAnalyzer().analyze_from_stats(stats) | 返回ThroughputVerificationResult对象 |
| 3 | 检查result.passed | passed=True（聚合QPS=1100 >= 1000且error_rate低） |
| 4 | 检查result.qps, total_requests, error_rate | qps=1100.0, total_requests=330000, error_rate≈80/330000 |

### 验证点

- ThroughputVerificationResult.passed == True
- qps == 1100.0（600+500）
- total_requests == 330000（180000+150000）
- error_rate ≈ 80/330000 ≈ 0.000242

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_002_query_throughput.py::test_analyze_from_stats_aggregates_qps
- **Test Type**: Real

---

### 用例编号

ST-FUNC-027-005

### 关联需求

NFR-002（Query throughput >= 1000 QPS sustained）

### 测试目标

验证ThroughputVerificationResult.summary()正确格式化包含NFR-002标识、判定结果和指标值

### 前置条件

- ThroughputVerificationResult类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建passing ThroughputVerificationResult(passed=True, qps=1500.0, ...) | 对象创建成功 |
| 2 | 调用result.summary() | 返回包含"NFR-002"、"PASS"、"1500"的字符串 |
| 3 | 创建failing ThroughputVerificationResult(passed=False, qps=800.0, ...) | 对象创建成功 |
| 4 | 调用result.summary() | 返回包含"NFR-002"、"FAIL"、"800"的字符串 |

### 验证点

- passing结果的summary包含"NFR-002"、"PASS"、"1500"、"1000"（阈值）
- failing结果的summary包含"NFR-002"、"FAIL"、"800"
- summary格式符合设计文档规定

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: Medium
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_002_query_throughput.py::test_summary_pass_format, test_nfr_002_query_throughput.py::test_summary_fail_format
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-027-001

### 关联需求

NFR-002（Query throughput >= 1000 QPS sustained）

### 测试目标

验证QPS恰好等于阈值时（边界值），analyze()返回passed=True（>= 语义）

### 前置条件

- ThroughputReportAnalyzer类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Locust格式CSV：Requests/s=1000.0（恰好等于阈值），Failure Count=0 | CSV文件创建成功 |
| 2 | 调用ThroughputReportAnalyzer().analyze(csv_path) | 返回ThroughputVerificationResult对象 |
| 3 | 检查result.passed | passed=True（1000.0 >= 1000.0） |
| 4 | 检查result.error_rate | error_rate=0.0 |

### 验证点

- ThroughputVerificationResult.passed == True
- 使用 >= 比较（非严格 >）

### 后置检查

- 临时CSV文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_002_query_throughput.py::test_analyze_csv_qps_exactly_at_threshold
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-027-002

### 关联需求

NFR-002（Query throughput >= 1000 QPS sustained with < 1% error rate）

### 测试目标

验证error_rate恰好等于阈值时（边界值），analyze()返回passed=False（严格 < 语义）

### 前置条件

- ThroughputReportAnalyzer类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Locust格式CSV：Requests/s=1500.0, Request Count=10000, Failure Count=100（error_rate=0.01） | CSV文件创建成功 |
| 2 | 调用ThroughputReportAnalyzer().analyze(csv_path) | 返回ThroughputVerificationResult对象 |
| 3 | 检查result.passed | passed=False（error_rate=0.01不满足 < 0.01） |
| 4 | 检查result.error_rate | error_rate == 0.01 |

### 验证点

- ThroughputVerificationResult.passed == False
- error_rate == 0.01（恰好等于阈值，严格 < 不通过）

### 后置检查

- 临时CSV文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_002_query_throughput.py::test_analyze_csv_error_rate_exactly_at_threshold
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-027-003

### 关联需求

NFR-002（Query throughput >= 1000 QPS sustained）

### 测试目标

验证total_requests为0时不发生ZeroDivisionError，error_rate回退为0.0

### 前置条件

- ThroughputReportAnalyzer类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Locust格式CSV：Requests/s=0.0, Request Count=0, Failure Count=0 | CSV文件创建成功 |
| 2 | 调用ThroughputReportAnalyzer().analyze(csv_path) | 返回ThroughputVerificationResult对象（无异常） |
| 3 | 检查result.error_rate | error_rate=0.0（不产生ZeroDivisionError） |
| 4 | 检查result.total_requests | total_requests=0 |

### 验证点

- 无ZeroDivisionError异常
- error_rate == 0.0
- total_requests == 0

### 后置检查

- 临时CSV文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_002_query_throughput.py::test_analyze_csv_zero_requests_no_division_error
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-027-004

### 关联需求

NFR-002（Query throughput >= 1000 QPS sustained）

### 测试目标

验证qps_threshold=0.0边界值和error_rate_threshold=0.0边界值的行为

### 前置条件

- ThroughputReportAnalyzer类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建CSV：Requests/s=0.1, Request Count=100, Failure Count=0 | CSV文件创建成功 |
| 2 | 调用analyze(csv_path, qps_threshold=0.0) | passed=True（0.1 >= 0.0） |
| 3 | 创建CSV：Requests/s=1500.0, Request Count=100000, Failure Count=0 | CSV文件创建成功 |
| 4 | 调用analyze(csv_path, error_rate_threshold=0.0) | passed=False（0.0 < 0.0为False） |

### 验证点

- qps_threshold=0.0时，任何非负QPS都通过QPS检查
- error_rate_threshold=0.0时，即使zero failures也不通过（0.0 < 0.0为False）

### 后置检查

- 临时CSV文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_002_query_throughput.py::test_analyze_csv_zero_qps_threshold, test_nfr_002_query_throughput.py::test_analyze_csv_zero_error_rate_threshold_with_zero_failures
- **Test Type**: Real

---

### 用例编号

ST-PERF-027-001

### 关联需求

NFR-002（Query throughput >= 1000 QPS sustained with < 1% error rate）

### 测试目标

验证完整的CSV解析→指标提取→阈值判定→结果格式化端到端流程，模拟真实Locust输出

### 前置条件

- ThroughputReportAnalyzer类已实现且可导入
- ThroughputVerificationResult类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建包含endpoint行和Aggregated行的Locust CSV：Requests/s=1250.0, Request Count=375000, Failure Count=150 | CSV文件创建成功 |
| 2 | 调用ThroughputReportAnalyzer().analyze(csv_path, qps_threshold=1000.0) | 返回ThroughputVerificationResult |
| 3 | 检查result.passed | passed=True |
| 4 | 检查所有指标字段 | qps=1250.0, total_requests=375000, error_rate≈0.0004, qps_threshold=1000.0, error_rate_threshold=0.01 |
| 5 | 调用result.summary() | 返回包含"NFR-002"、"PASS"、"1250"的格式化字符串 |

### 验证点

- 端到端流程：CSV写入→解析→指标提取→阈值判定→结果格式化全部正确
- passed == True
- 所有数值字段准确
- summary()输出包含正确的NFR标识和判定结果

### 后置检查

- 临时CSV文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: performance
- **已自动化**: Yes
- **测试引用**: test_nfr_002_query_throughput.py::TestRealThroughputReportFeature27::test_real_csv_roundtrip_analyze_feature_27
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-027-001 | NFR-002 | VS-1: QPS >= 1000 with < 1% error rate | test_analyze_csv_high_qps_passes | Real | PASS |
| ST-FUNC-027-002 | NFR-002 | VS-1: QPS >= 1000 with < 1% error rate | test_analyze_csv_low_qps_fails | Real | PASS |
| ST-FUNC-027-003 | NFR-002 | VS-1: QPS >= 1000 with < 1% error rate | test_analyze_csv_high_qps_high_error_rate_fails | Real | PASS |
| ST-FUNC-027-004 | NFR-002 | VS-1: QPS >= 1000 with < 1% error rate | test_analyze_from_stats_aggregates_qps | Real | PASS |
| ST-FUNC-027-005 | NFR-002 | VS-1: QPS >= 1000 with < 1% error rate | test_summary_pass_format, test_summary_fail_format | Real | PASS |
| ST-BNDRY-027-001 | NFR-002 | VS-1: QPS >= 1000 with < 1% error rate | test_analyze_csv_qps_exactly_at_threshold | Real | PASS |
| ST-BNDRY-027-002 | NFR-002 | VS-1: QPS >= 1000 with < 1% error rate | test_analyze_csv_error_rate_exactly_at_threshold | Real | PASS |
| ST-BNDRY-027-003 | NFR-002 | VS-1: QPS >= 1000 with < 1% error rate | test_analyze_csv_zero_requests_no_division_error | Real | PASS |
| ST-BNDRY-027-004 | NFR-002 | VS-1: QPS >= 1000 with < 1% error rate | test_analyze_csv_zero_qps_threshold, test_analyze_csv_zero_error_rate_threshold_with_zero_failures | Real | PASS |
| ST-PERF-027-001 | NFR-002 | VS-1: QPS >= 1000 with < 1% error rate | test_real_csv_roundtrip_analyze_feature_27 | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 10 |
| Passed | 10 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
