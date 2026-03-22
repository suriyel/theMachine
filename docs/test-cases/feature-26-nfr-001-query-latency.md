# 测试用例集: NFR-001: Query Latency p95 < 1s

**Feature ID**: 26
**关联需求**: NFR-001
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

ST-FUNC-026-001

### 关联需求

NFR-001（Query response latency p95 < 1000ms）

### 测试目标

验证LatencyReportAnalyzer.analyze()在p95低于阈值时返回passed=True并正确提取所有指标

### 前置条件

- LatencyReportAnalyzer类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Locust格式CSV文件，包含Aggregated行：p95=487ms, p99=650ms, median=200ms, avg=250ms, total_requests=10000, failure_count=0 | CSV文件创建成功 |
| 2 | 调用LatencyReportAnalyzer().analyze(csv_path, p95_threshold_ms=1000.0) | 返回VerificationResult对象 |
| 3 | 检查result.passed | passed=True（487 <= 1000） |
| 4 | 检查result.p95_ms, p99_ms, median_ms, avg_ms | p95_ms=487.0, p99_ms=650.0, median_ms=200.0, avg_ms=250.0 |
| 5 | 检查result.total_requests和failure_rate | total_requests=10000, failure_rate=0.0 |

### 验证点

- VerificationResult.passed == True
- 所有指标字段从CSV正确提取
- failure_rate == 0.0（0/10000）
- threshold_ms == 1000.0

### 后置检查

- 临时CSV文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_001_query_latency.py::TestLatencyReportAnalyzerHappyPath::test_a_p95_under_threshold_passes
- **Test Type**: Real

---

### 用例编号

ST-FUNC-026-002

### 关联需求

NFR-001（Query response latency p95 < 1000ms）

### 测试目标

验证LatencyReportAnalyzer.analyze()在p95超过阈值时返回passed=False

### 前置条件

- LatencyReportAnalyzer类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Locust格式CSV文件，包含Aggregated行：p95=1200ms | CSV文件创建成功 |
| 2 | 调用LatencyReportAnalyzer().analyze(csv_path, p95_threshold_ms=1000.0) | 返回VerificationResult对象 |
| 3 | 检查result.passed | passed=False（1200 > 1000） |
| 4 | 检查result.p95_ms | p95_ms=1200.0 |

### 验证点

- VerificationResult.passed == False
- p95_ms正确反映CSV中的值1200.0

### 后置检查

- 临时CSV文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_001_query_latency.py::TestLatencyReportAnalyzerHappyPath::test_b_p95_over_threshold_fails
- **Test Type**: Real

---

### 用例编号

ST-FUNC-026-003

### 关联需求

NFR-001（Query response latency p95 < 1000ms）

### 测试目标

验证analyze_from_stats()从字典列表中正确聚合指标并判定阈值

### 前置条件

- LatencyReportAnalyzer类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构建stats列表：[{"p95_ms": 400, "p99_ms": 550, "median_ms": 180, "avg_ms": 200, "total_requests": 5000, "failure_count": 5}] | stats列表构建成功 |
| 2 | 调用analyzer.analyze_from_stats(stats, p95_threshold_ms=1000.0) | 返回VerificationResult对象 |
| 3 | 检查result.passed | passed=True（400 <= 1000） |
| 4 | 检查result.failure_rate | failure_rate ≈ 0.001（5/5000） |

### 验证点

- VerificationResult.passed == True
- p95_ms=400.0, p99_ms=550.0, median_ms=180.0, avg_ms=200.0
- total_requests=5000
- failure_rate ≈ 0.001

### 后置检查

- 无外部资源需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_001_query_latency.py::TestAnalyzeFromStats::test_m_from_stats_happy_path
- **Test Type**: Real

---

### 用例编号

ST-FUNC-026-004

### 关联需求

NFR-001（Query response latency p95 < 1000ms）

### 测试目标

验证QueryGenerator.generate_payloads()按mix_ratio正确生成NL和symbol查询混合负载

### 前置条件

- QueryGenerator类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用QueryGenerator().generate_payloads(count=10, mix_ratio=0.7) | 返回10个payload字典的列表 |
| 2 | 统计query_type=="nl"的数量 | 7个NL查询 |
| 3 | 统计query_type=="symbol"的数量 | 3个symbol查询 |
| 4 | 检查每个payload包含"query"键且为非空字符串 | 所有payload验证通过 |

### 验证点

