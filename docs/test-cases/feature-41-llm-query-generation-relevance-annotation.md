# 测试用例集: LLM Query Generation & Relevance Annotation

**Feature ID**: 41
**关联需求**: FR-025
**日期**: 2026-03-22
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 5 |
| boundary | 4 |
| security | 2 |
| **合计** | **11** |

---

### 用例编号

ST-FUNC-041-001

### 关联需求

FR-025（LLM Query Generation & Relevance Annotation）

### 测试目标

验证 generate_queries 在 MiniMax 提供者下生成 50-100 个查询，覆盖 4 个类别，并包含正确的 repo_id、language 和 category 字段。

### 前置条件

- MINIMAX_API_KEY 环境变量已设置
- OpenAI 兼容客户端已使用 MiniMax 端点初始化
- 已有一个有效的 EvalRepo 对象和已索引的代码块

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 设置 EVAL_LLM_PROVIDER=minimax 及相关环境变量 | 环境变量已就绪 |
| 2 | 创建 LLMAnnotator(provider="minimax") | 实例初始化成功，内部 client 指向 MiniMax 端点 |
| 3 | 调用 generate_queries(repo, chunk_count=200, n_queries=75)，其中 LLM 返回包含 75 个查询的 JSON | 返回 list[EvalQuery] 长度为 75 |
| 4 | 检查返回的每个 EvalQuery 的字段 | 每个查询的 repo_id 等于 repo.name，language 等于 repo.language，text 非空 |
| 5 | 统计返回查询的 category 分布 | 包含 api_usage、bug_diagnosis、configuration、architecture 四个类别 |

### 验证点

- 返回列表长度在 [50, 100] 范围内
- 所有 4 个类别均有查询
- 每个 EvalQuery.text 非空字符串
- 每个 EvalQuery.repo_id 与输入 repo 匹配
- 每个 EvalQuery.category 属于 {"api_usage", "bug_diagnosis", "configuration", "architecture"}

### 后置检查

- 无持久化副作用需要清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/eval/test_annotator.py::TestGenerateQueriesHappyPath::test_t01_generates_75_queries_across_categories
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-041-002

### 关联需求

FR-025（LLM Query Generation & Relevance Annotation）

### 测试目标

验证 dual annotation 在两个评分一致（差值 ≤ 1）时返回两者均值（四舍五入），annotator_run=2。

### 前置条件

- LLMAnnotator 已初始化
- 有效的 EvalQuery 和 ScoredChunk 对象

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 EvalQuery 和含 1 个 chunk 的列表 | 对象创建成功 |
| 2 | Mock LLM 返回两次 "2"（temp=0.1 和 temp=0.3） | Mock 配置成功 |
| 3 | 调用 annotate_relevance(query, [chunk]) | 返回 list[Annotation]，长度为 1 |
| 4 | 检查 Annotation.score | score = 2（round((2+2)/2)） |
| 5 | 检查 Annotation.annotator_run | annotator_run = 2（无第三次调用） |

### 验证点

- 返回恰好 1 个 Annotation
- Annotation.score == 2
- Annotation.annotator_run == 2
- Annotation.chunk_id 与输入 chunk 的 chunk_id 匹配

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/eval/test_annotator.py::TestAnnotateRelevanceHappyPath::test_t02_dual_annotate_agreement
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-041-003

### 关联需求

FR-025（LLM Query Generation & Relevance Annotation）

### 测试目标

验证当 dual annotation 评分差异 >1 时触发第三次 LLM 调用，通过 majority vote 决定最终分数，annotator_run=3。

### 前置条件

- LLMAnnotator 已初始化
- 有效的 EvalQuery 和 ScoredChunk 对象

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 EvalQuery 和含 1 个 chunk 的列表 | 对象创建成功 |
| 2 | Mock LLM 三次调用依次返回 "0"、"3"、"0"（差值=3 >1，触发 tiebreaker） | Mock 配置成功 |
| 3 | 调用 annotate_relevance(query, [chunk]) | 返回 list[Annotation]，长度为 1 |
| 4 | 检查 Annotation.score | score = 0（majority vote: 两个 0 vs 一个 3） |
| 5 | 检查 Annotation.annotator_run | annotator_run = 3（触发了第三次调用） |

### 验证点

- LLM client 被调用恰好 3 次
- Annotation.score == 0（majority vote 结果）
- Annotation.annotator_run == 3

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/eval/test_annotator.py::TestAnnotateRelevanceHappyPath::test_t03_disagreement_triggers_tiebreaker
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-041-004

### 关联需求

