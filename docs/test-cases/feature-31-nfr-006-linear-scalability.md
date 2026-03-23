# 测试用例集: NFR-006: Linear Scalability >= 70%

**Feature ID**: 31
**关联需求**: NFR-006
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

ST-FUNC-031-001

### 关联需求

NFR-006（Scalability: Horizontal Scaling — Adding 1 node yields >= 70% of theoretical throughput increase）

### 测试目标

验证ScalabilityReportAnalyzer.analyze()在两组CSV（baseline 1000 QPS/2节点, scaled 1400 QPS/3节点）下返回passed=True，efficiency=0.80

### 前置条件

- ScalabilityReportAnalyzer类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建baseline Locust CSV文件，Aggregated行Requests/s=1000.0 | CSV文件创建成功 |
| 2 | 创建scaled Locust CSV文件，Aggregated行Requests/s=1400.0 | CSV文件创建成功 |
| 3 | 调用ScalabilityReportAnalyzer().analyze(baseline_csv, scaled_csv, baseline_nodes=2, scaled_nodes=3) | 返回ScalabilityVerificationResult对象 |
| 4 | 检查result.passed | passed=True（efficiency=0.80 >= 0.70） |
| 5 | 检查result.efficiency, result.baseline_qps, result.scaled_qps | efficiency=0.80, baseline_qps=1000.0, scaled_qps=1400.0 |

### 验证点

- ScalabilityVerificationResult.passed == True
- efficiency == 0.80（(1400-1000)/(1000/2) = 400/500）
- baseline_qps == 1000.0, scaled_qps == 1400.0
- baseline_nodes == 2, scaled_nodes == 3, efficiency_threshold == 0.70

### 后置检查

- 临时CSV文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_006_linear_scalability.py::TestAnalyzeCSVPassing::test_passing_scalability
- **Test Type**: Real

---

### 用例编号

ST-FUNC-031-002

### 关联需求

NFR-006（Scalability: Horizontal Scaling — Adding 1 node yields >= 70% of theoretical throughput increase）

### 测试目标

验证ScalabilityReportAnalyzer.analyze()在效率低于阈值（efficiency=0.40）时返回passed=False

### 前置条件

- ScalabilityReportAnalyzer类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建baseline Locust CSV文件，Aggregated行Requests/s=1000.0 | CSV文件创建成功 |
| 2 | 创建scaled Locust CSV文件，Aggregated行Requests/s=1200.0 | CSV文件创建成功 |
| 3 | 调用ScalabilityReportAnalyzer().analyze(baseline_csv, scaled_csv, baseline_nodes=2, scaled_nodes=3) | 返回ScalabilityVerificationResult对象 |
| 4 | 检查result.passed | passed=False（efficiency=0.40 < 0.70） |
| 5 | 检查result.efficiency | efficiency=0.40（(1200-1000)/(1000/2) = 200/500） |

### 验证点

- ScalabilityVerificationResult.passed == False
- efficiency == 0.40
- baseline_qps == 1000.0, scaled_qps == 1200.0

### 后置检查

- 临时CSV文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_006_linear_scalability.py::TestAnalyzeCSVFailing::test_failing_scalability
- **Test Type**: Real

---

### 用例编号

ST-FUNC-031-003

### 关联需求

NFR-006（Scalability: Horizontal Scaling — Adding 1 node yields >= 70% of theoretical throughput increase）

### 测试目标

验证analyze_from_stats()在超线性扩展场景（efficiency=1.05）下正确返回passed=True

### 前置条件

- ScalabilityReportAnalyzer类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用analyze_from_stats(baseline_qps=900.0, scaled_qps=1530.0, baseline_nodes=3, scaled_nodes=5) | 返回ScalabilityVerificationResult对象 |
| 2 | 检查result.passed | passed=True（efficiency=1.05 >= 0.70） |
| 3 | 检查result.efficiency | efficiency=1.05（(1530-900)/(900/3*2) = 630/600） |
| 4 | 检查result.baseline_nodes, result.scaled_nodes | baseline_nodes=3, scaled_nodes=5 |

### 验证点

- ScalabilityVerificationResult.passed == True
- efficiency == 1.05（超线性扩展：实际增量超过理论增量）
- 正确处理多节点增加（从3节点到5节点）

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_006_linear_scalability.py::TestFromStatsSuperLinear::test_superlinear_scalability
- **Test Type**: Real

