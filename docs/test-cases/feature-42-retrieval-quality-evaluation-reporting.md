# 测试用例集: Retrieval Quality Evaluation & Reporting

**Feature ID**: 42
**关联需求**: FR-026
**日期**: 2026-03-22
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 5 |
| boundary | 4 |
| **合计** | **9** |

---

### 用例编号

ST-FUNC-042-001

### 关联需求

FR-026（Retrieval Quality Evaluation & Reporting）

### 测试目标

验证 EvalRunner.evaluate_stage("vector") 针对含有两种语言查询的 golden dataset 正确计算 MRR@10、NDCG@10、Recall@200、Precision@3，并输出 per_language 分组。

### 前置条件

- GoldenDataset 已加载，包含 2 个查询（Python 语言和 Java 语言各一个），每个查询有对应的 Annotation
- Mock Retriever 配置为 vector_code_search 返回已知顺序的 ScoredChunk 列表
- Retriever._qdrant 不为 None

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构造 GoldenDataset：2 个 EvalQuery（language 分别为 "python" 和 "java"），每个有 Annotation 标注 | GoldenDataset 创建成功 |
| 2 | 创建 Mock Retriever，vector_code_search 返回已知的 chunk 序列，其中已知 chunk 的 relevance ≥ 2 | Mock 配置成功 |
| 3 | 创建 EvalRunner(retriever, golden) | 初始化成功，_relevant_map 和 _relevance_scores_map 构建完成 |
| 4 | 调用 await evaluate_stage("vector") | 返回 StageMetrics，status="OK" |
| 5 | 检查返回的 StageMetrics.mrr_at_10、ndcg_at_10、recall_at_200、precision_at_3 | 所有指标均为非 None 的 float 值，与手算结果一致 |
| 6 | 检查 StageMetrics.per_language | 包含 "python" 和 "java" 两个键，每个键下有独立的指标均值 |
| 7 | 检查 StageMetrics.query_count | 等于 2 |

### 验证点

- StageMetrics.status == "OK"
- 所有 4 个指标均为 float 且与手算值匹配
- per_language 包含 "python" 和 "java" 两个键
- query_count == 2

### 后置检查

- 无持久化副作用需要清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/eval/test_runner.py::TestEvaluateStageHappyPath::test_t01_vector_stage_computes_metrics, tests/eval/test_runner.py::TestEvaluateStageHappyPath::test_t07_per_language_breakdown
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-042-002

### 关联需求

FR-026（Retrieval Quality Evaluation & Reporting）

### 测试目标

验证当 retrieval stage 尚未实现（如 "rrf"）时，evaluate_stage 返回 StageMetrics 且所有指标为 None、status="N/A"，不抛出异常。

### 前置条件

- GoldenDataset 已加载，包含至少 1 个查询
- Mock Retriever 已初始化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 EvalRunner(retriever, golden) | 初始化成功 |
| 2 | 调用 await evaluate_stage("rrf") | 返回 StageMetrics |
| 3 | 检查 StageMetrics.status | "N/A" |
| 4 | 检查 mrr_at_10、ndcg_at_10、recall_at_200、precision_at_3 | 全部为 None |
| 5 | 调用 await evaluate_stage("reranked") | 返回 StageMetrics，status="N/A"，所有指标为 None |

### 验证点

- status == "N/A"
- 所有 4 个指标均为 None
- 不抛出异常
- per_language 为空 dict

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/eval/test_runner.py::TestEvaluateStageHappyPath::test_t08_unimplemented_stage_returns_na
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-042-003

### 关联需求

FR-026（Retrieval Quality Evaluation & Reporting）

### 测试目标

验证 ReportGenerator.generate() 输出包含 overall scores 表、per-stage breakdown、per-language breakdown 和 weak spots 的 Markdown 报告，并将 N/A stage 正确渲染。

### 前置条件

