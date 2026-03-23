# 测试用例集: NFR-005: Service Availability 99.9%

**Feature ID**: 30
**关联需求**: NFR-007
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

ST-FUNC-030-001

### 关联需求

NFR-007（Reliability: Service Availability 99.9% uptime）

### 测试目标

验证AvailabilityReportAnalyzer.analyze()在所有health check均为success时返回passed=True，正确提取所有指标

### 前置条件

- AvailabilityReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JSON uptime报告文件，包含1000个check条目，全部status="success" | JSON文件创建成功 |
| 2 | 调用AvailabilityReportAnalyzer().analyze(json_path, min_uptime_ratio=0.999) | 返回AvailabilityVerificationResult对象 |
| 3 | 检查result.passed | passed=True（所有check成功，uptime_ratio=1.0 >= 0.999） |
| 4 | 检查result.total_checks, result.successful_checks | total_checks=1000, successful_checks=1000 |
| 5 | 检查result.uptime_ratio | uptime_ratio=1.0 |

### 验证点

- AvailabilityVerificationResult.passed == True
- total_checks == 1000
- successful_checks == 1000
- uptime_ratio == 1.0

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_005_service_availability.py::TestAnalyzeHappyPath::test_passes_all_success
- **Test Type**: Real

---

### 用例编号

ST-FUNC-030-002

### 关联需求

NFR-007（Reliability: Service Availability 99.9% uptime）

### 测试目标

验证当uptime_ratio略高于阈值（99.95%）时analyze()返回passed=True

### 前置条件

- AvailabilityReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JSON uptime报告文件，包含10000个check条目：9995个success、5个failure（99.95% uptime） | JSON文件创建成功 |
| 2 | 调用AvailabilityReportAnalyzer().analyze(json_path, min_uptime_ratio=0.999) | 返回AvailabilityVerificationResult对象 |
| 3 | 检查result.passed | passed=True（uptime_ratio=0.9995 >= 0.999） |
| 4 | 检查result.uptime_ratio | uptime_ratio=0.9995 |
| 5 | 检查result.successful_checks | successful_checks=9995 |

### 验证点

- AvailabilityVerificationResult.passed == True
- uptime_ratio == 0.9995（略高于0.999阈值）
- total_checks == 10000, successful_checks == 9995

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_005_service_availability.py::TestAnalyzeHappyPath::test_passes_above_threshold
- **Test Type**: Real

---

### 用例编号

ST-FUNC-030-003

### 关联需求

NFR-007（Reliability: Service Availability 99.9% uptime）

### 测试目标

验证当uptime_ratio低于阈值（99.8%）时analyze()返回passed=False

### 前置条件

- AvailabilityReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JSON uptime报告文件，包含1000个check条目：998个success、2个failure（99.8% uptime） | JSON文件创建成功 |
| 2 | 调用AvailabilityReportAnalyzer().analyze(json_path, min_uptime_ratio=0.999) | 返回AvailabilityVerificationResult对象 |
| 3 | 检查result.passed | passed=False（uptime_ratio=0.998 < 0.999） |
| 4 | 检查result.uptime_ratio | uptime_ratio=0.998 |

### 验证点

- AvailabilityVerificationResult.passed == False
- uptime_ratio == 0.998（低于0.999阈值）
- total_checks == 1000, successful_checks == 998

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_005_service_availability.py::TestAnalyzeHappyPath::test_fails_below_threshold
- **Test Type**: Real

---

### 用例编号

ST-FUNC-030-004

### 关联需求

NFR-007（Reliability: Service Availability 99.9% uptime）

### 测试目标

验证analyze_from_stats()通过编程接口正确计算uptime指标并返回通过/失败结果，以及错误处理

### 前置条件

- AvailabilityReportAnalyzer类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用analyze_from_stats({"total_checks":43200, "successful_checks":43157}, min_uptime_ratio=0.999) | passed=True, uptime_ratio≈0.999004 >= 0.999 |
| 2 | 调用analyze_from_stats({"total_checks":5, "successful_checks":5}, min_total_checks=100) | passed=False（total_checks=5 < min_total_checks=100） |
| 3 | 调用analyze_from_stats({"successful_checks":10})（缺少total_checks键） | 抛出ValueError，包含"total_checks" |
| 4 | 调用analyze_from_stats({"total_checks":-1, "successful_checks":0}) | 抛出ValueError，包含"non-negative" |

### 验证点

- stats path正确计算uptime_ratio并与阈值比较
- min_total_checks条件被正确执行
- 缺少必要键时抛出ValueError
- 负数值时抛出ValueError

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_005_service_availability.py::TestAnalyzeHappyPath::test_stats_passes_above_threshold, test_nfr_005_service_availability.py::TestAnalyzeHappyPath::test_fails_insufficient_checks, test_nfr_005_service_availability.py::TestAnalyzeErrors::test_stats_missing_keys, test_nfr_005_service_availability.py::TestAnalyzeErrors::test_stats_negative_count
- **Test Type**: Real

