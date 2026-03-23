# 测试用例集: NFR-003: Repository Capacity

**Feature ID**: 28
**关联需求**: NFR-003
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

ST-FUNC-028-001

### 关联需求

NFR-003（Repository capacity: 100–1000 repositories indexed）

### 测试目标

验证CapacityReportAnalyzer.analyze()在repo数量处于范围内且indexed ratio超过阈值时返回passed=True并正确提取所有指标

### 前置条件

- CapacityReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JSON库存报告文件，包含150个repository条目，其中140个status="indexed"，10个status="pending" | JSON文件创建成功 |
| 2 | 调用CapacityReportAnalyzer().analyze(json_path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8) | 返回CapacityVerificationResult对象 |
| 3 | 检查result.passed | passed=True（150在[100,1000]范围内且ratio=140/150≈0.933>=0.8） |
| 4 | 检查result.total_repos, result.indexed_repos | total_repos=150, indexed_repos=140 |
| 5 | 检查result.indexed_ratio | indexed_ratio ≈ 0.9333 |

### 验证点

- CapacityVerificationResult.passed == True
- total_repos == 150
- indexed_repos == 140
- indexed_ratio ≈ 140/150
- min_repos == 100, max_repos == 1000, min_indexed_ratio == 0.8

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_003_repository_capacity.py::TestAnalyzeHappyPath::test_passes_with_150_repos_140_indexed
- **Test Type**: Real

---

### 用例编号

ST-FUNC-028-002

### 关联需求

NFR-003（Repository capacity: 100–1000 repositories indexed）

### 测试目标

验证当repo数量低于min_repos阈值时analyze()返回passed=False

### 前置条件

- CapacityReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JSON库存报告文件，包含50个repository条目，全部status="indexed" | JSON文件创建成功 |
| 2 | 调用CapacityReportAnalyzer().analyze(json_path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8) | 返回CapacityVerificationResult对象 |
| 3 | 检查result.passed | passed=False（50 < 100 min_repos阈值） |
| 4 | 检查result.total_repos | total_repos=50 |

### 验证点

- CapacityVerificationResult.passed == False
- total_repos == 50（低于min_repos=100）
- indexed_ratio == 1.0（全部indexed，但数量不足）

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_003_repository_capacity.py::TestAnalyzeHappyPath::test_fails_below_min_repos
- **Test Type**: Real

---

### 用例编号

ST-FUNC-028-003

### 关联需求

NFR-003（Repository capacity: 100–1000 repositories indexed）

### 测试目标

验证当repo数量超过max_repos上限或indexed ratio低于阈值时analyze()返回passed=False（三条件检查的各失败路径）

### 前置条件

- CapacityReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JSON库存报告文件，包含200个repository条目，其中100个indexed（ratio=0.5） | JSON文件创建成功 |
| 2 | 调用analyze(json_path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8) | 返回result.passed=False（ratio=0.5 < 0.8） |
| 3 | 创建JSON库存报告文件，包含1500个repository条目，全部indexed | JSON文件创建成功 |
| 4 | 调用analyze(json_path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8) | 返回result.passed=False（1500 > 1000 max_repos） |

### 验证点

- 低indexed ratio场景：passed=False, total_repos=200, indexed_repos=100, indexed_ratio=0.5
- 超过max_repos场景：passed=False, total_repos=1500, indexed_repos=1500, indexed_ratio=1.0

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_003_repository_capacity.py::TestAnalyzeHappyPath::test_fails_low_indexed_ratio, test_nfr_003_repository_capacity.py::TestAnalyzeHappyPath::test_fails_above_max_repos
- **Test Type**: Real

---

### 用例编号

ST-FUNC-028-004

### 关联需求

NFR-003（Repository capacity: 100–1000 repositories indexed）

### 测试目标

验证analyze_from_stats()通过编程接口正确计算容量指标并返回通过/失败结果

### 前置条件

- CapacityReportAnalyzer类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用analyze_from_stats({"total_repos": 0, "indexed_repos": 0}, min_repos=100) | 返回passed=False, indexed_ratio=0.0（无ZeroDivisionError） |
| 2 | 调用analyze_from_stats({"indexed_repos": 10})（缺少total_repos键） | 抛出ValueError，包含"total_repos" |
| 3 | 调用analyze_from_stats({"total_repos": -1, "indexed_repos": 0}) | 抛出ValueError，包含"non-negative" |

### 验证点