FR-025（LLM Query Generation & Relevance Annotation）

### 测试目标

验证 Cohen's Kappa 在混合一致/不一致标注对上正确计算，返回值在 [-1, 1] 范围内。

### 前置条件

- LLMAnnotator 已初始化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构造 10 对标注分数：7 对一致，3 对不一致 | 数据准备完成 |
| 2 | 调用 _compute_kappa(pairs) | 返回 float 值 |
| 3 | 检查返回值范围 | -1.0 ≤ kappa ≤ 1.0 |
| 4 | 检查返回值大小 | kappa > 0.3（至少 fair agreement） |

### 验证点

- 返回值为 float 类型
- 返回值在 [-1.0, 1.0] 范围内
- 7/10 一致率下 kappa 显著大于 0

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/eval/test_annotator.py::TestComputeKappa::test_t04_kappa_with_mixed_agreement
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-041-005

### 关联需求

FR-025（LLM Query Generation & Relevance Annotation）

### 测试目标

验证 Zhipu 提供者使用正确的 API 端点、密钥和模型，与 MiniMax 产生相同格式的输出。

### 前置条件

- ZHIPU_API_KEY、ZHIPU_BASE_URL、ZHIPU_MODEL 环境变量已设置
- EVAL_LLM_PROVIDER=zhipu

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 设置 EVAL_LLM_PROVIDER=zhipu 及 Zhipu 环境变量 | 环境变量已就绪 |
| 2 | 创建 LLMAnnotator(provider="zhipu") | 实例初始化成功 |
| 3 | 检查 annotator._base_url | 等于 Zhipu base URL |
| 4 | 检查 annotator._model | 等于 "glm-4" |

### 验证点

- _base_url 指向 Zhipu API 端点
- _model 等于配置的 Zhipu 模型
- OpenAI client 使用 Zhipu 的 api_key 初始化

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/eval/test_annotator.py::TestProviderConfig::test_t07_zhipu_provider_config
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-041-001

### 关联需求

FR-025（LLM Query Generation & Relevance Annotation）

### 测试目标

验证 n_queries=50（下界）被接受，n_queries=49 被拒绝。

### 前置条件

- LLMAnnotator 已初始化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 generate_queries(repo, chunk_count=200, n_queries=50)，LLM 返回 50 条 | 返回 50 个 EvalQuery |
| 2 | 调用 generate_queries(repo, chunk_count=200, n_queries=49) | 抛出 ValueError("n_queries must be between 50 and 100") |
| 3 | 调用 generate_queries(repo, chunk_count=200, n_queries=100)，LLM 返回 100 条 | 返回 100 个 EvalQuery |
| 4 | 调用 generate_queries(repo, chunk_count=200, n_queries=101) | 抛出 ValueError("n_queries must be between 50 and 100") |

### 验证点

- n_queries=50 → 成功返回 50 个查询
- n_queries=49 → ValueError
- n_queries=100 → 成功返回 100 个查询
- n_queries=101 → ValueError

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/eval/test_annotator.py::TestGenerateQueriesBoundary::test_t21_minimum_n_queries_50, tests/eval/test_annotator.py::TestGenerateQueriesErrors::test_t08_n_queries_below_50_raises, tests/eval/test_annotator.py::TestGenerateQueriesBoundary::test_t22_maximum_n_queries_100, tests/eval/test_annotator.py::TestGenerateQueriesErrors::test_t09_n_queries_above_100_raises
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-041-002

### 关联需求

FR-025（LLM Query Generation & Relevance Annotation）

### 测试目标

验证 LLM 返回超过 100 条查询时截断到 100；返回少于 50 条有效查询时抛出 LLMAnnotatorError。

### 前置条件

- LLMAnnotator 已初始化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Mock LLM 返回 110 条有效查询 | Mock 配置成功 |
| 2 | 调用 generate_queries(repo, chunk_count=200, n_queries=75) | 返回恰好 100 个 EvalQuery（截断） |
| 3 | Mock LLM 返回 30 条有效查询 | Mock 配置成功 |
| 4 | 调用 generate_queries(repo, chunk_count=200, n_queries=75) | 抛出 LLMAnnotatorError("fewer than 50 valid queries") |

### 验证点

- 110 条输入 → 截断到 100 条
- 30 条输入 → LLMAnnotatorError
- chunk_count=0 → ValueError("chunk_count must be positive")

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/eval/test_annotator.py::TestGenerateQueriesBoundary::test_t23_truncates_to_100_if_llm_returns_more, tests/eval/test_annotator.py::TestGenerateQueriesErrors::test_t12_fewer_than_50_valid_queries_raises
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-041-003

