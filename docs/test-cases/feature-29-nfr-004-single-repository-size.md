# 测试用例集: NFR-004: Single Repository Size

**Feature ID**: 29
**关联需求**: NFR-004
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

ST-FUNC-029-001

### 关联需求

NFR-004（Single Repository Size: <= 1 GB per repository）

### 测试目标

验证RepoSizeReportAnalyzer.analyze()在所有repo的size_bytes均<=1GB且全部status="completed"时返回passed=True，正确提取所有指标

### 前置条件

- RepoSizeReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JSON大小报告文件，包含3个repo条目：size_bytes分别为500MB、800MB、1GB(exactly 1_073_741_824)，全部status="completed" | JSON文件创建成功 |
| 2 | 调用RepoSizeReportAnalyzer().analyze(json_path, max_size_bytes=1_073_741_824) | 返回RepoSizeVerificationResult对象 |
| 3 | 检查result.passed | passed=True（所有repo<=1GB且全部completed） |
| 4 | 检查result.total_repos, result.repos_within_limit, result.repos_completed | total_repos=3, repos_within_limit=3, repos_completed=3 |
| 5 | 检查result.max_observed_bytes | max_observed_bytes=1_073_741_824 |

### 验证点

- RepoSizeVerificationResult.passed == True
- total_repos == 3
- repos_within_limit == 3
- repos_completed == 3
- max_observed_bytes == 1_073_741_824 (1GB)

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_004_single_repository_size.py::TestAnalyzeHappyPath::test_passes_with_three_repos_up_to_1gb
- **Test Type**: Real

---

### 用例编号

ST-FUNC-029-002

### 关联需求

NFR-004（Single Repository Size: <= 1 GB per repository）

### 测试目标

验证当存在超过1GB的repo时analyze()返回passed=False，正确统计oversized repo

### 前置条件

- RepoSizeReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JSON大小报告文件，包含3个repo条目：500MB、1.5GB(over limit)、500MB，全部status="completed" | JSON文件创建成功 |
| 2 | 调用RepoSizeReportAnalyzer().analyze(json_path, max_size_bytes=1_073_741_824) | 返回RepoSizeVerificationResult对象 |
| 3 | 检查result.passed | passed=False（1.5GB repo超出限制） |
| 4 | 检查result.repos_within_limit, result.total_repos | repos_within_limit=2, total_repos=3 |
| 5 | 检查result.max_observed_bytes | max_observed_bytes=1_500_000_000 |

### 验证点

- RepoSizeVerificationResult.passed == False
- repos_within_limit == 2（仅2个repo<=1GB）
- total_repos == 3
- max_observed_bytes == 1_500_000_000

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_004_single_repository_size.py::TestAnalyzeHappyPath::test_fails_with_oversized_repo
- **Test Type**: Real

---

### 用例编号

ST-FUNC-029-003

### 关联需求

NFR-004（Single Repository Size: <= 1 GB per repository）

### 测试目标

验证当repo在size limit内但indexing status为"oom"或"timeout"时（非completed），analyze()返回passed=False

### 前置条件

- RepoSizeReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JSON大小报告文件：3个repo均在1GB内，其中1个status="oom" | JSON文件创建成功 |
| 2 | 调用analyze(json_path, max_size_bytes=ONE_GB) | passed=False, repos_completed=2, completion_ratio≈0.667 |
| 3 | 创建JSON大小报告文件：3个repo均在1GB内，其中1个status="timeout" | JSON文件创建成功 |
| 4 | 调用analyze(json_path, max_size_bytes=ONE_GB) | passed=False, repos_completed=2, completion_ratio≈0.667 |

### 验证点

- OOM场景：passed=False, repos_completed=2, completion_ratio≈2/3
- Timeout场景：passed=False, repos_completed=2, completion_ratio≈2/3
- 非"completed"的任何status都视为indexing失败

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_004_single_repository_size.py::TestAnalyzeHappyPath::test_fails_with_oom_status, test_nfr_004_single_repository_size.py::TestAnalyzeHappyPath::test_fails_with_timeout_status
- **Test Type**: Real

---

### 用例编号

ST-FUNC-029-004

### 关联需求

NFR-004（Single Repository Size: <= 1 GB per repository）

### 测试目标

验证analyze_from_stats()通过编程接口正确计算repo大小指标并返回通过/失败结果，以及错误处理

### 前置条件

- RepoSizeReportAnalyzer类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用analyze_from_stats({"total_repos":1, "repos_within_limit":0, "repos_completed":0, "max_observed_bytes":2_000_000_000}) | passed=False, completion_ratio=0.0（无ZeroDivisionError） |
| 2 | 调用analyze_from_stats({"total_repos":3, "repos_within_limit":3, "repos_completed":3, "max_observed_bytes":ONE_GB}) | passed=True, completion_ratio=1.0 |
| 3 | 调用analyze_from_stats({"repos_completed": 10})（缺少total_repos等键） | 抛出ValueError，包含"total_repos" |
| 4 | 调用analyze_from_stats({"total_repos":-1, "repos_within_limit":0, "repos_completed":0, "max_observed_bytes":0}) | 抛出ValueError，包含"non-negative" |