- 返回列表长度为10
- NL查询数量 == 7（round(10 * 0.7)）
- Symbol查询数量 == 3
- 每个payload包含"query"和"query_type"键

### 后置检查

- 无外部资源需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_001_query_latency.py::TestQueryGenerator::test_h_default_mix_ratio
- **Test Type**: Real

---

### 用例编号

ST-FUNC-026-005

### 关联需求

NFR-001（Query response latency p95 < 1000ms）

### 测试目标

验证VerificationResult.summary()返回包含关键信息的人类可读摘要字符串

### 前置条件

- VerificationResult数据类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建VerificationResult(passed=True, p95_ms=487.0, p99_ms=650.0, median_ms=200.0, avg_ms=250.0, total_requests=10000, failure_rate=0.0, threshold_ms=1000.0) | 对象创建成功 |
| 2 | 调用result.summary() | 返回非空字符串 |
| 3 | 检查summary包含"PASS" | 包含"PASS"关键字 |
| 4 | 检查summary包含"487" | 包含p95值 |
| 5 | 检查summary包含请求数信息 | 包含"10000"或"10,000" |

### 验证点

- summary()返回非空字符串
- 包含verdict（PASS/FAIL）
- 包含p95延迟值
- 包含请求数量

### 后置检查

- 无外部资源需清理

### 元数据

- **优先级**: Medium
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_001_query_latency.py::TestVerificationResultSummary::test_o_summary_contains_key_info
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-026-001

### 关联需求

NFR-001（Query response latency p95 < 1000ms）

### 测试目标

验证p95恰好等于阈值时使用<=判定为通过（边界条件）

### 前置条件

- LatencyReportAnalyzer类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Locust格式CSV文件，包含Aggregated行：p95=1000ms | CSV文件创建成功 |
| 2 | 调用analyzer.analyze(csv_path, p95_threshold_ms=1000.0) | 返回VerificationResult对象 |
| 3 | 检查result.passed | passed=True（1000 <= 1000，使用<=而非<） |

### 验证点

- VerificationResult.passed == True
- p95_ms == 1000.0（精确等于阈值）
- 使用<=比较而非<比较

### 后置检查

- 临时CSV文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_001_query_latency.py::TestLatencyReportAnalyzerHappyPath::test_c_p95_equals_threshold_passes
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-026-002

### 关联需求

NFR-001（Query response latency p95 < 1000ms）

### 测试目标

验证CSV中total_requests=0时不发生除零错误，failure_rate=0.0

### 前置条件

- LatencyReportAnalyzer类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Locust格式CSV文件，包含Aggregated行：total_requests=0, failure_count=0 | CSV文件创建成功 |
| 2 | 调用analyzer.analyze(csv_path) | 返回VerificationResult对象，无异常 |
| 3 | 检查result.failure_rate | failure_rate=0.0（无除零错误） |
| 4 | 检查result.total_requests | total_requests=0 |

### 验证点

- 不抛出ZeroDivisionError
- failure_rate == 0.0
- total_requests == 0

### 后置检查

- 临时CSV文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_001_query_latency.py::TestLatencyReportAnalyzerBoundary::test_g_zero_requests_no_division_error
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-026-003

### 关联需求

NFR-001（Query response latency p95 < 1000ms）

### 测试目标

验证mix_ratio边界值：0.0产生全symbol查询，1.0产生全NL查询

### 前置条件

- QueryGenerator类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用generate_payloads(count=5, mix_ratio=0.0) | 返回5个payload |
| 2 | 检查所有payload的query_type | 全部为"symbol" |
| 3 | 调用generate_payloads(count=5, mix_ratio=1.0) | 返回5个payload |
| 4 | 检查所有payload的query_type | 全部为"nl" |

### 验证点

- mix_ratio=0.0时所有payload为symbol类型
- mix_ratio=1.0时所有payload为nl类型
- 两种情况均返回正确数量的payload

### 后置检查

- 无外部资源需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_001_query_latency.py::TestQueryGenerator::test_i_mix_ratio_zero_all_symbol, test_j_mix_ratio_one_all_nl
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-026-004

### 关联需求

NFR-001（Query response latency p95 < 1000ms）

### 测试目标

验证错误输入的边界处理：CSV不存在、无Aggregated行、CSV格式错误、count<=0、mix_ratio越界、空stats列表

### 前置条件

