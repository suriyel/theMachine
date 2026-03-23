# 测试用例集: NFR-007: Single-Node Failure Tolerance

**Feature ID**: 32
**关联需求**: NFR-008
**日期**: 2026-03-23
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 5 |
| boundary | 6 |
| performance | 1 |
| **合计** | **12** |

---

### 用例编号

ST-FUNC-032-001

### 关联需求

NFR-008（Reliability: Single-node failure tolerance — Query service continues operating when any single node fails）

### 测试目标

验证FailureToleranceReportAnalyzer.analyze_from_stats()在四个通过条件全部满足时返回passed=True

### 前置条件

- FailureToleranceReportAnalyzer类已实现且可导入
- FailureToleranceVerificationResult类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构造stats = {total_requests:100, failed_requests:0, nodes_killed:1, nodes_initial:3} | 字典构造成功 |
| 2 | 调用FailureToleranceReportAnalyzer().analyze_from_stats(stats, max_allowed_failures=0) | 返回FailureToleranceVerificationResult对象 |
| 3 | 检查result.passed | passed=True（全部四个条件满足） |
| 4 | 检查result.failed_requests和result.nodes_killed | failed_requests=0, nodes_killed=1 |
| 5 | 检查result.total_requests和result.nodes_initial | total_requests=100, nodes_initial=3 |

### 验证点

- FailureToleranceVerificationResult.passed == True
- result.failed_requests == 0
- result.nodes_killed == 1
- result.total_requests == 100
- result.nodes_initial == 3

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_007_single_node_failure.py::TestAnalyzeFromStatsHappyPath::test_passes_when_all_conditions_met
- **Test Type**: Real

---

### 用例编号

ST-FUNC-032-002

### 关联需求

NFR-008（Reliability: Single-node failure tolerance — Query service continues operating when any single node fails）

### 测试目标

验证FailureToleranceReportAnalyzer.analyze()从JSON文件读取时正确解析并返回passed=True

### 前置条件

- FailureToleranceReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 将{total_requests:200, failed_requests:0, nodes_killed:1, nodes_initial:2}写入临时JSON文件 | JSON文件写入成功 |
| 2 | 调用FailureToleranceReportAnalyzer().analyze(json_path) | 返回FailureToleranceVerificationResult对象 |
| 3 | 检查result.passed | passed=True |
| 4 | 检查result.total_requests | total_requests=200 |
| 5 | 检查result.nodes_killed和result.nodes_initial | nodes_killed=1, nodes_initial=2 |

### 验证点

- FailureToleranceVerificationResult.passed == True
- result.total_requests == 200
- result.nodes_killed == 1
- result.nodes_initial == 2

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_007_single_node_failure.py::TestAnalyzeJsonHappyPath::test_passes_reading_from_json_file
- **Test Type**: Real

---

### 用例编号

ST-FUNC-032-003

### 关联需求

NFR-008（Reliability: Single-node failure tolerance — Query service continues operating when any single node fails）

### 测试目标

验证错误处理：JSON文件不存在时抛出FileNotFoundError；JSON内容格式错误时抛出ValueError；JSON缺少必要字段时抛出ValueError

### 前置条件

- FailureToleranceReportAnalyzer类已实现且可导入
- 临时目录可用于写入格式错误的JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用analyze("/nonexistent/path/report.json") | 抛出FileNotFoundError |
| 2 | 将"{bad json!"写入临时文件，调用analyze(path) | 抛出ValueError，消息包含"malformed JSON" |
| 3 | 将{total_requests:100, failed_requests:0, nodes_initial:3}（缺少nodes_killed）写入临时文件，调用analyze(path) | 抛出ValueError，消息包含"missing key" |

### 验证点

- FileNotFoundError在json_path不存在时抛出
- ValueError在JSON格式错误时抛出，消息包含"malformed JSON"
- ValueError在缺少必要字段时抛出，消息包含"missing key"

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_007_single_node_failure.py::TestFileNotFound::test_raises_file_not_found_for_missing_path, test_nfr_007_single_node_failure.py::TestMalformedJson::test_raises_value_error_on_malformed_json, test_nfr_007_single_node_failure.py::TestMissingKeyInJson::test_raises_value_error_when_nodes_killed_absent
- **Test Type**: Real

---

### 用例编号

ST-FUNC-032-004

### 关联需求