### 关联需求

FR-025（LLM Query Generation & Relevance Annotation）

### 测试目标

验证 annotation 评分差值边界：差值=1 不触发 tiebreaker，差值=2 触发 tiebreaker。

### 前置条件

- LLMAnnotator 已初始化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Mock LLM 返回 "0" 和 "1"（diff=1） | Mock 配置成功 |
| 2 | 调用 annotate_relevance(query, [chunk]) | annotator_run=2（无 tiebreaker） |
| 3 | Mock LLM 返回 "0"、"2"、"2"（diff=2，触发 tiebreaker） | Mock 配置成功 |
| 4 | 调用 annotate_relevance(query, [chunk]) | annotator_run=3（触发 tiebreaker），score=2 |

### 验证点

- diff=1 → annotator_run=2，score=round(mean)
- diff=2 → annotator_run=3，使用 majority vote

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/eval/test_annotator.py::TestAnnotationBoundary::test_t24_diff_1_no_tiebreaker, tests/eval/test_annotator.py::TestAnnotationBoundary::test_t25_diff_2_triggers_tiebreaker
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-041-004

### 关联需求

FR-025（LLM Query Generation & Relevance Annotation）

### 测试目标

验证 _resolve_disagreement 当三个评分全不相同时返回中位数；_compute_kappa 对空列表抛出 ValueError，对全部相同对返回 1.0。

### 前置条件

- LLMAnnotator 已初始化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 _resolve_disagreement("q", chunk, (0, 2))，Mock 第三次返回 "3" | 返回 2（[0,2,3] 中位数） |
| 2 | 调用 _compute_kappa([]) | 抛出 ValueError("No annotation pairs") |
| 3 | 调用 _compute_kappa([(2, 2)]) — 单对完美一致 | 返回 1.0 |
| 4 | 调用 _compute_kappa([(1, 1)] * 10) — 全部相同 P_e=1.0 | 返回 1.0（无除零错误） |

### 验证点

- 三个不同分数 → 中位数
- 空列表 → ValueError
- 单对一致 → kappa=1.0
- P_e=1.0 → kappa=1.0（边界保护）

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/eval/test_annotator.py::TestResolveDisagreementBoundary::test_t28_all_three_different_returns_median, tests/eval/test_annotator.py::TestComputeKappa::test_t18_compute_kappa_empty_raises, tests/eval/test_annotator.py::TestComputeKappa::test_t26_single_pair_perfect_agreement, tests/eval/test_annotator.py::TestComputeKappa::test_t27_all_identical_pe_equals_one
- **Test Type**: Mock

---

### 用例编号

ST-SEC-041-001

### 关联需求

FR-025（LLM Query Generation & Relevance Annotation）

### 测试目标

验证不支持的 provider 名称被拒绝；缺少 API key 环境变量时初始化失败。

### 前置条件

- 环境变量不包含无效 provider 的配置

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 LLMAnnotator(provider="unsupported") | 抛出 ValueError("Unsupported provider") |
| 2 | 设置 EVAL_LLM_PROVIDER=minimax 但不设置 MINIMAX_API_KEY | Mock 配置成功 |
| 3 | 调用 LLMAnnotator(provider="minimax") | 抛出 ValueError("Missing env var: MINIMAX_API_KEY") |

### 验证点

- 不支持的 provider 名称 → ValueError，无 API 调用
- 缺少 API key → ValueError，不会泄露部分配置

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: security
- **已自动化**: Yes
- **测试引用**: tests/eval/test_annotator.py::TestProviderConfigErrors::test_t16_unsupported_provider_raises, tests/eval/test_annotator.py::TestProviderConfigErrors::test_t17_missing_api_key_raises
- **Test Type**: Mock

---

### 用例编号

ST-SEC-041-002

### 关联需求

FR-025（LLM Query Generation & Relevance Annotation）

### 测试目标

验证 LLM 返回异常内容（非 JSON、超范围评分、非数字评分）时被安全处理，不导致崩溃或信息泄露。

### 前置条件

- LLMAnnotator 已初始化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Mock LLM 返回 "not json at all" 用于 generate_queries | 抛出 LLMAnnotatorError("Failed to parse LLM response") |
| 2 | Mock LLM 返回 "5" 用于 annotate_relevance | 抛出 LLMAnnotatorError("Score 5 outside [0,3]") |
| 3 | Mock LLM 返回 "high" 用于 annotate_relevance | 抛出 LLMAnnotatorError("Annotation failed") |
| 4 | Mock LLM 引发 APIError 用于 annotate_relevance | 抛出 LLMAnnotatorError("Annotation failed") |

