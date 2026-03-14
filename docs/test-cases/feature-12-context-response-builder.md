# ST Test Case Document: Context Response Builder

**Feature ID**: 12
**关联需求**: FR-012 (Return Context Response)
**日期**: 2026-03-15
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

---

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 3 |
| boundary | 3 |
| ui | 0 |
| security | 0 |
| accessibility | 0 |
| performance | 0 |
| **合计** | **6** |

---

### 用例编号

ST-FUNC-012-001

### 关联需求

FR-012 (Return Context Response)

### 测试目标

Given 50 ranked candidates after reranking, when response is built, then exactly 3 results are returned with all required fields

### 前置条件

- ContextResponseBuilder 已初始化，top_k=3
- 50 个 Candidate 对象已创建，包含不同的 score 值

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 创建 50 个 Candidate 对象，score 从 1.0 到 0.01 递减 | candidates 列表包含 50 个元素 |
| 2 | 调用 builder.build(candidates) | 返回结果列表 |
| 3 | 验证 len(results) == 3 | 返回结果数量为 3 |
| 4 | 验证 results[0].repository 字段存在且非空 | 字段映射正确 |
| 5 | 验证 results[0].file_path 字段存在且非空 | 字段映射正确 |
| 6 | 验证 results[0].symbol 字段存在（可为 None） | 字段映射正确 |
| 7 | 验证 results[0].score 字段存在且为数值 | 字段映射正确 |
| 8 | 验证 results[0].content 字段存在且非空 | 字段映射正确 |

### 验证点

- 返回结果数量为 3
- 每个结果包含所有必需字段：repository, file_path, symbol, score, content
- 字段值与输入 Candidate 对应

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_response_builder.py::TestContextResponseBuilder::test_build_returns_top_3_from_50_candidates
- **Test Type**: Real

---

### 用例编号

ST-FUNC-012-002

### 关联需求

FR-012 (Return Context Response)

### 测试目标

Given zero candidates after full pipeline, when response is built, then empty results array is returned with no error

### 前置条件

- ContextResponseBuilder 已初始化，top_k=3
- 输入空列表 []

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 调用 builder.build([]) | 返回空列表 |
| 2 | 验证 results == [] | 返回空列表 |
| 3 | 验证 results 是 list 类型 | 类型正确 |

### 验证点

- 返回空列表，无异常抛出
- 返回类型为 list

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_response_builder.py::TestContextResponseBuilder::test_build_returns_empty_list_when_no_candidates
- **Test Type**: Real

---

### 用例编号

ST-FUNC-012-003

### 关联需求

FR-012 (Return Context Response)

### 测试目标

Verify all fields are correctly mapped from Candidate to ContextResult

### 前置条件

- ContextResponseBuilder 已初始化，top_k=3
- 1 个包含所有字段的 Candidate 对象

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 创建 Candidate: chunk_id="chunk_1", repo_name="spring-framework", file_path="src/RestTemplate.java", symbol="RestTemplate", content="public class", score=0.95 | Candidate 创建成功 |
| 2 | 调用 builder.build([candidate]) | 返回包含 1 个结果 |
| 3 | 验证 results[0].repository == "spring-framework" | 字段映射正确 |
| 4 | 验证 results[0].file_path == "src/RestTemplate.java" | 字段映射正确 |
| 5 | 验证 results[0].symbol == "RestTemplate" | 字段映射正确 |
| 6 | 验证 results[0].score == 0.95 | 字段映射正确 |
| 7 | 验证 results[0].content == "public class" | 字段映射正确 |

### 验证点

- 所有字段正确从 Candidate 映射到 ContextResult

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_response_builder.py::TestContextResponseBuilder::test_build_transforms_candidate_fields_correctly
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-012-001

### 关联需求

FR-012 (Return Context Response)

### 测试目标

Given 2 candidates when top_k is 3, when response is built, then 2 results returned (less than top_k)

### 前置条件

- ContextResponseBuilder 已初始化，top_k=3
- 2 个 Candidate 对象

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 创建 2 个 Candidate: scores 0.8, 0.5 | candidates 列表包含 2 个元素 |
| 2 | 调用 builder.build(candidates) | 返回结果列表 |
| 3 | 验证 len(results) == 2 | 返回结果数量为 2 |
| 4 | 验证 results[0].score == 0.8 | 较高 score 在前 |
| 5 | 验证 results[1].score == 0.5 | 较低 score 在后 |

### 验证点

- 返回所有可用的结果（不足 top_k 时）
- 结果按 score 降序排列

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_response_builder.py::TestContextResponseBuilder::test_build_with_less_than_top_k_candidates
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-012-002

### 关联需求

FR-012 (Return Context Response)

### 测试目标

Given custom top_k=5, when response is built, then exactly 5 results returned

### 前置条件

- ContextResponseBuilder 已初始化，top_k=5
- 20 个 Candidate 对象

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 创建 20 个 Candidate，score 从 2.0 到 0.01 | candidates 列表包含 20 个元素 |
| 2 | 调用 builder.build(candidates) | 返回结果列表 |
| 3 | 验证 len(results) == 5 | 返回结果数量为 5（top_k） |

### 验证点

- 自定义 top_k 参数生效

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_response_builder.py::TestContextResponseBuilder::test_build_with_custom_top_k
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-012-003

### 关联需求

FR-012 (Return Context Response)

### 测试目标

Given results with varying scores, when response is built, then results are ordered by score descending

### 前置条件

- ContextResponseBuilder 已初始化，top_k=3
- 3 个具有不同 score 的 Candidate 对象

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 创建 3 个 Candidate: scores 0.3, 0.9, 0.6 | candidates 列表包含 3 个元素 |
| 2 | 调用 builder.build(candidates) | 返回结果列表 |
| 3 | 验证 results[0].score == 0.9 | 最高分排在第一 |
| 4 | 验证 results[1].score == 0.6 | 中间分排在第二 |
| 5 | 验证 results[2].score == 0.3 | 最低分排在第三 |

### 验证点

- 结果按 score 降序排列

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_response_builder.py::TestContextResponseBuilder::test_build_orders_results_by_score_descending
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-012-001 | FR-012 | Given 50 ranked candidates... | test_build_returns_top_3_from_50_candidates | Real | PASS |
| ST-FUNC-012-002 | FR-012 | Given zero candidates... | test_build_returns_empty_list_when_no_candidates | Real | PASS |
| ST-FUNC-012-003 | FR-012 | Verify field mapping | test_build_transforms_candidate_fields_correctly | Real | PASS |
| ST-BNDRY-012-001 | FR-012 | Given < top_k candidates | test_build_with_less_than_top_k_candidates | Real | PASS |
| ST-BNDRY-012-002 | FR-012 | Custom top_k | test_build_with_custom_top_k | Real | PASS |
| ST-BNDRY-012-003 | FR-012 | Score ordering | test_build_orders_results_by_score_descending | Real | PASS |

---

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 6 |
| Passed | 6 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