### 验证点

- repos_within_limit=0时不产生ZeroDivisionError，completion_ratio=0.0
- 完整stats通过时passed=True
- 缺少必要键时抛出ValueError
- 负数值时抛出ValueError

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_004_single_repository_size.py::TestAnalyzeBoundary::test_zero_repos_within_limit_no_division_error, test_nfr_004_single_repository_size.py::TestAnalyzeBoundary::test_stats_with_repos_within_limit_positive, test_nfr_004_single_repository_size.py::TestAnalyzeErrors::test_stats_missing_keys, test_nfr_004_single_repository_size.py::TestAnalyzeErrors::test_stats_negative_value
- **Test Type**: Real

---

### 用例编号

ST-FUNC-029-005

### 关联需求

NFR-004（Single Repository Size: <= 1 GB per repository）

### 测试目标

验证RepoSizeVerificationResult.summary()正确格式化包含NFR-004标识、判定结果和指标值

### 前置条件

- RepoSizeVerificationResult类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建passing RepoSizeVerificationResult(passed=True, total_repos=3, repos_within_limit=3, repos_completed=3, max_observed_bytes=ONE_GB, ...) | 对象创建成功 |
| 2 | 调用result.summary() | 返回包含"NFR-004"、"PASS"、"3"、str(ONE_GB)的字符串 |
| 3 | 创建failing RepoSizeVerificationResult(passed=False, repos_within_limit=2, max_observed_bytes=1_500_000_000, ...) | 对象创建成功 |
| 4 | 调用result.summary() | 返回包含"NFR-004"、"FAIL"、str(ONE_GB)的字符串 |

### 验证点

- passing结果的summary包含"NFR-004"、"PASS"、repo count、max observed size
- failing结果的summary包含"NFR-004"、"FAIL"、threshold值
- summary格式符合设计文档规定

### 后置检查

- 无需清理（纯内存操作）

### 元数据

- **优先级**: Medium
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_nfr_004_single_repository_size.py::TestVerificationResultSummary::test_summary_pass_format, test_nfr_004_single_repository_size.py::TestVerificationResultSummary::test_summary_fail_format
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-029-001

### 关联需求

NFR-004（Single Repository Size: <= 1 GB per repository）

### 测试目标

验证repo的size_bytes恰好等于max_size_bytes(1GB)时返回passed=True（确认使用<= 语义，非严格<）

### 前置条件

- RepoSizeReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JSON大小报告文件，包含1个repo：size_bytes=1_073_741_824（恰好1GB），status="completed" | JSON文件创建成功 |
| 2 | 调用analyze(json_path, max_size_bytes=1_073_741_824) | 返回RepoSizeVerificationResult对象 |
| 3 | 检查result.passed | passed=True（size == max_size_bytes，使用<=） |
| 4 | 检查result.repos_within_limit | repos_within_limit=1 |

### 验证点

- RepoSizeVerificationResult.passed == True
- 使用 <= 比较（非严格 <）对max_size_bytes
- size_bytes == max_size_bytes时repo被计入within_limit

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_004_single_repository_size.py::TestAnalyzeBoundary::test_passes_at_exact_size_limit
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-029-002

### 关联需求

NFR-004（Single Repository Size: <= 1 GB per repository）

### 测试目标

验证repo的size_bytes超出max_size_bytes 1个字节时返回passed=False（边界off-by-one检查）

### 前置条件

- RepoSizeReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JSON大小报告文件，包含1个repo：size_bytes=1_073_741_825（1GB+1字节），status="completed" | JSON文件创建成功 |
| 2 | 调用analyze(json_path, max_size_bytes=1_073_741_824) | 返回RepoSizeVerificationResult对象 |
| 3 | 检查result.passed | passed=False（size > max_size_bytes） |
| 4 | 检查result.repos_within_limit | repos_within_limit=0 |

### 验证点

- RepoSizeVerificationResult.passed == False
- repos_within_limit == 0（1字节超出即不计入）
- 边界值1GB+1字节被正确拒绝

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_004_single_repository_size.py::TestAnalyzeBoundary::test_fails_one_byte_over_limit
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-029-003

### 关联需求

NFR-004（Single Repository Size: <= 1 GB per repository）

### 测试目标

验证completion_ratio恰好等于min_completion_ratio阈值时返回passed=True（确认使用>= 语义）

### 前置条件

- RepoSizeReportAnalyzer类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JSON大小报告文件，包含2个repo均在1GB内：1个completed、1个error | JSON文件创建成功 |
| 2 | 调用analyze(json_path, max_size_bytes=ONE_GB, min_completion_ratio=0.5) | 返回RepoSizeVerificationResult对象 |
| 3 | 检查result.passed | passed=True（completion_ratio=0.5 == min_completion_ratio=0.5，使用>=） |
| 4 | 检查result.completion_ratio | completion_ratio == 0.5 |

