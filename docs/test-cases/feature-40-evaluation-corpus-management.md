# 测试用例集: Evaluation Corpus Management

**Feature ID**: 40
**关联需求**: FR-024 (Evaluation Corpus Management)
**日期**: 2026-03-22
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 4 |
| boundary | 3 |
| security | 1 |
| **合计** | **8** |

---

### 用例编号

ST-FUNC-040-001

### 关联需求

FR-024（Evaluation Corpus Management）

### 测试目标

Verify that EvalCorpusBuilder.build() clones and indexes all accessible repos from repos.json into eval_-prefixed ES/Qdrant namespaces.

### 前置条件

- EvalCorpusBuilder is instantiated with all required dependencies (GitCloner, ContentExtractor, Chunker, EmbeddingEncoder, IndexWriter, ES client)
- A valid repos.json file exists with well-formed repo entries
- ES eval_code_chunks index does not contain documents for the repos (count == 0)

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Prepare a repos.json with 3 repo entries, each with name, url, language, branch | JSON file is valid and parseable |
| 2 | Configure ES client mock to return count=0 for all repos (not yet indexed) | Idempotency check returns False for each repo |
| 3 | Call `EvalCorpusBuilder.build(repos_json_path)` | Method executes without raising exceptions |
| 4 | Inspect returned CorpusSummary | total=3, indexed=3, skipped=0, failed=0 |
| 5 | Verify IndexWriter.write_code_chunks was called 3 times | Each repo's chunks were written to eval_ prefix indices |
| 6 | Verify GitCloner.clone_or_update was called 3 times | Each repo was cloned |

### 验证点

- CorpusSummary.total equals the number of repos in the JSON file
- CorpusSummary.indexed equals 3 (all repos successfully indexed)
- CorpusSummary.skipped and CorpusSummary.failed are both 0
- IndexWriter.write_code_chunks was invoked once per repo
- GitCloner.clone_or_update was invoked once per repo

### 后置检查

- No side effects on production indices (only eval_-prefixed indices are written)

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/eval/test_corpus_builder.py::test_build_indexes_all_repos
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-040-002

### 关联需求

FR-024（Evaluation Corpus Management）

### 测试目标

Verify that EvalCorpusBuilder.build() skips repos that are already indexed (idempotent behavior).

### 前置条件

- EvalCorpusBuilder is instantiated with all required dependencies
- A valid repos.json exists with repo entries
- ES eval_code_chunks index already contains documents for these repos (count > 0)

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Prepare repos.json with 3 repo entries | JSON file is valid |
| 2 | Configure ES client to return count > 0 for all 3 repos (already indexed) | Idempotency check returns True for each repo |
| 3 | Call `EvalCorpusBuilder.build(repos_json_path)` | Method executes without raising exceptions |
| 4 | Inspect returned CorpusSummary | total=3, indexed=0, skipped=3, failed=0 |
| 5 | Verify GitCloner.clone_or_update was NOT called | No cloning for already-indexed repos |
| 6 | Verify IndexWriter.write_code_chunks was NOT called | No indexing for already-indexed repos |

### 验证点

- CorpusSummary.skipped equals 3
- CorpusSummary.indexed equals 0
- GitCloner.clone_or_update was never invoked
- IndexWriter.write_code_chunks was never invoked

### 后置检查

- Existing indexed data in eval_ indices remains unchanged

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/eval/test_corpus_builder.py::test_build_skips_already_indexed
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-040-003

### 关联需求

FR-024（Evaluation Corpus Management）

### 测试目标

Verify that an inaccessible repo URL causes an error log but does not halt processing of remaining repos.

### 前置条件

- EvalCorpusBuilder is instantiated with all required dependencies
- repos.json contains 3 repos; repo2 has an inaccessible URL
- ES eval_code_chunks returns count=0 for all (none previously indexed)

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Prepare repos.json with 3 repo entries | JSON file is valid |
| 2 | Configure GitCloner to raise CloneError for repo2 | repo2 clone will fail |
| 3 | Call `EvalCorpusBuilder.build(repos_json_path)` | Method executes without raising exceptions |
| 4 | Inspect returned CorpusSummary | total=3, indexed=2, skipped=0, failed=1 |
| 5 | Check details list for the failed entry | Failed entry has name="repo2", status="failed", error contains "network error" |