---

### 用例编号

ST-FUNC-031-004

### 关联需求

NFR-006（Scalability: Horizontal Scaling — Adding 1 node yields >= 70% of theoretical throughput increase）

### 测试目标

验证错误处理：CSV文件不存在、节点数无效、baseline QPS为零/负数时正确抛出异常

### 前置条件

- ScalabilityReportAnalyzer类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用analyze(baseline_csv="/nonexistent/path.csv", ...) | 抛出FileNotFoundError |
| 2 | 调用analyze(baseline_csv=valid, scaled_csv="/nonexistent/path.csv", ...) | 抛出FileNotFoundError |
| 3 | 调用analyze(..., baseline_nodes=0, scaled_nodes=3) | 抛出ValueError("baseline_nodes must be >= 1") |
| 4 | 调用analyze(..., baseline_nodes=2, scaled_nodes=2) | 抛出ValueError("scaled_nodes must be > baseline_nodes") |
| 5 | 调用analyze(..., baseline_nodes=3, scaled_nodes=1) | 抛出ValueError("scaled_nodes must be > baseline_nodes") |
| 6 | 调用analyze_from_stats(baseline_qps=0.0, ...) | 抛出ValueError("baseline_qps must be > 0") |
| 7 | 调用analyze_from_stats(baseline_qps=-10.0, ...) | 抛出ValueError("baseline_qps must be > 0") |
| 8 | 调用analyze(baseline CSV含0.0 QPS, ...) | 抛出ValueError("baseline QPS must be > 0") |

### 验证点

- FileNotFoundError在baseline CSV不存在时抛出
- FileNotFoundError在scaled CSV不存在时抛出
- ValueError在baseline_nodes < 1时抛出
- ValueError在scaled_nodes == baseline_nodes时抛出
- ValueError在scaled_nodes < baseline_nodes时抛出
- ValueError在baseline_qps <= 0时抛出（analyze_from_stats）
- ValueError在baseline CSV中QPS=0时抛出（analyze）

### 后置检查

- 临时CSV文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_006_linear_scalability.py::TestBaselineCSVNotFound::test_missing_baseline_csv, test_nfr_006_linear_scalability.py::TestScaledCSVNotFound::test_missing_scaled_csv, test_nfr_006_linear_scalability.py::TestBaselineNodesTooLow::test_baseline_nodes_zero, test_nfr_006_linear_scalability.py::TestScaledNodesEqual::test_equal_node_counts, test_nfr_006_linear_scalability.py::TestScaledNodesLess::test_reversed_node_counts, test_nfr_006_linear_scalability.py::TestFromStatsZeroQPS::test_zero_baseline_qps, test_nfr_006_linear_scalability.py::TestFromStatsNegativeQPS::test_negative_baseline_qps, test_nfr_006_linear_scalability.py::TestCSVZeroQPS::test_zero_qps_in_csv
- **Test Type**: Real

---

### 用例编号

ST-FUNC-031-005

### 关联需求

NFR-006（Scalability: Horizontal Scaling — Adding 1 node yields >= 70% of theoretical throughput increase）

### 测试目标

验证ScalabilityVerificationResult.summary()正确格式化包含NFR-006标识、判定结果和指标值

### 前置条件

- ScalabilityVerificationResult类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建passing ScalabilityVerificationResult(passed=True, efficiency=0.80, baseline_qps=1000.0, scaled_qps=1400.0, baseline_nodes=2, scaled_nodes=3, efficiency_threshold=0.70) | 对象创建成功 |
| 2 | 调用result.summary() | 返回包含"NFR-006"、"PASS"、"80.00%"、baseline_qps=1000.0、scaled_qps=1400.0的字符串 |
| 3 | 创建failing ScalabilityVerificationResult(passed=False, efficiency=0.40, baseline_qps=1000.0, scaled_qps=1200.0, baseline_nodes=2, scaled_nodes=3, efficiency_threshold=0.70) | 对象创建成功 |
| 4 | 调用result.summary() | 返回包含"NFR-006"、"FAIL"、"40.00%"的字符串 |

### 验证点

