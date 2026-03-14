# ST Test Case Document: Rank Fusion (FR-010)

**Feature ID**: 10
**关联需求**: FR-010 (Fuse Retrieval Results)
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

ST-FUNC-010-001

### 关联需求

FR-010 (Fuse Retrieval Results)

### 测试目标

验证RRF算法能够正确合并关键字检索和语义检索的结果，包括去重和排序

### 前置条件

- Python环境已配置
- src/query/rank_fusion模块可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 导入RankFusion类和Candidate类 | 导入成功，无错误 |
| 2 | 创建关键字检索结果列表 [A, B, C] | 列表包含3个Candidate对象 |
| 3 | 创建语义检索结果列表 [B, D, E] | 列表包含3个Candidate对象 |
| 4 | 实例化RankFusion(k=60) | RankFusion对象创建成功 |
| 5 | 调用fuse(keyword_results, semantic_results) | 返回融合后的列表 |
| 6 | 验证返回列表包含5个唯一chunk_id: A, B, C, D, E | 验证通过 |
| 7 | 验证B因为同时出现在两个列表中而排名第一 | B的chunk_id为"A" |

### 验证点

- 融合结果包含所有5个唯一chunks
- 重复的chunk_id B被去重，只出现一次
- B排在第一位（因为同时出现在两个列表中）
- 原始的Candidate元数据被保留

### 后置检查

- 无需清理（纯函数，无外部状态）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_rank_fusion.py::test_rrf_with_overlapping_results
- **Test Type**: Mock (pure function, no external I/O)

---

### 用例编号

ST-FUNC-010-002

### 关联需求

FR-010 (Fuse Retrieval Results)

### 测试目标

验证当关键字检索结果为空时，RRF能正确返回语义检索结果

### 前置条件

- Python环境已配置
- src/query/rank_fusion模块可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建空的关键字检索结果列表 [] | 列表为空 |
| 2 | 创建语义检索结果列表 [A, B] | 列表包含2个Candidate对象 |
| 3 | 调用fuse(keyword_results, semantic_results) | 返回融合后的列表 |
| 4 | 验证返回列表长度为2 | 长度为2 |
| 5 | 验证返回列表chunk_id顺序为 [A, B] | 顺序正确 |

### 验证点

- 返回语义检索的所有结果
- 结果顺序保持不变

### 后置检查

- 无需清理（纯函数，无外部状态）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_rank_fusion.py::test_rrf_with_empty_keyword_results
- **Test Type**: Mock (pure function, no external I/O)

---

### 用例编号

ST-FUNC-010-003

### 关联需求

FR-010 (Fuse Retrieval Results)

### 测试目标

验证当两个检索结果都为空时，RRF返回空列表

### 前置条件

- Python环境已配置
- src/query/rank_fusion模块可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建空的关键字检索结果列表 [] | 列表为空 |
| 2 | 创建空的语义检索结果列表 [] | 列表为空 |
| 3 | 调用fuse(keyword_results, semantic_results) | 返回空列表 |
| 4 | 验证返回列表长度为0 | 长度为0 |

### 验证点

- 返回空列表而不是None或抛出异常
- 无错误发生

### 后置检查

- 无需清理（纯函数，无外部状态）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_rank_fusion.py::test_rrf_with_both_empty
- **Test Type**: Mock (pure function, no external I/O)

---

### 用例编号

ST-BNDRY-010-001

### 关联需求

FR-010 (Fuse Retrieval Results)

### 测试目标

验证RRF能正确处理完全不重叠的结果列表

### 前置条件

- Python环境已配置
- src/query/rank_fusion模块可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建关键字检索结果列表 [A, B] | 列表包含2个Candidate对象 |
| 2 | 创建语义检索结果列表 [C, D] | 列表包含2个Candidate对象 |
| 3 | 调用fuse(keyword_results, semantic_results) | 返回融合后的列表 |
| 4 | 验证返回列表长度为4 | 长度为4 |
| 5 | 验证所有4个唯一chunk_id都存在 | A, B, C, D 都存在 |