---

### 用例编号

ST-FUNC-030-005

### 关联需求

NFR-007（Reliability: Service Availability 99.9% uptime）

### 测试目标

验证AvailabilityVerificationResult.summary()正确格式化包含NFR-007标识、判定结果和指标值

### 前置条件

- AvailabilityVerificationResult类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建passing AvailabilityVerificationResult(passed=True, total_checks=1000, successful_checks=1000, uptime_ratio=1.0, ...) | 对象创建成功 |
| 2 | 调用result.summary() | 返回包含"NFR-007"、"PASS"、"1000"、uptime_ratio的字符串 |
| 3 | 创建failing AvailabilityVerificationResult(passed=False, total_checks=1000, successful_checks=998, uptime_ratio=0.998, ...) | 对象创建成功 |
| 4 | 调用result.summary() | 返回包含"NFR-007"、"FAIL"、threshold值的字符串 |

### 验证点

- passing结果的summary包含"NFR-007"、"PASS"、total_checks、uptime_ratio
- failing结果的summary包含"NFR-007"、"FAIL"、threshold值
- summary格式符合设计文档规定

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: Medium
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_005_service_availability.py::TestVerificationResultSummary::test_summary_pass_format, test_nfr_005_service_availability.py::TestVerificationResultSummary::test_summary_fail_format
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-030-001

### 关联需求

NFR-007（Reliability: Service Availability 99.9% uptime）

### 测试目标

验证uptime_ratio恰好等于min_uptime_ratio(0.999)时返回passed=True（确认使用>= 语义，非严格>）

### 前置条件

- AvailabilityReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JSON uptime报告文件，包含1000个check条目：999个success、1个failure（uptime_ratio=0.999 exactly） | JSON文件创建成功 |
| 2 | 调用analyze(json_path, min_uptime_ratio=0.999) | 返回AvailabilityVerificationResult对象 |
| 3 | 检查result.passed | passed=True（uptime_ratio=0.999 == min_uptime_ratio=0.999，使用>=） |
| 4 | 检查result.uptime_ratio | uptime_ratio == 0.999 |

### 验证点

- AvailabilityVerificationResult.passed == True
- 使用 >= 比较（非严格 >）对min_uptime_ratio
- uptime_ratio == min_uptime_ratio时通过

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_005_service_availability.py::TestAnalyzeBoundary::test_passes_at_exact_threshold
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-030-002

### 关联需求

NFR-007（Reliability: Service Availability 99.9% uptime）

### 测试目标

验证uptime_ratio略低于阈值（0.9989）时返回passed=False（边界检查）

### 前置条件

- AvailabilityReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JSON uptime报告文件，包含10000个check条目：9989个success、11个failure（uptime_ratio=0.9989） | JSON文件创建成功 |
| 2 | 调用analyze(json_path, min_uptime_ratio=0.999) | 返回AvailabilityVerificationResult对象 |
| 3 | 检查result.passed | passed=False（uptime_ratio=0.9989 < 0.999） |
| 4 | 检查result.uptime_ratio | uptime_ratio == 0.9989 |

### 验证点

- AvailabilityVerificationResult.passed == False
- uptime_ratio == 0.9989（略低于0.999阈值）
- 边界值0.9989被正确拒绝

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_005_service_availability.py::TestAnalyzeBoundary::test_fails_just_below_threshold
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-030-003

### 关联需求

NFR-007（Reliability: Service Availability 99.9% uptime）

### 测试目标

验证analyze_from_stats在total_checks=0时不产生ZeroDivisionError，以及单个check的边界情况

### 前置条件

- AvailabilityReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用analyze_from_stats({"total_checks":0, "successful_checks":0}, min_total_checks=1) | passed=False, uptime_ratio=0.0, 无ZeroDivisionError |
| 2 | 创建JSON uptime报告文件，包含1个check：status="success" | JSON文件创建成功 |
| 3 | 调用analyze(json_path, min_uptime_ratio=0.999) | passed=True, uptime_ratio=1.0（单check成功） |
| 4 | 创建JSON uptime报告文件，包含1个check：status="failure" | JSON文件创建成功 |
| 5 | 调用analyze(json_path, min_uptime_ratio=0.999) | passed=False, uptime_ratio=0.0（单check失败） |

### 验证点

- total_checks=0时不产生ZeroDivisionError，uptime_ratio=0.0
- 单个success check：uptime_ratio=1.0，passed=True
- 单个failure check：uptime_ratio=0.0，passed=False

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_005_service_availability.py::TestAnalyzeBoundary::test_zero_total_checks_no_division_error, test_nfr_005_service_availability.py::TestAnalyzeBoundary::test_single_check_success, test_nfr_005_service_availability.py::TestAnalyzeBoundary::test_single_check_failure
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-030-004