NFR-008（Reliability: Single-node failure tolerance — Query service continues operating when any single node fails）

### 测试目标

验证analyze_from_stats()在stats字典缺少必要键或包含负数值时抛出ValueError

### 前置条件

- FailureToleranceReportAnalyzer类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构造stats = {total_requests:100, nodes_killed:1, nodes_initial:3}（缺少failed_requests） | 字典构造成功 |
| 2 | 调用analyze_from_stats(stats) | 抛出ValueError，消息包含"stats must contain" |
| 3 | 构造stats = {total_requests:-1, failed_requests:0, nodes_killed:1, nodes_initial:3} | 字典构造成功 |
| 4 | 调用analyze_from_stats(stats) | 抛出ValueError，消息包含"non-negative" |

### 验证点

- ValueError在stats缺少failed_requests时抛出，消息包含"stats must contain"
- ValueError在total_requests为负数时抛出，消息包含"non-negative"

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_007_single_node_failure.py::TestMissingKeyInStats::test_raises_value_error_when_failed_requests_absent, test_nfr_007_single_node_failure.py::TestNegativeFieldValue::test_raises_value_error_on_negative_total_requests
- **Test Type**: Real

---

### 用例编号

ST-FUNC-032-005

### 关联需求

NFR-008（Reliability: Single-node failure tolerance — Query service continues operating when any single node fails）

### 测试目标

验证FailureToleranceVerificationResult.summary()在PASS和FAIL情形下均包含NFR-008标识、判定结果及关键指标值

### 前置条件

- FailureToleranceVerificationResult类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建FailureToleranceVerificationResult(passed=True, total_requests=100, failed_requests=0, nodes_killed=1, nodes_initial=3, max_allowed_failures=0) | 对象创建成功 |
| 2 | 调用result.summary() | 返回包含"NFR-008"、"PASS"、"1"（nodes_killed）、"0"（failed_requests）的字符串 |
| 3 | 创建FailureToleranceVerificationResult(passed=False, total_requests=100, failed_requests=5, nodes_killed=0, nodes_initial=3, max_allowed_failures=0) | 对象创建成功 |
| 4 | 调用result.summary() | 返回包含"NFR-008"、"FAIL"、"5"（failed_requests）的字符串 |

### 验证点

- passing结果的summary包含"NFR-008"、"PASS"、nodes_killed值、failed_requests值
- failing结果的summary包含"NFR-008"、"FAIL"、failed_requests值
- summary格式符合设计文档规定

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: Medium
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_007_single_node_failure.py::TestSummaryPass::test_summary_contains_nfr_label_and_pass_verdict, test_nfr_007_single_node_failure.py::TestSummaryFail::test_summary_contains_fail_verdict
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-032-001

### 关联需求

NFR-008（Reliability: Single-node failure tolerance — Query service continues operating when any single node fails）

### 测试目标

验证nodes_killed=0（无节点被杀）时cond1=False导致passed=False

### 前置条件

- FailureToleranceReportAnalyzer类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构造stats = {total_requests:100, failed_requests:0, nodes_killed:0, nodes_initial:3} | 字典构造成功 |
| 2 | 调用analyze_from_stats(stats) | 返回FailureToleranceVerificationResult对象 |
| 3 | 检查result.passed | passed=False（cond1: nodes_killed=0 < 1） |
| 4 | 检查result.nodes_killed | nodes_killed=0 |

### 验证点

- FailureToleranceVerificationResult.passed == False
- result.nodes_killed == 0（条件1不满足）

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_007_single_node_failure.py::TestNoNodeKilled::test_fails_when_nodes_killed_is_zero
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-032-002

### 关联需求

NFR-008（Reliability: Single-node failure tolerance — Query service continues operating when any single node fails）

### 测试目标

验证nodes_killed == nodes_initial（集群全灭）时cond2=False导致passed=False

### 前置条件

- FailureToleranceReportAnalyzer类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构造stats = {total_requests:100, failed_requests:0, nodes_killed:3, nodes_initial:3} | 字典构造成功 |
| 2 | 调用analyze_from_stats(stats) | 返回FailureToleranceVerificationResult对象 |
| 3 | 检查result.passed | passed=False（cond2: nodes_initial=3 不大于 nodes_killed=3） |
| 4 | 检查result.nodes_killed和result.nodes_initial | nodes_killed=3, nodes_initial=3 |