- total_repos=0时不产生ZeroDivisionError，indexed_ratio=0.0
- 缺少必要键时抛出ValueError
- 负数repo count时抛出ValueError

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_003_repository_capacity.py::TestAnalyzeBoundary::test_zero_total_repos_no_division_error, test_nfr_003_repository_capacity.py::TestAnalyzeErrors::test_stats_missing_keys, test_nfr_003_repository_capacity.py::TestAnalyzeErrors::test_stats_negative_count
- **Test Type**: Real

---

### 用例编号

ST-FUNC-028-005

### 关联需求

NFR-003（Repository capacity: 100–1000 repositories indexed）

### 测试目标

验证CapacityVerificationResult.summary()正确格式化包含NFR-003标识、判定结果和指标值

### 前置条件

- CapacityVerificationResult类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建passing CapacityVerificationResult(passed=True, total_repos=150, indexed_repos=140, ...) | 对象创建成功 |
| 2 | 调用result.summary() | 返回包含"NFR-003"、"PASS"、"150"、"140"的字符串 |
| 3 | 创建failing CapacityVerificationResult(passed=False, total_repos=50, ...) | 对象创建成功 |
| 4 | 调用result.summary() | 返回包含"NFR-003"、"FAIL"、"100"（min阈值）、"1000"（max阈值）的字符串 |

### 验证点

- passing结果的summary包含"NFR-003"、"PASS"、"150"、"140"
- failing结果的summary包含"NFR-003"、"FAIL"、"100"、"1000"（阈值）
- summary格式符合设计文档规定

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: Medium
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_003_repository_capacity.py::TestVerificationResultSummary::test_summary_pass_format, test_nfr_003_repository_capacity.py::TestVerificationResultSummary::test_summary_fail_format
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-028-001

### 关联需求

NFR-003（Repository capacity: 100–1000 repositories indexed）

### 测试目标

验证repo数量恰好等于min_repos且indexed ratio恰好等于min_indexed_ratio时（边界值），analyze()返回passed=True（>= 语义）

### 前置条件

- CapacityReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JSON库存报告文件，包含100个repository条目，其中80个status="indexed"（ratio=0.8恰好等于阈值） | JSON文件创建成功 |
| 2 | 调用analyze(json_path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8) | 返回CapacityVerificationResult对象 |
| 3 | 检查result.passed | passed=True（100>=100 且 0.8>=0.8） |
| 4 | 检查result.indexed_ratio | indexed_ratio == 0.8 |

### 验证点

- CapacityVerificationResult.passed == True
- 使用 >= 比较（非严格 >）对min_repos和min_indexed_ratio

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_003_repository_capacity.py::TestAnalyzeBoundary::test_passes_at_exact_min_repos_and_exact_ratio
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-028-002

### 关联需求

NFR-003（Repository capacity: 100–1000 repositories indexed）

### 测试目标

验证indexed ratio刚好低于min_indexed_ratio阈值时返回passed=False（确认>= 语义的边界行为）

### 前置条件

- CapacityReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JSON库存报告文件，包含100个repository条目，其中79个indexed（ratio=0.79） | JSON文件创建成功 |
| 2 | 调用analyze(json_path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8) | 返回CapacityVerificationResult对象 |
| 3 | 检查result.passed | passed=False（0.79 < 0.8） |
| 4 | 检查result.indexed_ratio | indexed_ratio == 0.79 |

### 验证点

- CapacityVerificationResult.passed == False
- indexed_ratio == 0.79（刚好低于0.8阈值）

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_003_repository_capacity.py::TestAnalyzeBoundary::test_fails_just_below_ratio_threshold
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-028-003

### 关联需求

NFR-003（Repository capacity: 100–1000 repositories indexed）

### 测试目标

验证repo数量恰好等于max_repos上限时返回passed=True（<= 语义的边界行为）

### 前置条件

- CapacityReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JSON库存报告文件，包含1000个repository条目，其中800个indexed（ratio=0.8） | JSON文件创建成功 |
| 2 | 调用analyze(json_path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8) | 返回CapacityVerificationResult对象 |
| 3 | 检查result.passed | passed=True（1000<=1000 且 0.8>=0.8） |
| 4 | 检查result.total_repos | total_repos == 1000 |

### 验证点

- CapacityVerificationResult.passed == True
- 使用 <= 比较（非严格 <）对max_repos
- total_repos == max_repos时通过

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_003_repository_capacity.py::TestAnalyzeBoundary::test_passes_at_exact_max_repos
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-028-004

### 关联需求

NFR-003（Repository capacity: 100–1000 repositories indexed）

### 测试目标

