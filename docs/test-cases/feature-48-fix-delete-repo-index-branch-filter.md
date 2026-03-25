# 测试用例集: Fix delete_repo_index Branch Filter on Doc/Rule Indices

**Feature ID**: 48
**关联需求**: FR-020 (Manual Reindex Trigger)
**日期**: 2026-03-25
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 3 |
| boundary | 2 |
| ui | 0 |
| security | 0 |
| accessibility | 0 |
| performance | 0 |
| **合计** | **5** |

---

### 用例编号

ST-FUNC-048-001

### 关联需求

FR-020（Manual Reindex Trigger）

### 测试目标

Verify that `delete_repo_index` deletes doc_chunks and rule_chunks using a repo_id-only filter (no branch field) so that documents without a branch field are correctly removed.

### 前置条件

- IndexWriter is instantiated with valid ES and Qdrant client connections
- ES indices `doc_chunks` and `rule_chunks` contain documents with a `repo_id` field but NO `branch` field
- A known `repo_id` ("repo-1") and `branch` ("main") are provided as arguments

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Call `delete_repo_index(repo_id="repo-1", branch="main")` | Method executes without exception |
| 2 | Inspect the ES `delete_by_query` call for `doc_chunks` index | Query body contains `{"term": {"repo_id": "repo-1"}}` only — no `{"term": {"branch": ...}}` clause |
| 3 | Inspect the ES `delete_by_query` call for `rule_chunks` index | Query body contains `{"term": {"repo_id": "repo-1"}}` only — no `{"term": {"branch": ...}}` clause |
| 4 | Count the `must` clauses in both `doc_chunks` and `rule_chunks` query bodies | Each has exactly 1 must clause (repo_id term only) |

### 验证点

- doc_chunks delete query has exactly 1 must clause containing only repo_id
- rule_chunks delete query has exactly 1 must clause containing only repo_id
- Neither query body contains any branch term

### 后置检查

- No stale doc_chunks or rule_chunks remain for the given repo_id

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_index_writer.py::test_feature_48_delete_doc_rule_chunks_uses_repo_only_filter, tests/test_index_writer.py::test_feature_48_doc_chunks_query_body_no_branch_term, tests/test_index_writer.py::test_feature_48_exact_es_query_structures
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-048-002

### 关联需求

FR-020（Manual Reindex Trigger）

### 测试目标

Verify that `delete_repo_index` deletes code_chunks and code_embeddings using a repo_id+branch filter, preserving branch-aware filtering for indices that have the branch field.

### 前置条件

- IndexWriter is instantiated with valid ES and Qdrant client connections
- ES index `code_chunks` contains documents with both `repo_id` and `branch` fields
- Qdrant collection `code_embeddings` contains points with both `repo_id` and `branch` payload fields

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Call `delete_repo_index(repo_id="repo-1", branch="main")` | Method executes without exception |
| 2 | Inspect the ES `delete_by_query` call for `code_chunks` index | Query body contains both `{"term": {"repo_id": "repo-1"}}` and `{"term": {"branch": "main"}}` in the must clause |
| 3 | Inspect the Qdrant `delete` call for `code_embeddings` collection | Filter has 2 FieldConditions: `repo_id = "repo-1"` and `branch = "main"` |
| 4 | Verify `code_chunks` query must clause count | Exactly 2 must clauses |

### 验证点

- code_chunks ES query uses both repo_id and branch terms
- code_embeddings Qdrant filter uses both repo_id and branch conditions
- Exactly 2 filter conditions in each

### 后置检查

- No code_chunks or code_embeddings for repo_id+branch remain

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_index_writer.py::test_feature_48_delete_code_chunks_uses_repo_branch_filter, tests/test_index_writer.py::test_feature_48_exact_es_query_structures, tests/test_index_writer.py::test_feature_48_exact_qdrant_filter_structures
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-048-003

### 关联需求

FR-020（Manual Reindex Trigger）

### 测试目标

Verify that `delete_repo_index` deletes doc_embeddings from Qdrant using a repo_id-only filter (no branch condition), since doc_embeddings documents have no branch payload.

### 前置条件