### 验证点

- 恶意/异常 LLM 响应被捕获并转换为 LLMAnnotatorError
- 不会传播原始异常堆栈到调用者
- 超范围评分被明确拒绝

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: security
- **已自动化**: Yes
- **测试引用**: tests/eval/test_annotator.py::TestGenerateQueriesErrors::test_t11_malformed_json_raises, tests/eval/test_annotator.py::TestAnnotationErrors::test_t13_score_outside_range_raises, tests/eval/test_annotator.py::TestAnnotationErrors::test_t32_non_numeric_score_raises, tests/eval/test_annotator.py::TestAnnotationErrors::test_t14_api_error_raises
- **Test Type**: Mock

---

---

### 用例编号

ST-FUNC-041-006

### 关联需求

FR-025（LLM Query Generation & Relevance Annotation — Golden Dataset persistence）

### 测试目标

验证 GoldenDataset.save() 将正确的 JSON 写入 eval/golden/{slug}.json，包含 repo_slug、queries、annotations、kappa 和 metadata；GoldenDataset.load() 可正确反序列化。

### 前置条件

- 有效的 GoldenDataset 对象，包含 queries 和 annotations

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 GoldenDataset(repo_slug="flask", queries=[...], annotations={...}, kappa=0.8) | 对象创建成功 |
| 2 | 调用 save("/tmp/test_golden/flask.json") | JSON 文件被写入，父目录自动创建 |
| 3 | 读取文件并解析 JSON | 包含 repo_slug, queries, annotations, kappa, metadata 键 |
| 4 | 调用 GoldenDataset.load("/tmp/test_golden/flask.json") | 返回 GoldenDataset，字段与原始对象匹配 |
| 5 | 验证 metadata.generated_at 存在 | ISO 格式时间戳 |

### 验证点

- JSON 文件包含所有必需键
- load 后的对象与 save 前的数据一致
- metadata 包含 generated_at、provider、model
- 父目录不存在时自动创建

### 后置检查

- 清理 /tmp/test_golden/ 目录

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/eval/test_golden_dataset.py
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-041-001 | FR-025 | verification_steps[0]: generate_queries produces 50-100 NL queries across 4 categories | test_t01_generates_75_queries_across_categories | Mock | PASS |
| ST-FUNC-041-002 | FR-025 | verification_steps[1]: dual annotation produces two scores; agreement path | test_t02_dual_annotate_agreement | Mock | PASS |
| ST-FUNC-041-003 | FR-025 | verification_steps[1]: dual annotation disagreement triggers third annotation | test_t03_disagreement_triggers_tiebreaker | Mock | PASS |
| ST-FUNC-041-004 | FR-025 | verification_steps[2]: Cohen Kappa computed and recorded | test_t04_kappa_with_mixed_agreement | Mock | PASS |
| ST-FUNC-041-005 | FR-025 | verification_steps[4]: Zhipu provider uses Zhipu API endpoint | test_t07_zhipu_provider_config | Mock | PASS |
| ST-FUNC-041-006 | FR-025 | verification_steps[3]: golden dataset saved with correct fields | test_golden_dataset.py | Mock | PASS |
| ST-BNDRY-041-001 | FR-025 | verification_steps[0]: n_queries boundary (50, 100) | test_t21, test_t22, test_t08, test_t09 | Mock | PASS |
| ST-BNDRY-041-002 | FR-025 | verification_steps[0]: LLM response count truncation/rejection | test_t23, test_t12 | Mock | PASS |
| ST-BNDRY-041-003 | FR-025 | verification_steps[1]: annotation score diff boundary (1 vs 2) | test_t24, test_t25 | Mock | PASS |
| ST-BNDRY-041-004 | FR-025 | verification_steps[1,2]: disagreement median + kappa edge cases | test_t28, test_t18, test_t26, test_t27 | Mock | PASS |
| ST-SEC-041-001 | FR-025 | verification_steps[4]: unsupported provider and missing credentials rejected | test_t16, test_t17 | Mock | PASS |
| ST-SEC-041-002 | FR-025 | verification_steps[1]: malicious LLM responses safely handled | test_t11, test_t13, test_t32, test_t14 | Mock | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 0 |
| Passed | 0 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> All test cases for this feature are Mock-based since the feature interacts with external LLM APIs (MiniMax/Zhipu) that require paid credentials and network access. The unit tests mock the OpenAI client to verify all logic paths.