### 验证点

- CorpusSummary.failed equals 1 (only repo2)
- CorpusSummary.indexed equals 2 (repo1 and repo3 succeeded)
- The build did not abort on the first failure — all repos were attempted
- Failed repo is recorded in details with error message

### 后置检查

- repo1 and repo3 chunks exist in eval_ indices
- No partial data for repo2

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/eval/test_corpus_builder.py::test_build_continues_on_clone_error
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-040-004

### 关联需求

FR-024（Evaluation Corpus Management）

### 测试目标

Verify that the real ES idempotency check works correctly — count-based query returns correct values for indexed and non-indexed repos.

### 前置条件

- Elasticsearch is running and healthy at localhost:9200
- No proxy interference (ALL_PROXY cleared)

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create a test ES index with keyword mapping for repo_id | Index created successfully |
| 2 | Insert a document with repo_id="test-repo" and refresh | Document indexed, shard refreshed |
| 3 | Execute ES count query with term filter repo_id="test-repo" | count == 1 |
| 4 | Execute ES count query with term filter repo_id="nonexistent" | count == 0 |
| 5 | Delete the test index in cleanup | Index deleted |

### 验证点

- ES count query correctly returns >0 for an existing repo_id
- ES count query correctly returns 0 for a non-existent repo_id
- This validates the idempotency mechanism used by _is_already_indexed

### 后置检查

- Test index is deleted (cleanup in finally block)
- No leaked indices remain

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/eval/test_corpus_builder.py::test_real_es_idempotency_check_feature_40
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-040-001

### 关联需求

FR-024（Evaluation Corpus Management）

### 测试目标

Verify that an empty repos.json array produces a CorpusSummary with all-zero counts and no errors.

### 前置条件

- EvalCorpusBuilder is instantiated with all required dependencies
- repos.json file contains an empty JSON array `[]`

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create repos.json with content `[]` | File exists with empty array |
| 2 | Call `EvalCorpusBuilder.build(repos_json_path)` | Method executes without raising exceptions |
| 3 | Inspect returned CorpusSummary | total=0, indexed=0, skipped=0, failed=0 |
| 4 | Verify details list is empty | No repo results recorded |

### 验证点

- CorpusSummary has all zero fields
- No dependencies (GitCloner, IndexWriter, etc.) were invoked
- No exceptions raised

### 后置检查

- No indices created or modified

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/eval/test_corpus_builder.py::test_build_empty_repos_list
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-040-002

### 关联需求

FR-024（Evaluation Corpus Management）

### 测试目标

Verify that a repo containing only non-CODE files (e.g., DOC files) is still counted as indexed but produces zero chunks.

### 前置条件

- EvalCorpusBuilder is instantiated with all required dependencies
- repos.json has 1 repo entry
- ContentExtractor returns only DOC-type files for this repo

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Prepare repos.json with 1 repo | JSON file is valid |
| 2 | Configure ContentExtractor to return only DOC-type files | No CODE files in extraction result |
| 3 | Call `EvalCorpusBuilder.build(repos_json_path)` | Method executes without exceptions |
| 4 | Inspect returned CorpusSummary | total=1, indexed=1, skipped=0, failed=0 |
| 5 | Verify EmbeddingEncoder.encode_batch was NOT called | No chunks to embed |
| 6 | Verify IndexWriter.write_code_chunks was NOT called | No chunks to write |

### 验证点

- Repo is counted as "indexed" even with 0 code chunks (not "failed")
- Embedding and write operations are skipped when there are no code chunks
- A warning is logged about no code chunks

### 后置检查

- No eval_ index data written for this repo

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/eval/test_corpus_builder.py::test_build_no_code_files
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-040-003

### 关联需求

FR-024（Evaluation Corpus Management）

### 测试目标