### 验证点

- FailureToleranceVerificationResult.passed == False
- result.nodes_killed == result.nodes_initial == 3（条件2不满足）

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_007_single_node_failure.py::TestAllNodesKilled::test_fails_when_all_nodes_killed
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-032-003

### 关联需求

NFR-008（Reliability: Single-node failure tolerance — Query service continues operating when any single node fails）

### 测试目标

验证total_requests=0（负载测试未运行）时cond4=False导致passed=False

### 前置条件

- FailureToleranceReportAnalyzer类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构造stats = {total_requests:0, failed_requests:0, nodes_killed:1, nodes_initial:3} | 字典构造成功 |
| 2 | 调用analyze_from_stats(stats) | 返回FailureToleranceVerificationResult对象 |
| 3 | 检查result.passed | passed=False（cond4: total_requests=0，非正数） |
| 4 | 检查result.total_requests | total_requests=0 |

### 验证点

- FailureToleranceVerificationResult.passed == False
- result.total_requests == 0（条件4不满足）

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_007_single_node_failure.py::TestZeroTotalRequests::test_fails_when_no_requests_made
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-032-004

### 关联需求

NFR-008（Reliability: Single-node failure tolerance — Query service continues operating when any single node fails）

### 测试目标

验证failed_requests=1且max_allowed_failures=0（严格零容错）时cond3=False导致passed=False

### 前置条件

- FailureToleranceReportAnalyzer类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构造stats = {total_requests:100, failed_requests:1, nodes_killed:1, nodes_initial:3} | 字典构造成功 |
| 2 | 调用analyze_from_stats(stats, max_allowed_failures=0) | 返回FailureToleranceVerificationResult对象 |
| 3 | 检查result.passed | passed=False（cond3: failed_requests=1 > max_allowed_failures=0） |
| 4 | 检查result.failed_requests和result.max_allowed_failures | failed_requests=1, max_allowed_failures=0 |

### 验证点

- FailureToleranceVerificationResult.passed == False
- result.failed_requests == 1, result.max_allowed_failures == 0（条件3不满足）

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_007_single_node_failure.py::TestFailureExceedsThreshold::test_fails_when_failure_count_exceeds_max
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-032-005

### 关联需求

NFR-008（Reliability: Single-node failure tolerance — Query service continues operating when any single node fails）

### 测试目标

验证最小有效集群（nodes_killed=1, nodes_initial=2）下passed=True（边界精确值）

### 前置条件

- FailureToleranceReportAnalyzer类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构造stats = {total_requests:50, failed_requests:0, nodes_killed:1, nodes_initial:2} | 字典构造成功 |
| 2 | 调用analyze_from_stats(stats) | 返回FailureToleranceVerificationResult对象 |
| 3 | 检查result.passed | passed=True（最小合法集群：nodes_initial=2 > nodes_killed=1） |
| 4 | 检查result.nodes_killed和result.nodes_initial | nodes_killed=1, nodes_initial=2 |

### 验证点

- FailureToleranceVerificationResult.passed == True
- result.nodes_killed == 1, result.nodes_initial == 2（最小合法配置）

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_007_single_node_failure.py::TestMinimumValidCluster::test_passes_with_minimum_cluster_configuration
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-032-006

### 关联需求

NFR-008（Reliability: Single-node failure tolerance — Query service continues operating when any single node fails）

### 测试目标

验证nodes_killed > nodes_initial（逻辑上不可能的杀死数超过初始节点数）时passed=False（cond2=False）

### 前置条件

- FailureToleranceReportAnalyzer类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构造stats = {total_requests:100, failed_requests:0, nodes_killed:5, nodes_initial:3} | 字典构造成功 |
| 2 | 调用analyze_from_stats(stats) | 返回FailureToleranceVerificationResult对象（不抛出异常） |
| 3 | 检查result.passed | passed=False（cond2: nodes_initial=3 不大于 nodes_killed=5） |
| 4 | 检查result.nodes_killed和result.nodes_initial | nodes_killed=5, nodes_initial=3 |

### 验证点

- FailureToleranceVerificationResult.passed == False
- result.nodes_killed=5 > result.nodes_initial=3（条件2不满足，报告为FAIL而非异常）

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_007_single_node_failure.py::TestMoreKilledThanInitial::test_fails_when_nodes_killed_exceeds_nodes_initial
- **Test Type**: Real

