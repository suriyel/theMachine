# 测试用例集: Scheduled Index Refresh

**Feature ID**: 21
**关联需求**: FR-019 (Scheduled Index Refresh)
**日期**: 2026-03-22
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 3 |
| boundary | 3 |
| **合计** | **6** |

---

### 用例编号

ST-FUNC-021-001

### 关联需求

FR-019（Scheduled Index Refresh — queues reindex jobs for active repos）

### 测试目标

验证调度器触发时，为所有 status='active' 的仓库排队重新索引任务

### 前置条件

- Celery app 已配置 beat_schedule
- 数据库中存在 3 个 status='active' 的仓库
- 不存在 pending/running 状态的 IndexJob

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 配置 3 个 active 仓库的数据库 mock，无 in-progress jobs | 数据库查询返回 3 个仓库 |
| 2 | 调用 scheduled_reindex_all() | 函数执行完毕 |
| 3 | 检查返回结果 | 返回 {"queued": 3, "skipped": 0, "repos_queued": [id1, id2, id3]} |
| 4 | 验证 reindex_repo_task.delay 被调用次数 | 调用 3 次，每次传入不同的 repo_id |

### 验证点

- queued 等于 active 仓库数量 (3)
- skipped 等于 0
- repos_queued 包含所有 3 个仓库的 ID
- reindex_repo_task.delay 被调用 3 次

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_scheduler.py::TestScheduledReindexAllHappy::test_queues_all_active_repos
- **Test Type**: Real

---

### 用例编号

ST-FUNC-021-002

### 关联需求

FR-019（Scheduled Index Refresh — retry on failure）

### 测试目标

验证调度任务失败时，系统在 1 小时后重试一次；如果重试也失败，记录错误并跳过

### 前置条件

- 有效的 active 仓库存在
- reindex_repo_task 的数据库提交操作会抛出异常

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 配置 mock 使 session.commit() 抛出异常 | 异常准备就绪 |
| 2 | 调用 reindex_repo_task(repo_id) | 触发 self.retry(countdown=3600, max_retries=1) |
| 3 | 验证 retry 调用参数 | countdown=3600 (1小时), max_retries=1 |
| 4 | 模拟 retry 也失败 (MaxRetriesExceededError) | 返回 {"status": "failed"}，记录错误日志 |

### 验证点

- 第一次失败触发 retry，countdown=3600 秒
- max_retries=1（仅重试一次）
- 重试失败后记录 ERROR 级别日志
- 重试失败后返回 failed 状态，不向上传播异常

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_scheduler.py::TestReindexRepoTaskErrors::test_retries_on_db_commit_failure, tests/test_scheduler.py::TestReindexRepoTaskErrors::test_logs_error_on_retry_exhaustion
- **Test Type**: Real

---

### 用例编号

ST-FUNC-021-003

### 关联需求

FR-019（Scheduled Index Refresh — skip in-progress repos）

### 测试目标

验证调度触发时，已有进行中索引任务的仓库被跳过并记录信息

### 前置条件

- 2 个 active 仓库
- 其中 1 个仓库有 pending 或 running 状态的 IndexJob

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 配置 2 个 active 仓库，仓库 A 有 in-progress job | mock 数据就绪 |
| 2 | 调用 scheduled_reindex_all() | 函数执行完毕 |
| 3 | 检查返回结果 | {"queued": 1, "skipped": 1} |
| 4 | 验证 reindex_repo_task.delay 调用 | 仅对仓库 B 调用一次 |
| 5 | 验证日志 | 包含跳过仓库 A 的信息日志 |

### 验证点

- queued=1, skipped=1
- 仅为无 in-progress job 的仓库排队
- 跳过的仓库记录 INFO 级别日志
- 不会为 in-progress 仓库创建重复任务

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_scheduler.py::TestBoundaryConditions::test_mixed_in_progress_and_eligible
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-021-001

### 关联需求

FR-019（边界: 零活跃仓库）

### 测试目标

验证没有 active 仓库时调度器正常返回，不崩溃

### 前置条件

- 数据库中无 status='active' 的仓库

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 配置 mock 返回空的 active 仓库列表 | 查询返回 [] |
| 2 | 调用 scheduled_reindex_all() | 正常返回 |
| 3 | 检查返回结果 | {"queued": 0, "skipped": 0, "repos_queued": []} |

### 验证点

- 函数不崩溃，正常返回
- queued=0, skipped=0
- repos_queued 为空列表

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_scheduler.py::TestBoundaryConditions::test_no_active_repos
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-021-002

### 关联需求

FR-019（边界: 所有仓库都有进行中任务）

### 测试目标

验证所有 active 仓库都有进行中索引任务时，全部跳过

### 前置条件

- 3 个 active 仓库
- 所有 3 个仓库都有 pending 或 running 状态的 IndexJob

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 配置 3 个 active 仓库，均有 in-progress jobs | mock 数据就绪 |
| 2 | 调用 scheduled_reindex_all() | 正常返回 |
| 3 | 检查返回结果 | {"queued": 0, "skipped": 3} |
| 4 | 验证 reindex_repo_task.delay 未被调用 | 调用次数为 0 |

### 验证点

- queued=0, skipped=3
- 不排队任何重新索引任务
- 每个跳过的仓库记录 INFO 日志

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_scheduler.py::TestBoundaryConditions::test_all_repos_in_progress
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-021-003

### 关联需求

FR-019（边界: 分支回退逻辑）

### 测试目标

验证 reindex_repo_task 的分支选择回退链: indexed_branch → default_branch → "main"

### 前置条件

- Active 仓库，indexed_branch=None, default_branch=None

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建仓库 mock，indexed_branch=None, default_branch=None | 仓库对象就绪 |
| 2 | 调用 reindex_repo_task(repo_id) | 正常执行 |
| 3 | 检查创建的 IndexJob 的 branch 字段 | branch="main" |

### 验证点

- 当 indexed_branch 和 default_branch 均为 None 时，使用 "main" 作为回退
- IndexJob 正确记录回退的分支名

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_scheduler.py::TestBoundaryConditions::test_branch_fallback_to_main
- **Test Type**: Real

---

## 可追溯性矩阵

| 用例编号 | 需求 | verification_step | 自动化测试 | 结果 |
|----------|------|-------------------|------------|------|
| ST-FUNC-021-001 | FR-019 AC-1 | VS-1: queues reindex jobs for active repos | test_queues_all_active_repos | PASS |
| ST-FUNC-021-002 | FR-019 AC-3 | VS-2: retry once after 1 hour, log error on exhaustion | test_retries_on_db_commit_failure, test_logs_error_on_retry_exhaustion | PASS |
| ST-FUNC-021-003 | FR-019 AC-4 | VS-3: skip duplicate, log info | test_mixed_in_progress_and_eligible | PASS |
| ST-BNDRY-021-001 | FR-019 | VS-1 (boundary: 0 repos) | test_no_active_repos | PASS |
| ST-BNDRY-021-002 | FR-019 | VS-3 (boundary: all in-progress) | test_all_repos_in_progress | PASS |
| ST-BNDRY-021-003 | FR-019 | VS-1 (boundary: branch fallback) | test_branch_fallback_to_main | PASS |

## Real Test Case Execution Summary

| Total Real Cases | Passed | Failed | Pending |
|------------------|--------|--------|---------|
| 6 | 6 | 0 | 0 |
