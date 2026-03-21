# 测试用例集: Branch Listing API

**Feature ID**: 33
**关联需求**: FR-023 (Branch Listing API)
**日期**: 2026-03-22
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

ST-FUNC-033-001

### 关联需求

FR-023（Branch Listing API）

### 测试目标

验证已克隆仓库的分支列表请求返回 200，包含按字母排序的分支名和默认分支。

### 前置条件

- API 服务已启动，健康检查通过
- 数据库中存在一个已注册且已克隆的仓库（clone_path 不为 None，default_branch = "main"）
- 有效的 API Key（admin 或 read 权限）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 使用有效 API Key 发送 GET /api/v1/repos/{id}/branches | HTTP 200 OK |
| 2 | 解析响应 JSON body | body 包含 `branches` (list) 和 `default_branch` (string) |
| 3 | 检查 branches 列表排序 | 列表按字母升序排列 |
| 4 | 检查 default_branch 值 | default_branch == "main" |

### 验证点

- 响应状态码为 200
- branches 是字符串列表，按字母排序
- default_branch 与仓库数据库记录一致
- 分支名不包含 "origin/" 前缀

### 后置检查

- 无状态变更，无清理需要

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_feature_33_branch_listing.py::test_list_branches_happy_path
- **Test Type**: Real

---

### 用例编号

ST-FUNC-033-002

### 关联需求

FR-023（Branch Listing API）

### 测试目标

验证不存在的仓库 ID 返回 404 Not Found。

### 前置条件

- API 服务已启动
- 有效的 API Key

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 生成一个随机 UUID（数据库中不存在） | UUID 已准备 |
| 2 | 使用有效 API Key 发送 GET /api/v1/repos/{random_uuid}/branches | HTTP 404 Not Found |
| 3 | 解析响应 JSON body | body 包含 detail 字段 |
| 4 | 检查 detail 值 | detail 包含 "not found" |

### 验证点

- 响应状态码为 404
- 响应 body 包含明确的错误信息

### 后置检查

- 无状态变更

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_feature_33_branch_listing.py::test_list_branches_repo_not_found
- **Test Type**: Real

---

### 用例编号

ST-FUNC-033-003

### 关联需求

FR-023（Branch Listing API）

### 测试目标

验证已注册但未克隆的仓库返回 409 Conflict。

### 前置条件

- API 服务已启动
- 数据库中存在一个仓库，clone_path 为 None（未克隆）
- 有效的 API Key

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 使用有效 API Key 发送 GET /api/v1/repos/{id}/branches | HTTP 409 Conflict |
| 2 | 解析响应 JSON body | body 包含 detail 字段 |
| 3 | 检查 detail 值 | detail 包含 "not been cloned" |

### 验证点

- 响应状态码为 409
- 错误消息明确指出仓库尚未克隆

### 后置检查

- 无状态变更

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_feature_33_branch_listing.py::test_list_branches_not_cloned
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-033-001

### 关联需求

FR-023（Branch Listing API）

### 测试目标

验证克隆仓库无远程分支时返回空列表。

### 前置条件

- API 服务已启动
- 数据库中存在已克隆仓库，但远程分支列表为空
- 有效的 API Key

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 使用有效 API Key 发送 GET /api/v1/repos/{id}/branches | HTTP 200 OK |
| 2 | 解析响应 JSON body | branches 为空列表 [] |
| 3 | 检查 default_branch | default_branch 仍有值（回退为 "main"） |

### 验证点

- 响应状态码为 200（不因空列表而失败）
- branches 为空数组 []
- default_branch 使用回退值

### 后置检查

- 无状态变更

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_feature_33_branch_listing.py::test_list_branches_empty_list
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-033-002

### 关联需求

FR-023（Branch Listing API）

### 测试目标

验证仓库 default_branch 为 None 时，响应回退为 "main"。

### 前置条件

- API 服务已启动
- 数据库中存在已克隆仓库，default_branch 字段为 NULL
- 有效的 API Key

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 使用有效 API Key 发送 GET /api/v1/repos/{id}/branches | HTTP 200 OK |
| 2 | 检查 default_branch 值 | default_branch == "main" |

### 验证点

- 当数据库 default_branch 为 NULL 时，API 返回 "main" 作为回退值
- 不返回 null 或空字符串

### 后置检查

- 无状态变更

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_feature_33_branch_listing.py::test_list_branches_default_branch_none_fallback
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-033-001 | FR-023 | VS-1: 200 with sorted branches and default_branch | test_list_branches_happy_path | Real | PASS |
| ST-FUNC-033-002 | FR-023 | VS-2: 404 Not Found for unknown repo | test_list_branches_repo_not_found | Real | PASS |
| ST-FUNC-033-003 | FR-023 | VS-3: 409 Conflict for uncloned repo | test_list_branches_not_cloned | Real | PASS |
| ST-BNDRY-033-001 | FR-023 | VS-1 (boundary: empty branches) | test_list_branches_empty_list | Real | PASS |
| ST-BNDRY-033-002 | FR-023 | VS-1 (boundary: null default_branch) | test_list_branches_default_branch_none_fallback | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 5 |
| Passed | 5 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