- passing结果的summary包含"NFR-006"、"PASS"、"80.00%"、baseline/scaled QPS和节点数
- failing结果的summary包含"NFR-006"、"FAIL"、"40.00%"
- summary格式符合设计文档规定

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: Medium
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_006_linear_scalability.py::TestSummaryPassing::test_summary_format_pass, test_nfr_006_linear_scalability.py::TestSummaryFailing::test_summary_format_fail
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-031-001

### 关联需求

NFR-006（Scalability: Horizontal Scaling — Adding 1 node yields >= 70% of theoretical throughput increase）

### 测试目标

验证efficiency恰好等于threshold（0.70）时返回passed=True（确认使用>= 语义，非严格>）

### 前置条件

- ScalabilityReportAnalyzer类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用analyze_from_stats(baseline_qps=1000.0, scaled_qps=1350.0, baseline_nodes=2, scaled_nodes=3) | 返回ScalabilityVerificationResult对象 |
| 2 | 检查result.passed | passed=True（efficiency=0.70 >= 0.70） |
| 3 | 检查result.efficiency | efficiency=0.70（350/500 exactly at threshold） |

### 验证点

- ScalabilityVerificationResult.passed == True
- 使用 >= 比较（非严格 >）对efficiency_threshold
- efficiency == efficiency_threshold时通过

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_006_linear_scalability.py::TestExactlyAtThreshold::test_at_threshold_passes
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-031-002

### 关联需求

NFR-006（Scalability: Horizontal Scaling — Adding 1 node yields >= 70% of theoretical throughput increase）

### 测试目标

验证efficiency略低于threshold（0.698）时返回passed=False（边界检查）

### 前置条件

- ScalabilityReportAnalyzer类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用analyze_from_stats(baseline_qps=1000.0, scaled_qps=1349.0, baseline_nodes=2, scaled_nodes=3) | 返回ScalabilityVerificationResult对象 |
| 2 | 检查result.passed | passed=False（efficiency=0.698 < 0.70） |
| 3 | 检查result.efficiency | efficiency=0.698（349/500, 略低于阈值） |

### 验证点

- ScalabilityVerificationResult.passed == False
- efficiency == 0.698（略低于0.70阈值）
- 边界值0.698被正确拒绝

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_006_linear_scalability.py::TestJustBelowThreshold::test_below_threshold_fails
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-031-003

### 关联需求

NFR-006（Scalability: Horizontal Scaling — Adding 1 node yields >= 70% of theoretical throughput increase）

### 测试目标

验证负增量和零增量场景：scaled QPS低于或等于baseline QPS时efficiency为0.0

### 前置条件

- ScalabilityReportAnalyzer类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用analyze_from_stats(baseline_qps=1000.0, scaled_qps=900.0, baseline_nodes=2, scaled_nodes=3) | passed=False, efficiency=0.0（负增量被钳位为0） |
| 2 | 调用analyze_from_stats(baseline_qps=1000.0, scaled_qps=1000.0, baseline_nodes=2, scaled_nodes=3) | passed=False, efficiency=0.0（零增量） |
| 3 | 调用analyze_from_stats(baseline_qps=1000.0, scaled_qps=1000.0, baseline_nodes=2, scaled_nodes=3, efficiency_threshold=0.0) | passed=True（efficiency=0.0 >= 0.0，零阈值允许零效率） |

### 验证点

- 负增量（scaled < baseline）：efficiency钳位为0.0，不产生负efficiency
- 零增量（scaled == baseline）：efficiency == 0.0
- 零阈值（threshold=0.0）与零efficiency：passed=True（0.0 >= 0.0）

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_006_linear_scalability.py::TestNegativeIncrease::test_negative_increase_clamps_to_zero, test_nfr_006_linear_scalability.py::TestZeroIncrease::test_zero_increase_efficiency_zero, test_nfr_006_linear_scalability.py::TestZeroThreshold::test_zero_threshold_zero_increase_passes
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-031-004

### 关联需求

NFR-006（Scalability: Horizontal Scaling — Adding 1 node yields >= 70% of theoretical throughput increase）

### 测试目标

验证最小节点数边界（baseline_nodes=1, scaled_nodes=2）下的正确计算

### 前置条件

- ScalabilityReportAnalyzer类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用analyze_from_stats(baseline_qps=500.0, scaled_qps=850.0, baseline_nodes=1, scaled_nodes=2) | 返回ScalabilityVerificationResult对象 |
| 2 | 检查result.passed | passed=True（efficiency=0.70 >= 0.70） |
| 3 | 检查result.efficiency | efficiency=0.70（(850-500)/(500/1) = 350/500） |
| 4 | 检查result.baseline_nodes, result.scaled_nodes | baseline_nodes=1, scaled_nodes=2 |

