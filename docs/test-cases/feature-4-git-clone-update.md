# 测试用例集: Git Clone or Update (FR-002)

**Feature ID**: 4
**关联需求**: FR-002
**日期**: 2026-03-15
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 2 |
| boundary | 2 |
| **合计** | **4** |

---

### 用例编号

ST-FUNC-004-001

### 关联需求

FR-002 (Clone or Update Repository)

### 测试目标

验证新仓库的完整克隆操作成功执行

### 前置条件

- 工作目录存在且可写
- 网络连接到 GitHub 正常

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | -------------- | ---------------- |
| 1 | 执行 GitCloner.clone_or_update() 对于新仓库 | 返回克隆的仓库路径 |
| 2 | 验证仓库目录已创建 | 目录存在 |
| 3 | 验证 .git 目录存在 | 是有效的 Git 仓库 |
| 4 | 验证克隆的提交历史可访问 | git log 成功 |

### 验证点

- 返回的路径指向有效的 Git 仓库
- 仓库内容完整下载

### 后置检查

- 清理克隆的仓库目录

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_git_cloner.py::TestGitClonerIntegration::test_clone_public_repository
- **Test Type**: Real

---

### 用例编号

ST-FUNC-004-002

### 关联需求

FR-002 (Clone or Update Repository)

### 测试目标

验证已存在仓库的增量更新（git fetch）操作成功执行

### 前置条件

- 仓库已经克隆到工作目录
- 远程仓库有新的提交

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | -------------- | ---------------- |
| 1 | 首次克隆仓库到工作目录 | 克隆成功 |
| 2 | 执行 GitCloner.clone_or_update() 再次调用 | 返回现有仓库路径 |
| 3 | 验证 _fetch_updates 被调用 | 无异常抛出 |
| 4 | 验证远程更新已被获取 | fetch 成功完成 |

### 验证点

- 返回现有仓库路径（不是重新克隆）
- fetch 操作成功执行
- 现有文件未被删除

### 后置检查

- 清理克隆的仓库目录

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_git_cloner.py::TestCloneOrUpdate::test_clone_or_update_fetch_existing_repo
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-004-001

### 关联需求

FR-002 (Clone or Update Repository)

### 测试目标

验证无效凭据导致的克隆失败正确处理，不重试

### 前置条件

- 无

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | -------------- | ---------------- |
| 1 | 使用无效凭据的 URL 尝试克隆 | 抛出 GitCloneFailedError |
| 2 | 验证错误消息包含 "Authentication" | 错误消息正确 |
| 3 | 验证只尝试了一次（无重试） | 不重试 |

### 验证点

- 立即失败，不重试
- 错误消息明确指出认证失败

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_git_cloner.py::TestGitClonerRetry::test_auth_failure_does_not_retry
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-004-002

### 关联需求

FR-002 (Clone or Update Repository)

### 测试目标

验证网络超时时的重试逻辑正确工作

### 前置条件

- 无

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | -------------- | ---------------- |
| 1 | 模拟网络超时错误 | 首次尝试失败 |
| 2 | 验证重试次数 | 3 次重试 |
| 3 | 验证指数退避 | 等待时间递增 (1s, 2s, 4s) |
| 4 | 所有尝试失败后抛出 GitCloneFailedError | 正确的最终错误 |

### 验证点

- 重试次数为 MAX_RETRIES (3)
- 指数退避正确实现
- 最终抛出有意义的错误

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_git_cloner.py::TestGitClonerRetry::test_full_clone_retries_on_network_timeout
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-004-001 | FR-002 | Given registered repo not yet cloned, full clone is performed | test_clone_public_repository | Real | PASS |
| ST-FUNC-004-002 | FR-002 | Given previously cloned repo, git fetch retrieves latest | test_clone_or_update_fetch_existing_repo | Real | PASS |
| ST-BNDRY-004-001 | FR-002 | Invalid credentials fail immediately, no retry | test_auth_failure_does_not_retry | Real | PASS |
| ST-BNDRY-004-002 | FR-002 | Network timeout triggers retry with backoff | test_full_clone_retries_on_network_timeout | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 4 |
| Passed | 4 |
| Failed | 0 |
| Pending | 0 |
