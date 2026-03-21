# 测试用例集: Rank Fusion (RRF)

**Feature ID**: 10
**关联需求**: FR-008
**日期**: 2026-03-21
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 3 |
| boundary | 3 |
| performance | 1 |
| **合计** | **7** |

---

### 用例编号

ST-FUNC-010-001

### 关联需求

FR-008（Rank Fusion — 重叠候选项评分增强）

### 测试目标

验证当 BM25 和 vector 检索结果存在重叠候选项时，RRF 融合对重叠项正确累加分数且输出不超过 top_k 个候选项。

### 前置条件

- RankFusion 类已实现并可导入
- ScoredChunk 数据类可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构造 200 个 BM25 候选项（chunk-0 至 chunk-199）和 200 个 vector 候选项（chunk-150 至 chunk-349），重叠 50 个 | 两个列表构造成功，重叠项 ID 为 chunk-150 至 chunk-199 |
| 2 | 调用 `RankFusion(k=60).fuse(bm25, vector, top_k=50)` | 返回结果列表，长度 ≤ 50 |
| 3 | 检查重叠项（如 chunk-150）的 score 是否等于两个列表中 RRF 分数之和 | chunk-150 score = 1/(60+151) + 1/(60+1) ≈ 0.02108 |
| 4 | 比较重叠项最高分与非重叠项最高分 | 重叠项最高分 > 非重叠项最高分 |

### 验证点

- 输出列表长度 ≤ 50
- 重叠候选项的 score 等于来自两个列表的 RRF 分数之和（精度 1e-9）
- 重叠候选项排名优先于仅出现在单个列表中的候选项

### 后置检查

- 无（纯计算，无副作用）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_rank_fusion.py::TestRRFHappyPath::test_overlapping_chunks_get_boosted_scores
- **Test Type**: Real

---

### 用例编号

ST-FUNC-010-002

### 关联需求

FR-008（Rank Fusion — 单路径空结果处理）

### 测试目标

验证当一个检索路径返回空结果时，融合仅使用非空列表的候选项。

### 前置条件

- RankFusion 类已实现并可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构造一个空列表和一个包含 5 个候选项的列表 | 两个列表构造成功 |
| 2 | 调用 `RankFusion(k=60).fuse([], chunks)` | 返回 5 个候选项 |
| 3 | 验证每个候选项的 score 等于单列表 RRF 分数 | 第 i 个候选项 score = 1/(60+i)，i 从 1 开始 |

### 验证点

- 返回所有 5 个非空列表的候选项
- 每个候选项的 RRF score 仅基于其在单个列表中的排名
- 无错误抛出

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_rank_fusion.py::TestRRFHappyPath::test_one_empty_list
- **Test Type**: Real

---

### 用例编号

ST-FUNC-010-003

### 关联需求

FR-008（Rank Fusion — 4 路融合）

### 测试目标

验证 4 路输入（BM25 code、vector code、BM25 doc、vector doc）正确合并，包含 code 和 doc 两种内容类型。

### 前置条件

- RankFusion 类已实现并可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构造 4 个列表（各 100 项），分别标记 content_type 为 "code" 或 "doc" | 4 个列表构造成功 |
| 2 | 调用 `RankFusion(k=60).fuse(bm25_code, vec_code, bm25_doc, vec_doc, top_k=50)` | 返回 50 个候选项 |
| 3 | 检查输出中同时包含 content_type="code" 和 content_type="doc" 的候选项 | 两种类型均存在 |

### 验证点

- 输出长度等于 50
- 输出中包含 content_type="code" 的候选项
- 输出中包含 content_type="doc" 的候选项
- 所有 4 个输入列表的候选项均参与融合

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_rank_fusion.py::TestRRFHappyPath::test_four_way_fusion_performance
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-010-001

### 关联需求

FR-008（Rank Fusion — 空输入边界）

### 测试目标

验证当所有输入列表均为空时，融合返回空列表且不抛出异常。

### 前置条件

- RankFusion 类已实现并可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 `RankFusion(k=60).fuse()` 无参数 | 返回空列表 `[]` |
| 2 | 调用 `RankFusion(k=60).fuse([], [], [])` 三个空列表 | 返回空列表 `[]` |

### 验证点