Verify that when ES is unavailable for the idempotency check, the builder falls back to re-indexing the repo instead of failing.

### 前置条件

- EvalCorpusBuilder is instantiated with all required dependencies
- ES client count operation raises a ConnectionError
- GitCloner, ContentExtractor, Chunker, EmbeddingEncoder, IndexWriter all work normally

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Prepare repos.json with 1 repo | JSON file is valid |
| 2 | Configure ES client count to raise ConnectionError | Idempotency check will fail |
| 3 | Call `EvalCorpusBuilder.build(repos_json_path)` | Method executes without raising exceptions |
| 4 | Inspect returned CorpusSummary | total=1, indexed=1, skipped=0, failed=0 |
| 5 | Verify GitCloner.clone_or_update was called | Repo was cloned despite ES check failure |

### 验证点

- _is_already_indexed returns False on ES error (safe fallback)
- Repo is re-indexed rather than skipped or failed
- A warning is logged about the idempotency check failure

### 后置检查

- None

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/eval/test_corpus_builder.py::test_build_es_unavailable_for_idempotency
- **Test Type**: Mock

---

### 用例编号

ST-SEC-040-001

### 关联需求

FR-024（Evaluation Corpus Management）

### 测试目标

Verify that repos.json entries with missing required fields or invalid values (empty name) are rejected with clear error messages, preventing injection of malformed data into the indexing pipeline.

### 前置条件

- EvalCorpusBuilder is instantiated with all required dependencies

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create repos.json with an entry missing the "url" field | File parseable but entry is invalid |
| 2 | Call `EvalCorpusBuilder.build(repos_json_path)` | ValueError raised mentioning "missing" fields |
| 3 | Create repos.json with an entry with name="" (empty string) | File parseable but name is invalid |
| 4 | Call `EvalCorpusBuilder.build(repos_json_path)` | ValueError raised mentioning "name" |
| 5 | Create repos.json with malformed JSON syntax | File not parseable |
| 6 | Call `EvalCorpusBuilder.build(repos_json_path)` | ValueError raised mentioning "valid JSON" |

### 验证点

- Missing required fields in repo entries are detected before any pipeline operations
- Empty repo names are explicitly rejected (prevents silent ES query issues)
- Malformed JSON is caught and reported with a clear message
- No partial pipeline execution occurs for invalid input

### 后置检查

- No indices were created or modified
- No git clone operations were initiated

### 元数据

- **优先级**: High
- **类别**: security
- **已自动化**: Yes
- **测试引用**: tests/eval/test_corpus_builder.py::test_build_missing_required_field, tests/eval/test_corpus_builder.py::test_build_empty_repo_name, tests/eval/test_corpus_builder.py::test_build_malformed_json
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-040-001 | FR-024 | VS-1: All accessible repos cloned and indexed with eval_ prefix | test_build_indexes_all_repos | Mock | PASS |
| ST-FUNC-040-002 | FR-024 | VS-2: Skips already-indexed repos (idempotent) | test_build_skips_already_indexed | Mock | PASS |
| ST-FUNC-040-003 | FR-024 | VS-3: Logs error for inaccessible repo, continues with remaining | test_build_continues_on_clone_error | Mock | PASS |
| ST-FUNC-040-004 | FR-024 | VS-1: Idempotency mechanism verified against real ES | test_real_es_idempotency_check_feature_40 | Real | PASS |
| ST-BNDRY-040-001 | FR-024 | VS-1: Empty repos list boundary | test_build_empty_repos_list | Mock | PASS |
| ST-BNDRY-040-002 | FR-024 | VS-1: No code files boundary | test_build_no_code_files | Mock | PASS |
| ST-BNDRY-040-003 | FR-024 | VS-2: ES unavailable fallback for idempotency | test_build_es_unavailable_for_idempotency | Mock | PASS |
| ST-SEC-040-001 | FR-024 | VS-1: Input validation prevents malformed data entering pipeline | test_build_missing_required_field, test_build_empty_repo_name, test_build_malformed_json | Mock | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 1 |
| Passed | 1 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
