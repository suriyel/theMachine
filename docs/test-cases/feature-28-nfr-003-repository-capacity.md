# 测试用例集: NFR-003: Repository Capacity

**Feature ID**: 28
**关联需求**: NFR-003 (Repository Capacity)
**日期**: 2026-03-18
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

---

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 1 |
| boundary | 1 |
| performance | 2 |
| **合计** | **4** |

---

### 用例编号

ST-PERF-028-001

### 关联需求

NFR-003 (Repository Capacity) — 100-1000 repositories indexed simultaneously

### 测试目标

验证系统在 100 个仓库时能够保持查询延迟在 NFR-001 范围内（P95 <= 1000ms）

### 前置条件

- PostgreSQL、Redis、Qdrant、Elasticsearch、Query Service 服务已启动
- 100 个仓库已索引并可查询
- 负载测试工具（locust）可用

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 启动 Query Service（如未运行） | 服务在 8000 端口响应 |
| 2 | 使用 100 个已索引仓库执行负载测试 | 查询成功执行 |
| 3 | 测量 P95 延迟 | P95 <= 1000ms |

### 验证点

- P95 延迟 <= 1000ms 表示通过 NFR-001 关联要求
- 测试期间失败率应小于 1%

### 后置检查

- 记录实际 P95 延迟值

### 元数据

- **优先级**: High
- **类别**: performance
- **已自动化**: Yes
- **测试引用**: scripts/run_capacity_test.py
- **Test Type**: Real（需要真实服务运行）

---

### 用例编号

ST-PERF-028-002

### 关联需求

NFR-003 (Repository Capacity) — 1000 repositories without degradation

### 测试目标

验证系统在 1000 个仓库时能够保持查询延迟在 NFR-001 范围内（P95 <= 1000ms）

### 前置条件

- PostgreSQL、Redis、Qdrant、Elasticsearch、Query Service 服务已启动
- 1000 个仓库已索引并可查询

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 启动 Query Service（如未运行） | 服务在 8000 端口响应 |
| 2 | 使用 1000 个已索引仓库执行负载测试 | 查询成功执行 |
| 3 | 测量 P95 延迟 | P95 <= 1000ms |

### 验证点

- P95 延迟 <= 1000ms 表示通过 NFR-003 容量要求

### 后置检查

- 记录实际 P95 延迟值

### 元数据

- **优先级**: High
- **类别**: performance
- **已自动化**: Yes
- **测试引用**: scripts/run_capacity_test.py
- **Test Type**: Real

---

### 用例编号

ST-FUNC-028-001

### 关联需求

NFR-003 (Repository Capacity) — 容量验证脚本可执行

### 测试目标

验证容量测试脚本能够正确执行并报告阈值验证结果

### 前置条件

- run_capacity_test.py 脚本存在

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 执行 `python scripts/run_capacity_test.py --help` | 输出帮助信息 |
| 2 | 执行 `python scripts/run_capacity_test.py --validate --repos 500 --latency 800` | 返回 exit code 0（通过） |
| 3 | 执行 `python scripts/run_capacity_test.py --validate --repos 500 --latency 1500` | 返回 exit code 1（失败） |

### 验证点

- 脚本接受正确参数
- 阈值验证逻辑正确

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_nfr03_capacity.py
- **Test Type**: Mock（使用子进程测试脚本接口）

---

### 用例编号

ST-BNDRY-028-001

### 关联需求

NFR-003 (Repository Capacity) — 边界条件验证

### 测试目标

验证阈值边界情况下的正确行为

### 前置条件

- run_capacity_test.py 脚本可执行

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 执行 `python scripts/run_capacity_test.py --validate --repos 50 --latency 500` | 返回 exit code 1（低于最小值） |
| 2 | 执行 `python scripts/run_capacity_test.py --validate --repos 1500 --latency 500` | 返回 exit code 1（超过最大值） |
| 3 | 执行 `python scripts/run_capacity_test.py --validate --repos 100 --latency 1000` | 返回 exit code 0（边界值） |
| 4 | 执行 `python scripts/run_capacity_test.py --validate --repos 1000 --latency 1000` | 返回 exit code 0（边界值） |

### 验证点

- 100 仓库边界值通过
- 1000 仓库边界值通过
- 低于 100 失败
- 超过 1000 失败

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_nfr03_capacity.py::TestCapacityThresholdValidation
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-PERF-028-001 | NFR-003 | Given progressive addition of repositories from 100 to 1000, when measuring query latency, then latency remains within NFR-001 bounds | scripts/run_capacity_test.py | Real | PENDING |
| ST-PERF-028-002 | NFR-003 | 同上（1000 repos） | scripts/run_capacity_test.py | Real | PENDING |
| ST-FUNC-028-001 | NFR-003 | 容量验证脚本可执行 | tests/test_nfr03_capacity.py | Mock | PASS |
| ST-BNDRY-028-001 | NFR-003 | 边界条件验证 | tests/test_nfr03_capacity.py | Mock | PASS |

---

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 2 |
| Passed | 0 |
| Failed | 0 |
| Pending | 2 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.

---

## 说明

### NFR-003 测试特殊性

NFR-003 (Repository Capacity) 是非功能性需求，需要在真实运行环境下进行容量测试：

1. **PERF 类测试需要真实服务**：
   - ST-PERF-028-001 和 ST-PERF-028-002 需要所有后端服务运行（PostgreSQL, Redis, Qdrant, Elasticsearch）
   - 需要实际的仓库数据已索引（100-1000 个仓库）

2. **测试执行方式**：
   - 使用 locust 进行负载测试
   - 使用 scripts/run_capacity_test.py 进行阈值验证

3. **CI/CD 环境**：
   - 在完整 CI 环境中运行完整容量测试
   - 在开发/验证阶段可使用 --validate 参数快速验证

### 执行命令

```bash
# 完整容量测试（需要服务运行）
python scripts/run_capacity_test.py --host http://localhost:8000

# 验证已收集的指标
python scripts/run_capacity_test.py --validate --repos 500 --latency 800
python scripts/run_capacity_test.py --validate --repos 1000 --latency 950
```