- 两个 StageMetrics：一个 vector stage（status="OK"，指标有值），一个 rrf stage（status="N/A"，指标全 None）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 StageMetrics(stage="vector", mrr_at_10=0.8, ndcg_at_10=0.75, recall_at_200=0.6, precision_at_3=0.67, per_language={"python": {...}}, query_count=10, status="OK") | 对象创建成功 |
| 2 | 创建 StageMetrics(stage="rrf", mrr_at_10=None, ..., status="N/A") | 对象创建成功 |
| 3 | 调用 ReportGenerator().generate([vector_stage, rrf_stage]) | 返回 Markdown 字符串 |
| 4 | 检查报告包含 "# Retrieval Quality Evaluation Report" | 标题存在 |
| 5 | 检查报告包含 "## Overall Scores" 表格，含 vector 行和 rrf 行 | vector 行有数值，rrf 行显示 N/A |
| 6 | 检查报告包含 "## Per-Language Breakdown" | per-language 部分存在 |
| 7 | 检查报告包含 "## Weak Spots" | weak spots 部分存在 |

### 验证点

- 报告包含标题行和日期
- Overall Scores 表含 vector 行（数值）和 rrf 行（N/A）
- Per-Stage 详情中 rrf 显示 "Stage not yet implemented — N/A."
- Per-Language Breakdown 存在
- Weak Spots 部分存在（列出低于 0.5 的指标或显示 "No weak spots"）

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/eval/test_report.py::TestReportGeneratorHappyPath::test_t09_generate_report_with_na_stage
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-042-004

### 关联需求

FR-026（Retrieval Quality Evaluation & Reporting）

### 测试目标

验证当提供 previous report 时，ReportGenerator.generate() 生成包含 delta section 的报告，delta 值为当前指标与前次指标的有符号差值。

### 前置条件

- 当前 StageMetrics 包含 vector stage，指标已知
- 前次报告为有效的 Markdown 字符串，包含 Overall Scores 表格中 vector 行的数值

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建当前 StageMetrics(stage="vector", mrr_at_10=0.85, ...) | 对象创建成功 |
| 2 | 构造前次报告字符串，含 Overall Scores 表格（vector 行 mrr_at_10=0.80, ...） | 字符串准备完成 |
| 3 | 调用 ReportGenerator().generate([current_stage], prev_report=prev_report_str) | 返回 Markdown 字符串 |
| 4 | 检查报告包含 "## Delta Comparison" | delta 部分存在 |
| 5 | 检查 delta 表中 vector 行的 Δ MRR@10 | 值为 +0.0500（0.85 - 0.80） |

### 验证点

- 报告包含 "## Delta Comparison" 部分
- Delta 表中 vector 行显示正确的有符号差值
- 差值格式为 +/- 小数

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/eval/test_report.py::TestReportGeneratorHappyPath::test_t10_delta_comparison
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-042-005

### 关联需求

FR-026（Retrieval Quality Evaluation & Reporting）

### 测试目标

验证 MRR@10 计算正确性：首个相关结果在 rank 1 时 MRR=1.0，在 rank 5 时 MRR=0.2，不在 top-10 时 MRR=0.0。

### 前置条件

- EvalRunner 已初始化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 compute_mrr(["c1","c2","c3"], relevant={"c1"}, k=10) | 返回 1.0（rank=1） |
| 2 | 调用 compute_mrr(["c1","c2","c3","c4","c5"], relevant={"c5"}, k=10) | 返回 0.2（rank=5） |
| 3 | 调用 compute_mrr(["c1","c2","c3"], relevant={"c99"}, k=10) | 返回 0.0（不在 top-k） |

### 验证点

- rank=1 → MRR=1.0
- rank=5 → MRR=0.2
- 不在 top-k → MRR=0.0

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/eval/test_runner.py::TestEvaluateStageHappyPath::test_t02_mrr_first_rank, tests/eval/test_runner.py::TestEvaluateStageHappyPath::test_t03_mrr_rank_five
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-042-001