- IndexWriter is instantiated with valid ES and Qdrant client connections
- Qdrant collection `doc_embeddings` contains points with `repo_id` payload only (no `branch` payload)

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Call `delete_repo_index(repo_id="repo-1", branch="main")` | Method executes without exception |
| 2 | Inspect the Qdrant `delete` call for `doc_embeddings` collection | Filter has exactly 1 FieldCondition: `repo_id = "repo-1"` |
| 3 | Verify no branch condition exists in the doc_embeddings filter | `branch` key is absent from filter conditions |

### 验证点

- doc_embeddings Qdrant delete filter has exactly 1 condition (repo_id only)
- No branch FieldCondition is present in the filter

### 后置检查

- No stale doc_embeddings remain for the given repo_id

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_index_writer.py::test_feature_48_delete_doc_embeddings_uses_repo_only_filter, tests/test_index_writer.py::test_feature_48_exact_qdrant_filter_structures
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-048-001

### 关联需求

FR-020（Manual Reindex Trigger）

### 测试目标

Verify that `delete_repo_index` handles an empty repo_id string gracefully — all 5 delete operations execute without raising an exception (queries match nothing, which is correct behavior).

### 前置条件

- IndexWriter is instantiated with valid ES and Qdrant client connections
- No documents exist matching an empty repo_id

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Call `delete_repo_index(repo_id="", branch="main")` | Method executes without exception |
| 2 | Verify ES `delete_by_query` call count | Exactly 3 calls made (code_chunks, doc_chunks, rule_chunks) |
| 3 | Verify Qdrant `delete` call count | Exactly 2 calls made (code_embeddings, doc_embeddings) |

### 验证点

- No exception raised for empty repo_id
- All 5 delete operations are still attempted (3 ES + 2 Qdrant)
- Each returns 0 deleted documents (silent no-op)

### 后置检查

- N/A — empty repo_id matches nothing

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_index_writer.py::test_feature_48_empty_repo_id_no_error
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-048-002

### 关联需求

FR-020（Manual Reindex Trigger）

### 测试目标

Verify that `delete_repo_index` handles the case where no documents match any filter — all delete operations return 0 deleted and no exception is raised.

### 前置条件

- IndexWriter is instantiated with valid ES and Qdrant client connections
- No documents exist matching the given repo_id in any index or collection

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Call `delete_repo_index(repo_id="nonexistent-repo", branch="main")` where no documents exist in any index | Method executes without exception |
| 2 | Verify ES `delete_by_query` returns `{"deleted": 0}` for all 3 indices | No exception raised, 0 documents deleted |
| 3 | Verify Qdrant `delete` completes for both collections | No exception raised |

### 验证点

- No exception raised when 0 documents match any filter
- All 5 delete operations are executed (not short-circuited)

### 后置检查

- N/A — no documents were affected

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_index_writer.py::test_feature_48_no_matching_docs_no_error
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-048-001 | FR-020 | verification_step[0]: doc_chunks and rule_chunks deleted with repo_id-only filter | test_feature_48_delete_doc_rule_chunks_uses_repo_only_filter, test_feature_48_doc_chunks_query_body_no_branch_term, test_feature_48_exact_es_query_structures | Mock | PASS |
| ST-FUNC-048-002 | FR-020 | verification_step[1]: code_chunks and code_embeddings deleted with repo_id+branch filter | test_feature_48_delete_code_chunks_uses_repo_branch_filter, test_feature_48_exact_es_query_structures, test_feature_48_exact_qdrant_filter_structures | Mock | PASS |
| ST-FUNC-048-003 | FR-020 | verification_step[2]: doc_embeddings deleted with repo_id-only filter | test_feature_48_delete_doc_embeddings_uses_repo_only_filter, test_feature_48_exact_qdrant_filter_structures | Mock | PASS |
| ST-BNDRY-048-001 | FR-020 | verification_step[0], verification_step[1], verification_step[2] | test_feature_48_empty_repo_id_no_error | Mock | PASS |
| ST-BNDRY-048-002 | FR-020 | verification_step[0], verification_step[1], verification_step[2] | test_feature_48_no_matching_docs_no_error | Mock | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 0 |
| Passed | 0 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