### 验证点

- baseline_nodes=1（最小有效值）被正确接受
- efficiency在最小节点数场景下正确计算
- per_node_throughput = baseline_qps / 1 = 500

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_006_linear_scalability.py::TestMinimumNodeCount::test_one_to_two_nodes
- **Test Type**: Real

---

### 用例编号

ST-PERF-031-001

### 关联需求

NFR-006（Scalability: Horizontal Scaling — Adding 1 node yields >= 70% of theoretical throughput increase）

### 测试目标

验证完整的CSV写入→解析→scalability指标提取→阈值判定→结果格式化端到端流程，模拟真实Locust负载测试报告

### 前置条件

- ScalabilityReportAnalyzer类已实现且可导入
- ScalabilityVerificationResult类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建baseline Locust CSV文件（Aggregated行Requests/s=1000.0） | CSV文件创建成功 |
| 2 | 创建scaled Locust CSV文件（Aggregated行Requests/s=1400.0） | CSV文件创建成功 |
| 3 | 调用ScalabilityReportAnalyzer().analyze(baseline_csv, scaled_csv, baseline_nodes=2, scaled_nodes=3) | 返回ScalabilityVerificationResult |
| 4 | 检查所有指标字段 | passed=True, efficiency=0.80, baseline_qps=1000.0, scaled_qps=1400.0, baseline_nodes=2, scaled_nodes=3, efficiency_threshold=0.70 |
| 5 | 调用result.summary()确认输出格式 | 返回包含"NFR-006"、"PASS"、"80.00%"的格式化字符串 |

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
- **测试引用**: test_nfr_006_linear_scalability.py::TestRealScalabilityReportFeature31::test_real_csv_roundtrip_analyze_feature_31
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-031-001 | NFR-006 | VS-1: N nodes X QPS, N+1 nodes yields >= 0.7*(X/N) increase | test_passing_scalability | Real | PASS |
| ST-FUNC-031-002 | NFR-006 | VS-1: N nodes X QPS, N+1 nodes yields >= 0.7*(X/N) increase | test_failing_scalability | Real | PASS |
| ST-FUNC-031-003 | NFR-006 | VS-1: N nodes X QPS, N+1 nodes yields >= 0.7*(X/N) increase | test_superlinear_scalability | Real | PASS |
| ST-FUNC-031-004 | NFR-006 | VS-1: N nodes X QPS, N+1 nodes yields >= 0.7*(X/N) increase | test_missing_baseline_csv, test_missing_scaled_csv, test_baseline_nodes_zero, test_equal_node_counts, test_reversed_node_counts, test_zero_baseline_qps, test_negative_baseline_qps, test_zero_qps_in_csv | Real | PASS |
| ST-FUNC-031-005 | NFR-006 | VS-1: N nodes X QPS, N+1 nodes yields >= 0.7*(X/N) increase | test_summary_format_pass, test_summary_format_fail | Real | PASS |
| ST-BNDRY-031-001 | NFR-006 | VS-1: N nodes X QPS, N+1 nodes yields >= 0.7*(X/N) increase | test_at_threshold_passes | Real | PASS |
| ST-BNDRY-031-002 | NFR-006 | VS-1: N nodes X QPS, N+1 nodes yields >= 0.7*(X/N) increase | test_below_threshold_fails | Real | PASS |
| ST-BNDRY-031-003 | NFR-006 | VS-1: N nodes X QPS, N+1 nodes yields >= 0.7*(X/N) increase | test_negative_increase_clamps_to_zero, test_zero_increase_efficiency_zero, test_zero_threshold_zero_increase_passes | Real | PASS |
| ST-BNDRY-031-004 | NFR-006 | VS-1: N nodes X QPS, N+1 nodes yields >= 0.7*(X/N) increase | test_one_to_two_nodes | Real | PASS |
| ST-PERF-031-001 | NFR-006 | VS-1: N nodes X QPS, N+1 nodes yields >= 0.7*(X/N) increase | test_real_csv_roundtrip_analyze_feature_31 | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 10 |
| Passed | 10 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
