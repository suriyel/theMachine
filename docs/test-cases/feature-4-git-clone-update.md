# 测试用例集: Git Clone & Update

**Feature ID**: 4
**关联需求**: FR-002（Git Clone & Update）
**日期**: 2026-03-21
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 3 |
| boundary | 2 |
| **合计** | **5** |

---

### 用例编号

ST-FUNC-004-001

### 关联需求

FR-002（Git Clone & Update）

### 测试目标

验证首次克隆新注册仓库时，GitCloner将仓库克隆到 REPO_CLONE_PATH/{repo_id} 并包含默认分支的 HEAD。

### 前置条件

- REPO_CLONE_PATH 环境变量已设置且目录可写
- 目标 repo_id 目录不存在（首次克隆）
- 网络可达 https://github.com/octocat/Hello-World

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 GitCloner 实例，storage_path 指向临时目录 | GitCloner 实例创建成功 |
| 2 | 调用 clone_or_update(repo_id="test-001", url="https://github.com/octocat/Hello-World") | 返回路径字符串 "{storage_path}/test-001" |
| 3 | 检查返回路径是否存在 | 目录存在 |
| 4 | 检查 {返回路径}/.git 目录是否存在 | .git 目录存在（完整 git 仓库） |
| 5 | 列出返回路径下的文件 | 包含 README 文件（非空仓库） |

### 验证点

- 返回路径等于 `{storage_path}/{repo_id}`
- 克隆目录包含 `.git` 子目录
- 克隆目录包含至少一个非 `.git` 文件

### 后置检查

- 清理临时目录

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_feature_4_git_cloner.py::test_real_clone_public_repo
- **Test Type**: Real

---

### 用例编号

ST-FUNC-004-002

### 关联需求

FR-002（Git Clone & Update）

### 测试目标

验证对已克隆仓库调用 clone_or_update 时，执行 git fetch + git reset（非重新克隆），返回相同路径。

### 前置条件

- 仓库已被克隆到 REPO_CLONE_PATH/{repo_id}（.git 目录存在）
- 网络可达

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 GitCloner 实例并首次调用 clone_or_update 克隆仓库 | 返回 dest_path，.git 目录存在 |
| 2 | 再次调用 clone_or_update，相同 repo_id 和 url | 返回相同路径 |
| 3 | 检查 .git 目录仍然存在 | .git 目录存在 |
| 4 | 验证仓库内容完整 | 文件仍然存在 |

### 验证点

- 第二次调用返回值与第一次相同
- .git 目录在更新后仍存在
- 仓库内容完整（非空）

### 后置检查

- 清理临时目录

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_feature_4_git_cloner.py::test_real_update_after_clone
- **Test Type**: Real

---

### 用例编号

ST-FUNC-004-003

### 关联需求

FR-002（Git Clone & Update）

### 测试目标

验证克隆失败（不可达URL）时抛出 CloneError 并清理残留文件。

### 前置条件

- REPO_CLONE_PATH 已配置
- 目标 URL 不可达（https://invalid.example.com/no-repo.git）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 GitCloner 实例 | 实例创建成功 |
| 2 | 调用 clone_or_update(repo_id="bad-repo", url="https://invalid.example.com/no-repo.git") | 抛出 CloneError 异常 |
| 3 | 检查 {storage_path}/bad-repo 目录是否存在 | 目录不存在（已被清理） |

### 验证点

- CloneError 异常被抛出
- 异常消息包含错误描述
- 残留目录被自动清理

### 后置检查

- 确认无残留文件

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_feature_4_git_cloner.py::test_real_clone_invalid_url_raises_clone_error
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-004-001

### 关联需求

FR-002（Git Clone & Update）

### 测试目标

验证 git 命令超时（>300秒）时抛出 CloneError 并包含 "timed out" 信息。

### 前置条件

- GitCloner 实例已创建
- subprocess.run 被模拟为超时

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 模拟 subprocess.run 抛出 TimeoutExpired(timeout=300) | 模拟设置完成 |
| 2 | 调用 clone_or_update | 抛出 CloneError |
| 3 | 检查异常消息 | 包含 "timed out" 字符串 |

### 验证点

- CloneError 异常被抛出
- 异常消息包含 "timed out"
- 超时值为 300 秒

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_feature_4_git_cloner.py::test_timeout_raises_clone_error
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-004-002

### 关联需求

FR-002（Git Clone & Update）

### 测试目标

验证 git 二进制文件不存在时抛出 CloneError 并包含 "git not found" 信息。

### 前置条件

- GitCloner 实例已创建
- subprocess.run 被模拟为抛出 FileNotFoundError

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 模拟 subprocess.run 抛出 FileNotFoundError | 模拟设置完成 |
| 2 | 调用 clone_or_update | 抛出 CloneError |
| 3 | 检查异常消息 | 包含 "git not found" 字符串 |

### 验证点

- CloneError 异常被抛出
- 异常消息包含 "git not found"
- FileNotFoundError 被正确包装

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_feature_4_git_cloner.py::test_git_not_found_raises_clone_error
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-004-001 | FR-002 | VS-1: clone to REPO_CLONE_PATH/{repo_id} | test_real_clone_public_repo | Real | PASS |
| ST-FUNC-004-002 | FR-002 | VS-2: fetch+reset without re-cloning | test_real_update_after_clone | Real | PASS |
| ST-FUNC-004-003 | FR-002 | VS-3: CloneError + cleanup on failure | test_real_clone_invalid_url_raises_clone_error | Real | PASS |
| ST-BNDRY-004-001 | FR-002 | VS-3: CloneError on failure (timeout) | test_timeout_raises_clone_error | Mock | PASS |
| ST-BNDRY-004-002 | FR-002 | VS-3: CloneError on failure (git missing) | test_git_not_found_raises_clone_error | Mock | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 3 |
| Passed | 3 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