### 关联需求

FR-026（Retrieval Quality Evaluation & Reporting）

### 测试目标

验证所有 metric 函数在 k < 1 时抛出 ValueError，在 k=1 时正常工作，在 results 为空列表时返回正确退化值。

### 前置条件

- EvalRunner 已初始化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 compute_mrr(results, relevant, k=0) | ValueError("k must be >= 1") |
| 2 | 调用 compute_ndcg(results, scores, k=-1) | ValueError("k must be >= 1") |
| 3 | 调用 compute_recall(results, relevant, k=0) | ValueError("k must be >= 1") |
| 4 | 调用 compute_precision(results, relevant, k=0) | ValueError("k must be >= 1") |
| 5 | 调用 compute_mrr([], relevant={"c1"}, k=10) | 返回 0.0 |
| 6 | 调用 compute_recall(["c1"], relevant=set(), k=10) | 返回 1.0（vacuously true） |
| 7 | 调用 compute_ndcg(["c1"], relevance_scores={}, k=10) | 返回 0.0（IDCG=0） |

### 验证点

- k=0 → ValueError for all 4 metric functions
- k=-1 → ValueError
- 空 results → MRR 返回 0.0
- 空 relevant set → Recall 返回 1.0
- 空 relevance_scores → NDCG 返回 0.0

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/eval/test_runner.py::TestMetricErrors::test_t12_mrr_k_zero, tests/eval/test_runner.py::TestMetricErrors::test_t13_ndcg_k_negative, tests/eval/test_runner.py::TestMetricErrors::test_t14_recall_k_zero, tests/eval/test_runner.py::TestMetricErrors::test_t15_precision_k_zero, tests/eval/test_runner.py::TestMetricBoundary::test_t19_empty_results, tests/eval/test_runner.py::TestMetricBoundary::test_t21_empty_relevant_recall, tests/eval/test_runner.py::TestMetricBoundary::test_t23_idcg_zero
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-042-002

### 关联需求

FR-026（Retrieval Quality Evaluation & Reporting）

### 测试目标

验证 evaluate_stage 对无效 stage 名称抛出 ValueError，对 Retriever 抛出 RetrievalError 时返回 N/A，对空 golden dataset 在 init 时拒绝。

### 前置条件

- Mock Retriever 已初始化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 evaluate_stage("unknown_stage") | ValueError("Unknown stage: unknown_stage") |
| 2 | 配置 Mock Retriever.vector_code_search 抛出 RetrievalError | Mock 配置成功 |
| 3 | 调用 evaluate_stage("vector") | 返回 StageMetrics(status="N/A") |
| 4 | 创建 EvalRunner(retriever, golden_with_empty_queries) | ValueError("Golden dataset has no queries") |

### 验证点

- 无效 stage → ValueError with stage name in message
- RetrievalError → StageMetrics(status="N/A")
- 空 golden → ValueError

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/eval/test_runner.py::TestEvaluateStageErrors::test_t11_unknown_stage, tests/eval/test_runner.py::TestEvaluateStageErrors::test_t18_retrieval_error_returns_na, tests/eval/test_runner.py::TestEvalRunnerInit::test_t16_empty_golden_raises
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-042-003

### 关联需求

FR-026（Retrieval Quality Evaluation & Reporting）

### 测试目标

验证 ReportGenerator.generate() 对空 stages 列表抛出 ValueError，对空字符串 prev_report 输出 "No comparable metrics found"，对全 N/A stages 正常渲染。

### 前置条件

- ReportGenerator 已初始化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 generate(stages=[]) | ValueError("At least one stage required") |
| 2 | 调用 generate([na_stage], prev_report="") | 报告生成成功，含 "No comparable metrics found" |
| 3 | 创建全部 N/A 的 StageMetrics，调用 generate([na_stage]) | 有效 Markdown 报告，N/A 行渲染正确，无崩溃 |