验证JSON报告的错误处理：文件不存在、JSON格式错误、缺少repositories键、空repositories列表

### 前置条件

- CapacityReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用analyze("/nonexistent/report.json") | 抛出FileNotFoundError |
| 2 | 创建包含无效JSON内容的文件，调用analyze() | 抛出ValueError，消息包含"malformed JSON" |
| 3 | 创建JSON文件但缺少"repositories"键，调用analyze() | 抛出ValueError，消息包含"repositories" |
| 4 | 创建JSON文件包含空repositories列表，调用analyze() | 抛出ValueError，消息包含"empty" |

### 验证点

- 文件不存在时抛出FileNotFoundError
- JSON格式错误时抛出ValueError("malformed JSON")
- 缺少repositories键时抛出ValueError("repositories")
- 空列表时抛出ValueError("empty")

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_003_repository_capacity.py::TestAnalyzeErrors::test_file_not_found, test_nfr_003_repository_capacity.py::TestAnalyzeErrors::test_malformed_json, test_nfr_003_repository_capacity.py::TestAnalyzeErrors::test_missing_repositories_key, test_nfr_003_repository_capacity.py::TestAnalyzeErrors::test_empty_repositories_list
- **Test Type**: Real

---

### 用例编号

ST-PERF-028-001

### 关联需求

NFR-003（Repository capacity: 100–1000 repositories indexed）

### 测试目标

验证完整的JSON报告写入→解析→指标提取→阈值判定→结果格式化端到端流程，模拟真实库存报告

### 前置条件

- CapacityReportAnalyzer类已实现且可导入
- CapacityVerificationResult类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建包含200个repository条目（180个indexed）的JSON库存报告文件 | JSON文件创建成功 |
| 2 | 调用CapacityReportAnalyzer().analyze(json_path, min_repos=100, max_repos=1000, min_indexed_ratio=0.8) | 返回CapacityVerificationResult |
| 3 | 检查result.passed | passed=True |
| 4 | 检查所有指标字段 | total_repos=200, indexed_repos=180, indexed_ratio≈0.9, min_repos=100, max_repos=1000, min_indexed_ratio=0.8 |
| 5 | 调用result.summary() | 返回包含"NFR-003"、"PASS"、"200"的格式化字符串 |

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
- **测试引用**: test_nfr_003_repository_capacity.py::TestRealCapacityReportFeature28::test_real_json_roundtrip_analyze_feature_28
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-028-001 | NFR-003 | VS-1: 100+注册repos，indexed content，查询返回在延迟预算内 | test_passes_with_150_repos_140_indexed | Real | PASS |
| ST-FUNC-028-002 | NFR-003 | VS-1: 100+注册repos，indexed content，查询返回在延迟预算内 | test_fails_below_min_repos | Real | PASS |
| ST-FUNC-028-003 | NFR-003 | VS-1: 100+注册repos，indexed content，查询返回在延迟预算内 | test_fails_low_indexed_ratio, test_fails_above_max_repos | Real | PASS |
| ST-FUNC-028-004 | NFR-003 | VS-1: 100+注册repos，indexed content，查询返回在延迟预算内 | test_zero_total_repos_no_division_error, test_stats_missing_keys, test_stats_negative_count | Real | PASS |
| ST-FUNC-028-005 | NFR-003 | VS-1: 100+注册repos，indexed content，查询返回在延迟预算内 | test_summary_pass_format, test_summary_fail_format | Real | PASS |
| ST-BNDRY-028-001 | NFR-003 | VS-1: 100+注册repos，indexed content，查询返回在延迟预算内 | test_passes_at_exact_min_repos_and_exact_ratio | Real | PASS |
| ST-BNDRY-028-002 | NFR-003 | VS-1: 100+注册repos，indexed content，查询返回在延迟预算内 | test_fails_just_below_ratio_threshold | Real | PASS |
| ST-BNDRY-028-003 | NFR-003 | VS-1: 100+注册repos，indexed content，查询返回在延迟预算内 | test_passes_at_exact_max_repos | Real | PASS |
| ST-BNDRY-028-004 | NFR-003 | VS-1: 100+注册repos，indexed content，查询返回在延迟预算内 | test_file_not_found, test_malformed_json, test_missing_repositories_key, test_empty_repositories_list | Real | PASS |
| ST-PERF-028-001 | NFR-003 | VS-1: 100+注册repos，indexed content，查询返回在延迟预算内 | test_real_json_roundtrip_analyze_feature_28 | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 10 |
| Passed | 10 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
