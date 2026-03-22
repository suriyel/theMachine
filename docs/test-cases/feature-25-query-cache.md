# 测试用例集: Query Cache

**Feature ID**: 25
**关联需求**: FR-019（Query Cache）
**日期**: 2026-03-22
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 4 |
| boundary | 2 |
| **合计** | **6** |

---

### 用例编号

ST-FUNC-025-001

### 关联需求

FR-019（Query Cache）

### 测试目标

验证缓存命中时直接返回缓存结果，不执行检索流水线

### 前置条件

- QueryCache 已实例化（无 Redis，仅 L1）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 cache.set("find auth", "repo1", ["python"], response, ttl=300) | 无异常 |
| 2 | 调用 cache.get("find auth", "repo1", ["python"]) | 返回与存入相同的 QueryResponse |
| 3 | 验证返回对象字段匹配 | query, results 等字段一致 |

### 验证点

- cache.get 返回非 None 结果
- 返回的 QueryResponse 与存入的完全一致

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_query_cache.py::test_set_then_get_returns_same_response
- **Test Type**: Real

---

### 用例编号

ST-FUNC-025-002

### 关联需求

FR-019（Query Cache）

### 测试目标

验证缓存未命中时返回 None

### 前置条件

- QueryCache 已实例化，无历史数据

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 cache.get("unknown query", None, None) | 返回 None |

### 验证点

- 缓存 miss 返回 None 而非异常

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_query_cache.py::test_cache_miss_returns_none
- **Test Type**: Real

---

### 用例编号

ST-FUNC-025-003

### 关联需求

FR-019（Query Cache）

### 测试目标

验证仓库 reindex 后缓存条目被清除

### 前置条件

- QueryCache 已实例化
- 至少一个缓存条目关联到 repo_id

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 cache.set("q", "repo1", None, response) | 无异常 |
| 2 | 验证 cache.get("q", "repo1", None) 返回结果 | 非 None |
| 3 | 调用 cache.invalidate_repo("repo1") | 无异常 |
| 4 | 验证 cache.get("q", "repo1", None) | 返回 None |

### 验证点

- invalidate_repo 清除指定仓库的所有缓存
- 其他仓库缓存不受影响

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_query_cache.py::test_invalidate_repo_clears_entries
- **Test Type**: Real

---

### 用例编号

ST-FUNC-025-004

### 关联需求

FR-019（Query Cache）

### 测试目标

验证 Redis 不可用时优雅降级，不抛异常

### 前置条件

- QueryCache 使用模拟的故障 Redis 客户端

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 cache.set(...) 时 Redis 抛 ConnectionError | 无异常，方法正常返回 |
| 2 | 调用 cache.get(...) 时 Redis 抛 ConnectionError | 返回 None，无异常 |

### 验证点

- Redis 故障不传播到调用方
- 系统降级为无缓存模式

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_query_cache.py::test_redis_unavailable_get_returns_none, test_redis_unavailable_set_no_exception
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-025-001

### 关联需求

FR-019（Query Cache）

### 测试目标

验证 None repo 和 None languages 产生有效缓存键

### 前置条件

- QueryCache 已实例化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 cache.set("q", None, None, response) | 无异常 |
| 2 | 调用 cache.get("q", None, None) | 返回缓存结果 |

### 验证点

- None 参数正确序列化为缓存键
- 不产生 TypeError 或 KeyError

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_query_cache.py::test_none_repo_and_languages_produce_valid_key
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-025-002

### 关联需求

FR-019（Query Cache）

### 测试目标

验证不同 query 相同 repo 产生不同缓存条目

### 前置条件

- QueryCache 已实例化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | cache.set("query_a", "repo1", None, response_a) | 无异常 |
| 2 | cache.set("query_b", "repo1", None, response_b) | 无异常 |
| 3 | cache.get("query_a", "repo1", None) | 返回 response_a |
| 4 | cache.get("query_b", "repo1", None) | 返回 response_b |

### 验证点

- 不同 query 不覆盖彼此的缓存
- 缓存键区分 query 内容

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_query_cache.py::test_different_query_same_repo_different_entries
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-025-001 | FR-019 | VS-1: cached result returned within TTL | test_set_then_get_returns_same_response | Real | PASS |
| ST-FUNC-025-002 | FR-019 | VS-1: cache miss | test_cache_miss_returns_none | Real | PASS |
| ST-FUNC-025-003 | FR-019 | VS-2: invalidate on reindex | test_invalidate_repo_clears_entries | Real | PASS |
| ST-FUNC-025-004 | FR-019 | VS-3: Redis unavailable graceful degradation | test_redis_unavailable_* | Mock | PASS |
| ST-BNDRY-025-001 | FR-019 | VS-1: None params valid | test_none_repo_and_languages_produce_valid_key | Real | PASS |
| ST-BNDRY-025-002 | FR-019 | VS-1: different queries different entries | test_different_query_same_repo_different_entries | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 5 |
| Passed | 5 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