### 验证点

- 不重叠的结果正确合并
- 没有去重发生（因为没有重复）

### 后置检查

- 无需清理（纯函数，无外部状态）

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_rank_fusion.py::test_rrf_with_all_unique_results
- **Test Type**: Mock (pure function, no external I/O)

---

### 用例编号

ST-BNDRY-010-002

### 关联需求

FR-010 (Fuse Retrieval Results)

### 测试目标

验证RRF能够正确处理同一列表中的重复chunk_id并进行去重

### 前置条件

- Python环境已配置
- src/query/rank_fusion模块可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建包含重复chunk_id的关键字检索结果 [A, A] | 列表包含2个Candidate，但chunk_id重复 |
| 2 | 创建语义检索结果列表 [B] | 列表包含1个Candidate |
| 3 | 调用fuse(keyword_results, semantic_results) | 返回融合后的列表 |
| 4 | 验证A只出现一次 | count(A) = 1 |
| 5 | 验证B出现一次 | count(B) = 1 |
| 6 | 验证总长度为2 | 长度为2 |

### 验证点

- 重复的chunk_id被正确去重
- 保留第一次出现的Candidate

### 后置检查

- 无需清理（纯函数，无外部状态）

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_rank_fusion.py::test_rrf_duplicate_chunk_ids_deduplicated
- **Test Type**: Mock (pure function, no external I/O)

---

### 用例编号

ST-BNDRY-010-003

### 关联需求

FR-010 (Fuse Retrieval Results)

### 测试目标

验证RRF能够正确保留原始Candidate的所有元数据字段

### 前置条件

- Python环境已配置
- src/query/rank_fusion模块可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建包含完整元数据的关键字检索结果 | 包含chunk_id, repo_name, file_path, symbol, content, score, language |
| 2 | 创建空的语义检索结果列表 [] | 列表为空 |
| 3 | 调用fuse(keyword_results, semantic_results) | 返回融合后的列表 |
| 4 | 验证返回的Candidate包含原始的所有元数据 | chunk_id, repo_name, file_path, symbol, content, score, language 都保留 |

### 验证点

- repo_name 被保留
- file_path 被保留
- symbol 被保留
- content 被保留
- score 被保留（原始分数，不是RRF分数）
- language 被保留

### 后置检查

- 无需清理（纯函数，无外部状态）

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_rank_fusion.py::test_rrf_preserves_candidate_metadata
- **Test Type**: Mock (pure function, no external I/O)

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|------------------|-----------|-----------|------|
| ST-FUNC-010-001 | FR-010 | 融合keyword [A,B,C] + semantic [B,D,E] → 5个唯一chunks | test_rrf_with_overlapping_results | Mock | PASS |
| ST-FUNC-010-002 | FR-010 | keyword空 + semantic [A,B] → [A,B] | test_rrf_with_empty_keyword_results | Mock | PASS |
| ST-FUNC-010-003 | FR-010 | keyword空 + semantic空 → 空列表 | test_rrf_with_both_empty | Mock | PASS |
| ST-BNDRY-010-001 | FR-010 | 完全不重叠的结果合并 | test_rrf_with_all_unique_results | Mock | PASS |
| ST-BNDRY-010-002 | FR-010 | 重复chunk_id去重 | test_rrf_duplicate_chunk_ids_deduplicated | Mock | PASS |
| ST-BNDRY-010-003 | FR-010 | Candidate元数据保留 | test_rrf_preserves_candidate_metadata | Mock | PASS |

---

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 0 |
| Passed | 0 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.

> **Note**: This feature is a pure function with no external I/O. All test cases are classified as "Mock" because they test the algorithm in isolation without connecting to real services (Qdrant, Elasticsearch). The unit tests provide complete coverage of the RRF algorithm behavior.

---

## 执行说明

由于本功能是纯函数（无外部I/O），无需启动服务。测试用例通过运行现有的单元测试来执行验证：

```bash
pytest tests/test_rank_fusion.py -v
```

所有6个测试用例均通过。