- 无参数调用返回 `[]`
- 多个空列表调用返回 `[]`
- 无异常抛出

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_rank_fusion.py::TestRRFBoundary::test_no_args_returns_empty, tests/test_rank_fusion.py::TestRRFBoundary::test_all_empty_lists_returns_empty
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-010-002

### 关联需求

FR-008（Rank Fusion — top_k 边界值）

### 测试目标

验证 top_k=0 返回空列表，top_k=1 返回单个最高分候选项，top_k 超过候选总数时返回所有候选项。

### 前置条件

- RankFusion 类已实现并可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 `fuse(chunks, top_k=0)` 其中 chunks 有 10 项 | 返回空列表 `[]` |
| 2 | 调用 `fuse(list_a, list_b, top_k=1)` 其中两个列表有重叠 | 返回 1 个候选项，为 RRF 最高分项 |
| 3 | 调用 `fuse(list_a, list_b, top_k=50)` 其中总计仅 3 个唯一候选项 | 返回 3 个候选项，不补齐 |

### 验证点

- top_k=0 → 空列表
- top_k=1 → 恰好 1 个结果
- top_k > 总数 → 返回所有可用候选项，不多不少

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_rank_fusion.py::TestRRFBoundary::test_top_k_zero_returns_empty, tests/test_rank_fusion.py::TestRRFBoundary::test_top_k_one_returns_single, tests/test_rank_fusion.py::TestRRFBoundary::test_top_k_exceeds_available
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-010-003

### 关联需求

FR-008（Rank Fusion — 无效 k 参数）

### 测试目标

验证构造 RankFusion 时传入 k≤0 会抛出 ValueError。

### 前置条件

- RankFusion 类已实现并可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 `RankFusion(k=0)` | 抛出 `ValueError("k must be positive, got 0")` |
| 2 | 调用 `RankFusion(k=-5)` | 抛出 `ValueError("k must be positive, got -5")` |

### 验证点

- k=0 抛出 ValueError，错误信息包含 "k must be positive, got 0"
- k=-5 抛出 ValueError，错误信息包含 "k must be positive, got -5"

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_rank_fusion.py::TestRRFError::test_k_zero_raises_value_error, tests/test_rank_fusion.py::TestRRFError::test_k_negative_raises_value_error
- **Test Type**: Real

---

### 用例编号

ST-PERF-010-001

### 关联需求

FR-008（Rank Fusion — 10ms 延迟要求）

### 测试目标

验证 4 路融合（各 100 个候选项）的执行时间在 10ms 以内。

### 前置条件

- RankFusion 类已实现并可导入
- 测试环境为标准开发机（非 CI 容器）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 构造 4 个列表各含 100 个候选项 | 列表构造成功 |
| 2 | 使用 `time.perf_counter()` 计时 `fuse()` 调用 | 执行时间 < 10ms |

### 验证点

- 融合执行耗时严格小于 10ms

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: performance
- **已自动化**: Yes
- **测试引用**: tests/test_rank_fusion.py::TestRRFHappyPath::test_four_way_fusion_performance
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-010-001 | FR-008 | VS-1: 重叠候选项 RRF 评分增强，输出 ≤ 50 | test_overlapping_chunks_get_boosted_scores | Real | PASS |
| ST-FUNC-010-002 | FR-008 | VS-2: 单路径空结果仅返回非空列表 | test_one_empty_list | Real | PASS |
| ST-FUNC-010-003 | FR-008 | VS-3: 4 路融合合并所有列表 | test_four_way_fusion_performance | Real | PASS |
| ST-BNDRY-010-001 | FR-008 | VS-1, VS-2 (边界) | test_no_args_returns_empty, test_all_empty_lists_returns_empty | Real | PASS |
| ST-BNDRY-010-002 | FR-008 | VS-1 (边界: top_k) | test_top_k_zero_returns_empty, test_top_k_one_returns_single, test_top_k_exceeds_available | Real | PASS |
| ST-BNDRY-010-003 | FR-008 | VS-1 (边界: k 验证) | test_k_zero_raises_value_error, test_k_negative_raises_value_error | Real | PASS |
| ST-PERF-010-001 | FR-008 | VS-3: 执行 < 10ms | test_four_way_fusion_performance | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 7 |
| Passed | 7 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