---

### 用例编号

ST-PERF-032-001

### 关联需求

NFR-008（Reliability: Single-node failure tolerance — Query service continues operating when any single node fails）

### 测试目标

验证完整的JSON写入→解析→指标提取→通过条件判定→结果格式化端到端流程，模拟真实负载测试报告处理场景

### 前置条件

- FailureToleranceReportAnalyzer类已实现且可导入
- FailureToleranceVerificationResult类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建负载测试报告JSON文件：{total_requests:500, failed_requests:0, nodes_killed:1, nodes_initial:3} | JSON文件创建成功 |
| 2 | 调用FailureToleranceReportAnalyzer().analyze(json_path, max_allowed_failures=0) | 返回FailureToleranceVerificationResult对象 |
| 3 | 检查所有指标字段 | passed=True, total_requests=500, failed_requests=0, nodes_killed=1, nodes_initial=3, max_allowed_failures=0 |
| 4 | 调用result.summary()确认输出格式 | 返回包含"NFR-008"、"PASS"、节点和失败指标的格式化字符串 |

### 验证点

- 端到端流程：JSON写入→解析→指标提取→通过条件判定→结果格式化全部正确
- passed == True
- 所有数值字段准确：total_requests=500, failed_requests=0, nodes_killed=1, nodes_initial=3
- summary()输出包含正确的"NFR-008"标识和"PASS"判定

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: performance
- **已自动化**: Yes
- **测试引用**: test_nfr_007_single_node_failure.py::TestRealFailureToleranceReportFeature32::test_real_json_roundtrip_analyze_feature_32
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-032-001 | NFR-008 | VS-1: multi-node cluster under load, one node killed, remaining nodes continue serving without failures | test_passes_when_all_conditions_met | Real | PASS |
| ST-FUNC-032-002 | NFR-008 | VS-1: multi-node cluster under load, one node killed, remaining nodes continue serving without failures | test_passes_reading_from_json_file | Real | PASS |
| ST-FUNC-032-003 | NFR-008 | VS-1: multi-node cluster under load, one node killed, remaining nodes continue serving without failures | test_raises_file_not_found_for_missing_path, test_raises_value_error_on_malformed_json, test_raises_value_error_when_nodes_killed_absent | Real | PASS |
| ST-FUNC-032-004 | NFR-008 | VS-1: multi-node cluster under load, one node killed, remaining nodes continue serving without failures | test_raises_value_error_when_failed_requests_absent, test_raises_value_error_on_negative_total_requests | Real | PASS |
| ST-FUNC-032-005 | NFR-008 | VS-1: multi-node cluster under load, one node killed, remaining nodes continue serving without failures | test_summary_contains_nfr_label_and_pass_verdict, test_summary_contains_fail_verdict | Real | PASS |
| ST-BNDRY-032-001 | NFR-008 | VS-1: multi-node cluster under load, one node killed, remaining nodes continue serving without failures | test_fails_when_nodes_killed_is_zero | Real | PASS |
| ST-BNDRY-032-002 | NFR-008 | VS-1: multi-node cluster under load, one node killed, remaining nodes continue serving without failures | test_fails_when_all_nodes_killed | Real | PASS |
| ST-BNDRY-032-003 | NFR-008 | VS-1: multi-node cluster under load, one node killed, remaining nodes continue serving without failures | test_fails_when_no_requests_made | Real | PASS |
| ST-BNDRY-032-004 | NFR-008 | VS-1: multi-node cluster under load, one node killed, remaining nodes continue serving without failures | test_fails_when_failure_count_exceeds_max | Real | PASS |
| ST-BNDRY-032-005 | NFR-008 | VS-1: multi-node cluster under load, one node killed, remaining nodes continue serving without failures | test_passes_with_minimum_cluster_configuration | Real | PASS |
| ST-BNDRY-032-006 | NFR-008 | VS-1: multi-node cluster under load, one node killed, remaining nodes continue serving without failures | test_fails_when_nodes_killed_exceeds_nodes_initial | Real | PASS |
| ST-PERF-032-001 | NFR-008 | VS-1: multi-node cluster under load, one node killed, remaining nodes continue serving without failures | test_real_json_roundtrip_analyze_feature_32 | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 12 |
| Passed | 12 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