### 关联需求

NFR-007（Reliability: Service Availability 99.9% uptime）

### 测试目标

验证JSON报告的错误处理：文件不存在、JSON格式错误、缺少checks键、空checks列表

### 前置条件

- AvailabilityReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用analyze("/nonexistent/report.json") | 抛出FileNotFoundError |
| 2 | 创建包含无效JSON内容的文件，调用analyze() | 抛出ValueError，消息包含"malformed JSON" |
| 3 | 创建JSON文件但缺少"checks"键，调用analyze() | 抛出ValueError，消息包含"checks" |
| 4 | 创建JSON文件包含空checks列表，调用analyze() | 抛出ValueError，消息包含"empty" |

### 验证点

- 文件不存在时抛出FileNotFoundError
- JSON格式错误时抛出ValueError("malformed JSON")
- 缺少checks键时抛出ValueError("checks")
- 空列表时抛出ValueError("empty")

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_005_service_availability.py::TestAnalyzeErrors::test_file_not_found, test_nfr_005_service_availability.py::TestAnalyzeErrors::test_malformed_json, test_nfr_005_service_availability.py::TestAnalyzeErrors::test_missing_checks_key, test_nfr_005_service_availability.py::TestAnalyzeErrors::test_empty_checks_list
- **Test Type**: Real

---

### 用例编号

ST-PERF-030-001

### 关联需求

NFR-007（Reliability: Service Availability 99.9% uptime）

### 测试目标

验证完整的JSON报告写入→解析→uptime指标提取→阈值判定→结果格式化端到端流程，模拟真实uptime监控报告

### 前置条件

- AvailabilityReportAnalyzer类已实现且可导入
- AvailabilityVerificationResult类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建包含1000个check条目（全部success）的JSON uptime报告文件 | JSON文件创建成功 |
| 2 | 调用AvailabilityReportAnalyzer().analyze(json_path, min_uptime_ratio=0.999) | 返回AvailabilityVerificationResult |
| 3 | 检查result.passed | passed=True |
| 4 | 检查所有指标字段 | total_checks=1000, successful_checks=1000, uptime_ratio=1.0, min_uptime_ratio=0.999, min_total_checks=1 |
| 5 | 调用result.summary()确认输出格式 | 返回包含"NFR-007"的格式化字符串 |

### 验证点

- 端到端流程：JSON写入→解析→指标提取→阈值判定→结果格式化全部正确
- passed == True
- 所有数值字段准确
- summary()输出包含正确的NFR标识和判定结果

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: performance
- **已自动化**: Yes
- **测试引用**: test_nfr_005_service_availability.py::TestRealAvailabilityReportFeature30::test_real_json_roundtrip_analyze_feature_30
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-030-001 | NFR-007 | VS-1: uptime exceeds 99.9% with automatic recovery | test_passes_all_success | Real | PASS |
| ST-FUNC-030-002 | NFR-007 | VS-1: uptime exceeds 99.9% with automatic recovery | test_passes_above_threshold | Real | PASS |
| ST-FUNC-030-003 | NFR-007 | VS-1: uptime exceeds 99.9% with automatic recovery | test_fails_below_threshold | Real | PASS |
| ST-FUNC-030-004 | NFR-007 | VS-1: uptime exceeds 99.9% with automatic recovery | test_stats_passes_above_threshold, test_fails_insufficient_checks, test_stats_missing_keys, test_stats_negative_count | Real | PASS |
| ST-FUNC-030-005 | NFR-007 | VS-1: uptime exceeds 99.9% with automatic recovery | test_summary_pass_format, test_summary_fail_format | Real | PASS |
| ST-BNDRY-030-001 | NFR-007 | VS-1: uptime exceeds 99.9% with automatic recovery | test_passes_at_exact_threshold | Real | PASS |
| ST-BNDRY-030-002 | NFR-007 | VS-1: uptime exceeds 99.9% with automatic recovery | test_fails_just_below_threshold | Real | PASS |
| ST-BNDRY-030-003 | NFR-007 | VS-1: uptime exceeds 99.9% with automatic recovery | test_zero_total_checks_no_division_error, test_single_check_success, test_single_check_failure | Real | PASS |
| ST-BNDRY-030-004 | NFR-007 | VS-1: uptime exceeds 99.9% with automatic recovery | test_file_not_found, test_malformed_json, test_missing_checks_key, test_empty_checks_list | Real | PASS |
| ST-PERF-030-001 | NFR-007 | VS-1: uptime exceeds 99.9% with automatic recovery | test_real_json_roundtrip_analyze_feature_30 | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 10 |
| Passed | 10 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
