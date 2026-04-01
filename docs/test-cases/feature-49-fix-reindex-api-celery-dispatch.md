# 测试用例集: Fix reindex API endpoint not dispatching Celery task

**Feature ID**: 49
**关联需求**: FR-020 (Manual Reindex Trigger)
**日期**: 2026-04-01
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

ST-FUNC-049-001

### 关联需求

FR-020（Manual Reindex Trigger）

### 测试目标

Verify that POST `/api/v1/repos/{repo_id}/reindex` with valid admin credentials dispatches `reindex_repo_task.delay()` with the repo ID as a string, and returns 200 with `job_id`, `repo_id`, and `status="pending"`.

### 前置条件

- Application is running with mock session containing a valid repository record
- Admin API key is authenticated
- `reindex_repo_task` is mocked to capture dispatch call

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create test app with admin API key and mock session containing a repo with known `repo_id` | App created, mock repo available in session |
| 2 | Mock `reindex_repo_task` and `IndexJob` in the endpoint module | Mocks ready to capture calls |
| 3 | POST `/api/v1/repos/{repo_id}/reindex` via TestClient | Response received |
| 4 | Assert response status code is 200 | HTTP 200 OK |
| 5 | Assert response JSON contains `job_id`, `repo_id` matching the test repo, and `status="pending"` | All fields present and correct |
| 6 | Assert `reindex_repo_task.delay` was called exactly once with `str(repo_id)` | `delay()` called with string representation of repo UUID |

### 验证点

- HTTP response is 200
- Response body contains valid `job_id`, correct `repo_id`, and `status="pending"`
- `reindex_repo_task.delay()` was called exactly once
- The argument to `delay()` is `str(repo.id)` (string type, not UUID object)

### 后置检查

- No side effects to clean up (mocked environment)

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_reindex_celery_dispatch.py::test_reindex_dispatches_celery_task, tests/test_reindex_celery_dispatch.py::test_reindex_dispatch_args_are_string
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-049-002

### 关联需求

FR-020（Manual Reindex Trigger）

### 测试目标

Verify that POST `/api/v1/repos/{repo_id}/reindex` with a non-existent repository UUID returns 404 and does NOT dispatch any Celery task.

### 前置条件

- Application is running with mock session that returns `None` for repo lookup
- Admin API key is authenticated
- `reindex_repo_task` is mocked to verify no dispatch occurs

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create test app with admin API key, session returns `None` for any repo query | App created, no repo in mock session |
| 2 | Mock `reindex_repo_task` in the endpoint module | Mock ready |
| 3 | POST `/api/v1/repos/{nonexistent_uuid}/reindex` via TestClient | Response received |
| 4 | Assert response status code is 404 | HTTP 404 Not Found |
| 5 | Assert `reindex_repo_task.delay` was NOT called | No Celery task dispatched |

### 验证点

- HTTP response is 404
- `reindex_repo_task.delay()` was never called
- No IndexJob record was created (session.add not called with IndexJob)

### 后置检查

- No side effects to clean up (mocked environment)

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_reindex_celery_dispatch.py::test_reindex_nonexistent_repo_no_dispatch
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-049-003

### 关联需求

FR-020（Manual Reindex Trigger）

### 测试目标

Verify that when `reindex_repo_task.delay()` raises an exception (e.g., Celery broker unavailable), the endpoint still returns 200 with a valid IndexJob record — the dispatch failure is gracefully handled.

### 前置条件

- Application is running with mock session containing a valid repository record
- Admin API key is authenticated
- `reindex_repo_task.delay` is mocked to raise `ConnectionError`

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create test app with admin API key and mock session containing a repo | App created with valid repo |
| 2 | Mock `reindex_repo_task.delay` to raise `ConnectionError("Celery broker down")` | Mock configured to fail on dispatch |
| 3 | POST `/api/v1/repos/{repo_id}/reindex` via TestClient | Response received despite dispatch failure |
| 4 | Assert response status code is 200 | HTTP 200 OK — endpoint did not crash |
| 5 | Assert response JSON contains valid `job_id` and `repo_id` | IndexJob was created and returned |
| 6 | Assert `session.commit()` was called | IndexJob record was persisted to DB before dispatch attempt |

### 验证点

- HTTP response is 200 even though Celery dispatch failed
- Response body contains valid `job_id` and `repo_id`
- `session.commit()` was called (IndexJob record was persisted)
- Endpoint did not propagate the `ConnectionError`

### 后置检查

- No side effects to clean up (mocked environment)

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_reindex_celery_dispatch.py::test_reindex_dispatch_failure_still_returns_success
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-049-001

### 关联需求

FR-020（Manual Reindex Trigger）

### 测试目标

Verify that `session.commit()` is called BEFORE `reindex_repo_task.delay()` — the IndexJob record must exist in the database before the Celery worker could pick it up.

### 前置条件

- Application is running with mock session containing a valid repository record
- Admin API key is authenticated
- Both `session.commit` and `reindex_repo_task.delay` are instrumented to record call order

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create test app with admin API key and mock session containing a repo | App created |
| 2 | Instrument `session.commit` and `reindex_repo_task.delay` to record call order in a shared list | Instrumentation ready |
| 3 | POST `/api/v1/repos/{repo_id}/reindex` via TestClient | Response 200 |
| 4 | Assert `commit` appears in the call order list before `delay` | `commit` index < `delay` index |

### 验证点

- Both `commit` and `delay` are called
- `commit` is called strictly before `delay` in execution order

### 后置检查

- No side effects to clean up (mocked environment)

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_reindex_celery_dispatch.py::test_reindex_commit_before_dispatch
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-049-002

### 关联需求

FR-020（Manual Reindex Trigger）

### 测试目标

Verify that the reindex endpoint succeeds when `app.state.query_cache` is absent (None) — no `AttributeError` or other exception occurs when cache invalidation is skipped.

### 前置条件

- Application is running with mock session containing a valid repository record
- Admin API key is authenticated
- `app.state.query_cache` is not set (attribute deleted or never assigned)

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create test app with admin API key and mock session containing a repo | App created |
| 2 | Remove `query_cache` from `app.state` if present | No cache object on app state |
| 3 | POST `/api/v1/repos/{repo_id}/reindex` via TestClient | Response received |
| 4 | Assert response status code is 200 | HTTP 200 OK — no crash from missing cache |
| 5 | Assert `reindex_repo_task.delay` was called | Celery task was still dispatched |

### 验证点

- HTTP response is 200
- No `AttributeError` for missing `query_cache`
- `reindex_repo_task.delay()` was still called successfully

### 后置检查

- No side effects to clean up (mocked environment)

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_reindex_celery_dispatch.py::test_reindex_no_cache_still_succeeds
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-049-001 | FR-020 | verification_step[0]: reindex_repo_task.delay() is called with the repo ID | test_reindex_dispatches_celery_task, test_reindex_dispatch_args_are_string | Mock | PASS |
| ST-FUNC-049-002 | FR-020 | AC-2: non-existent repo returns 404 | test_reindex_nonexistent_repo_no_dispatch | Mock | PASS |
| ST-FUNC-049-003 | FR-020 | verification_step[1]: dispatch fails, IndexJob still created, endpoint returns successfully | test_reindex_dispatch_failure_still_returns_success | Mock | PASS |
| ST-BNDRY-049-001 | FR-020 | verification_step[0]: commit before dispatch ordering | test_reindex_commit_before_dispatch | Mock | PASS |
| ST-BNDRY-049-002 | FR-020 | verification_step[0]: endpoint succeeds without cache | test_reindex_no_cache_still_succeeds | Mock | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 0 |
| Passed | 0 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