- LatencyReportAnalyzer和QueryGenerator类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用analyzer.analyze("/nonexistent/path/stats.csv") | 抛出FileNotFoundError |
| 2 | 创建仅包含endpoint行（无Aggregated行）的CSV，调用analyzer.analyze() | 抛出ValueError，消息包含"no aggregated stats row" |
| 3 | 创建缺少"95%"列的CSV（仅Type, Name, Request Count列），调用analyzer.analyze() | 抛出ValueError，消息包含"malformed CSV" |
| 4 | 调用generate_payloads(count=0) | 抛出ValueError，消息包含"count must be > 0" |
| 5 | 调用generate_payloads(count=5, mix_ratio=1.5) | 抛出ValueError，消息包含"mix_ratio must be in" |
| 6 | 调用generate_payloads(count=5, mix_ratio=-0.1) | 抛出ValueError，消息包含"mix_ratio must be in" |
| 7 | 调用analyzer.analyze_from_stats([], p95_threshold_ms=1000.0) | 抛出ValueError，消息包含"stats list must not be empty" |

### 验证点

- FileNotFoundError在文件不存在时正确抛出
- ValueError在无Aggregated行时包含正确消息
- ValueError在CSV格式错误时包含正确消息
- ValueError在count<=0时包含正确消息
- ValueError在mix_ratio越界时包含正确消息
- ValueError在空stats列表时包含正确消息

### 后置检查

- 临时CSV文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_001_query_latency.py::TestLatencyReportAnalyzerErrors (tests D, E, F), TestQueryGenerator (tests K, L), TestAnalyzeFromStats (test N)
- **Test Type**: Real

---

### 用例编号

ST-PERF-026-001

### 关联需求

NFR-001（Query response latency p95 < 1000ms）

### 测试目标

验证完整的CSV文件I/O往返流程：写入Locust CSV → 解析 → 提取指标 → 阈值判定

### 前置条件

- LatencyReportAnalyzer类已实现且可导入
- 临时目录可用于写入CSV文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建包含endpoint行和Aggregated行的完整Locust CSV文件：p95=520ms, p99=700ms, median=180ms, avg=220ms, total_requests=15000, failure_count=30 | CSV文件创建成功 |
| 2 | 调用analyzer.analyze(csv_path, p95_threshold_ms=1000.0) | 返回VerificationResult对象 |
| 3 | 检查result.passed | passed=True（520 <= 1000） |
| 4 | 检查所有指标字段 | p95_ms=520.0, p99_ms=700.0, median_ms=180.0, avg_ms=220.0, total_requests=15000 |
| 5 | 检查failure_rate | failure_rate ≈ 30/15000 = 0.002 |

### 验证点

- 完整CSV往返解析正确
- 所有指标字段精确匹配
- failure_rate计算正确（30/15000）
- 阈值判定正确（passed=True）

### 后置检查

- 临时CSV文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: performance
- **已自动化**: Yes
- **测试引用**: test_nfr_001_query_latency.py::TestRealLatencyReportFeature26::test_real_csv_roundtrip_analyze_feature_26
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-026-001 | NFR-001 | VS-1: p95 < 1000ms under load | test_a_p95_under_threshold_passes | Real | PASS |
| ST-FUNC-026-002 | NFR-001 | VS-1: p95 < 1000ms under load | test_b_p95_over_threshold_fails | Real | PASS |
| ST-FUNC-026-003 | NFR-001 | VS-1: p95 < 1000ms under load | test_m_from_stats_happy_path | Real | PASS |
| ST-FUNC-026-004 | NFR-001 | VS-1: p95 < 1000ms under load | test_h_default_mix_ratio | Real | PASS |
| ST-FUNC-026-005 | NFR-001 | VS-1: p95 < 1000ms under load | test_o_summary_contains_key_info | Real | PASS |
| ST-BNDRY-026-001 | NFR-001 | VS-1: p95 < 1000ms under load | test_c_p95_equals_threshold_passes | Real | PASS |
| ST-BNDRY-026-002 | NFR-001 | VS-1: p95 < 1000ms under load | test_g_zero_requests_no_division_error | Real | PASS |
| ST-BNDRY-026-003 | NFR-001 | VS-1: p95 < 1000ms under load | test_i, test_j | Real | PASS |
| ST-BNDRY-026-004 | NFR-001 | VS-1: p95 < 1000ms under load | tests D, E, F, K, L, N | Real | PASS |
| ST-PERF-026-001 | NFR-001 | VS-1: p95 < 1000ms under load | test_real_csv_roundtrip_analyze_feature_26 | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 10 |
| Passed | 10 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