### 验证点

- RepoSizeVerificationResult.passed == True
- 使用 >= 比较（非严格 >）对min_completion_ratio
- completion_ratio == min_completion_ratio时通过

### 后置检查

- 临时JSON文件由pytest tmp_path fixture自动清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_nfr_004_single_repository_size.py::TestAnalyzeBoundary::test_passes_at_exact_completion_ratio_threshold
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-029-004

### 关联需求

NFR-004（Single Repository Size: <= 1 GB per repository）

### 测试目标

验证JSON报告的错误处理：文件不存在、JSON格式错误、缺少repositories键、空repositories列表

### 前置条件

- RepoSizeReportAnalyzer类已实现且可导入
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
- **测试引用**: test_nfr_004_single_repository_size.py::TestAnalyzeErrors::test_file_not_found, test_nfr_004_single_repository_size.py::TestAnalyzeErrors::test_malformed_json, test_nfr_004_single_repository_size.py::TestAnalyzeErrors::test_missing_repositories_key, test_nfr_004_single_repository_size.py::TestAnalyzeErrors::test_empty_repositories_list
- **Test Type**: Real

---

### 用例编号

ST-PERF-029-001

### 关联需求

NFR-004（Single Repository Size: <= 1 GB per repository）

### 测试目标

验证完整的JSON报告写入→解析→大小指标提取→阈值判定→结果格式化端到端流程，模拟真实repo大小报告

### 前置条件

- RepoSizeReportAnalyzer类已实现且可导入
- RepoSizeVerificationResult类已实现且可导入
- 临时目录可用于写入JSON文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建包含3个repo条目（500MB、1GB、800MB，全部completed）的JSON大小报告文件 | JSON文件创建成功 |
| 2 | 调用RepoSizeReportAnalyzer().analyze(json_path, max_size_bytes=ONE_GB) | 返回RepoSizeVerificationResult |
| 3 | 检查result.passed | passed=True |
| 4 | 检查所有指标字段 | total_repos=3, repos_within_limit=3, repos_completed=3, max_observed_bytes=ONE_GB, max_size_bytes=ONE_GB, min_completion_ratio=1.0, completion_ratio=1.0 |
| 5 | 调用result.summary()确认输出格式 | 返回包含"NFR-004"的格式化字符串 |

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
- **测试引用**: test_nfr_004_single_repository_size.py::TestRealRepoSizeReportFeature29::test_real_json_roundtrip_analyze_feature_29
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-029-001 | NFR-004 | VS-1: repo approaching 1GB, indexing runs, all files processed without OOM/timeout | test_passes_with_three_repos_up_to_1gb | Real | PASS |
| ST-FUNC-029-002 | NFR-004 | VS-1: repo approaching 1GB, indexing runs, all files processed without OOM/timeout | test_fails_with_oversized_repo | Real | PASS |
| ST-FUNC-029-003 | NFR-004 | VS-1: repo approaching 1GB, indexing runs, all files processed without OOM/timeout | test_fails_with_oom_status, test_fails_with_timeout_status | Real | PASS |
| ST-FUNC-029-004 | NFR-004 | VS-1: repo approaching 1GB, indexing runs, all files processed without OOM/timeout | test_zero_repos_within_limit_no_division_error, test_stats_with_repos_within_limit_positive, test_stats_missing_keys, test_stats_negative_value | Real | PASS |
| ST-FUNC-029-005 | NFR-004 | VS-1: repo approaching 1GB, indexing runs, all files processed without OOM/timeout | test_summary_pass_format, test_summary_fail_format | Real | PASS |
| ST-BNDRY-029-001 | NFR-004 | VS-1: repo approaching 1GB, indexing runs, all files processed without OOM/timeout | test_passes_at_exact_size_limit | Real | PASS |
| ST-BNDRY-029-002 | NFR-004 | VS-1: repo approaching 1GB, indexing runs, all files processed without OOM/timeout | test_fails_one_byte_over_limit | Real | PASS |
| ST-BNDRY-029-003 | NFR-004 | VS-1: repo approaching 1GB, indexing runs, all files processed without OOM/timeout | test_passes_at_exact_completion_ratio_threshold | Real | PASS |
| ST-BNDRY-029-004 | NFR-004 | VS-1: repo approaching 1GB, indexing runs, all files processed without OOM/timeout | test_file_not_found, test_malformed_json, test_missing_repositories_key, test_empty_repositories_list | Real | PASS |
| ST-PERF-029-001 | NFR-004 | VS-1: repo approaching 1GB, indexing runs, all files processed without OOM/timeout | test_real_json_roundtrip_analyze_feature_29 | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 10 |
| Passed | 10 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