### 验证点

- 空 stages → ValueError
- prev_report="" → delta section 显示 "No comparable metrics found"
- 全 N/A stages → 报告正常生成

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/eval/test_report.py::TestReportGeneratorErrors::test_t17_empty_stages_raises, tests/eval/test_report.py::TestReportGeneratorBoundary::test_t25_empty_prev_report, tests/eval/test_report.py::TestReportGeneratorBoundary::test_t27_all_na_stages
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-042-004

### 关联需求

FR-026（Retrieval Quality Evaluation & Reporting）

### 测试目标

验证 Precision@k 在 results 数量少于 k 时使用 k 作为分母（非 len(results)），以及单个查询 golden dataset 的 evaluate_stage 指标等于该查询的单独计算结果。

### 前置条件

- EvalRunner 已初始化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 compute_precision(["c1"], relevant={"c1"}, k=3) | 返回 1/3（分母是 k=3，不是 len(results)=1） |
| 2 | 调用 compute_mrr(["c1","c2"], relevant={"c2"}, k=1) | 返回 0.0（c2 在 rank 2，超出 k=1） |
| 3 | 用单个查询 golden dataset 调用 evaluate_stage("bm25") | 返回的指标等于该查询的单独计算结果（无平均失真） |

### 验证点

- Precision 分母始终为 k
- k=1 时只考虑第一个结果
- 单查询 golden → 指标无平均失真

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/eval/test_runner.py::TestMetricBoundary::test_t26_precision_results_shorter_than_k, tests/eval/test_runner.py::TestMetricBoundary::test_t22_k_equals_one, tests/eval/test_runner.py::TestMetricBoundary::test_t24_single_query_golden
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-042-001 | FR-026 | VS[0]: Given a golden dataset and vector_code_search available, when EvalRunner.evaluate_stage("vector") runs, then MRR@10, NDCG@10, Recall@200, and Precision@3 are computed correctly | test_t01, test_t07 | Mock | PASS |
| ST-FUNC-042-002 | FR-026 | VS[1]: Given a retrieval stage not yet implemented, when EvalRunner.evaluate_stage() runs for that stage, then it returns N/A metrics without error | test_t08 | Mock | PASS |
| ST-FUNC-042-003 | FR-026 | VS[2]: Given evaluation results, when ReportGenerator.generate() runs, then a Markdown report is saved with per-language and per-stage breakdowns | test_t09 | Mock | PASS |
| ST-FUNC-042-004 | FR-026 | VS[3]: Given a previous report exists, when a new evaluation runs, then the report includes a delta section comparing metrics | test_t10 | Mock | PASS |
| ST-FUNC-042-005 | FR-026 | VS[0]: MRR@10 metric correctness at different ranks | test_t02, test_t03 | Mock | PASS |
| ST-BNDRY-042-001 | FR-026 | VS[0]: k boundary validation and empty input degeneracy for all metric functions | test_t12-t15, test_t19, test_t21, test_t23 | Mock | PASS |
| ST-BNDRY-042-002 | FR-026 | VS[1]: Invalid stage, RetrievalError handling, empty golden dataset rejection | test_t11, test_t18, test_t16 | Mock | PASS |
| ST-BNDRY-042-003 | FR-026 | VS[2]: Empty stages, empty prev_report, all-N/A stages for ReportGenerator | test_t17, test_t25, test_t27 | Mock | PASS |
| ST-BNDRY-042-004 | FR-026 | VS[0]: Precision denominator with short results, k=1 truncation, single-query golden | test_t26, test_t22, test_t24 | Mock | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 0 |
| Passed | 0 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> All test cases for this feature are Mock-based since the feature performs IR metric computation and report generation using in-memory data structures. The unit tests mock the Retriever to verify all logic paths without requiring running Elasticsearch/Qdrant services.
