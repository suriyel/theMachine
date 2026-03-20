# ST Test Case集: NFR-007 Single-Node Failure Tolerance

**Feature ID**: 32
**关联需求**: NFR-007 (Single-Node Failure Tolerance)
**日期**: 2026-03-18
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

---

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 2 |
| boundary | 2 |
| ui | 0 |
| security | 0 |
| accessibility | 0 |
| performance | 1 |
| **合计** | **5** |

---

### 用例编号

ST-FUNC-032-001

### 关联需求

NFR-007（Single-Node Failure Tolerance）— zero query failures, failover <= 30s

### 测试目标

验证故障转移测试脚本在零失败、快速故障转移场景下正确通过

### 前置条件

- 测试脚本 `scripts/run_failover_test.py` 存在且可执行

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `python scripts/run_failover_test.py --validate --queries 1000 --failures 0 --failover-time 5` | 命令执行成功，返回码为 0 |
| 2 | 检查输出 | 输出包含 "PASS" 或 "pass" |
| 3 | 检查输出 | 输出显示零失败 |

### 验证点

- 返回码为 0（测试通过）
- 输出中包含 "PASS" 关键词
- 输出显示 0 failures <= max failures

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_nfr07_failover.py::TestFailoverThresholdValidation::test_validate_zero_failures_fast_failover_pass
- **Test Type**: Real

---

### 用例编号

ST-FUNC-032-002

### 关联需求

NFR-007（Single-Node Failure Tolerance）— zero query failures, failover <= 30s

### 测试目标

验证故障转移测试脚本在零失败、30秒边界故障转移场景下正确通过

### 前置条件

- 测试脚本 `scripts/run_failover_test.py` 存在且可执行

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `python scripts/run_failover_test.py --validate --queries 1000 --failures 0 --failover-time 30` | 命令执行成功，返回码为 0 |
| 2 | 检查输出 | 输出包含 "PASS" 或 "pass" |

### 验证点

- 返回码为 0（测试通过）
- 输出中包含 "PASS" 关键词
- 30s 等于最大阈值，应通过

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_nfr07_failover.py::TestFailoverThresholdValidation::test_validate_zero_failures_30s_failover_pass
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-032-001

### 关联需求

NFR-007（Single-Node Failure Tolerance）— zero query failures, failover <= 30s

### 测试目标

验证故障转移测试脚本在1个失败时正确失败（零容忍）

### 前置条件

- 测试脚本 `scripts/run_failover_test.py` 存在且可执行

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `python scripts/run_failover_test.py --validate --queries 1000 --failures 1 --failover-time 5` | 命令执行失败，返回码为 1 |
| 2 | 检查输出 | 输出包含 "FAIL" 或 "fail" |

### 验证点

- 返回码为 1（测试失败）
- 输出中包含 "FAIL" 关键词
- 输出显示 failures > max failures

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_nfr07_failover.py::TestFailoverThresholdValidation::test_validate_one_failure_fail
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-032-002

### 关联需求

NFR-007（Single-Node Failure Tolerance）— zero query failures, failover <= 30s

### 测试目标

验证故障转移测试脚本在31秒故障转移时间（超过30秒阈值）时正确失败

### 前置条件

- 测试脚本 `scripts/run_failover_test.py` 存在且可执行

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `python scripts/run_failover_test.py --validate --queries 1000 --failures 0 --failover-time 31` | 命令执行失败，返回码为 1 |
| 2 | 检查输出 | 输出包含 "FAIL" 或 "fail" |

### 验证点

- 返回码为 1（测试失败）
- 输出中包含 "FAIL" 关键词
- 输出显示 failover_time > max_time

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_nfr07_failover.py::TestFailoverThresholdValidation::test_validate_31s_failover_fail
- **Test Type**: Real

---

### 用例编号

ST-PERF-032-001

### 关联需求

NFR-007（Single-Node Failure Tolerance）— zero query failures, failover <= 30s

### 测试目标

验证故障转移测试脚本支持自定义阈值配置

### 前置条件

- 测试脚本 `scripts/run_failover_test.py` 存在且可执行

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `python scripts/run_failover_test.py --help` | 命令执行成功，显示帮助信息 |
| 2 | 检查帮助文档 | 包含 `--max-failures` 参数说明 |
| 3 | 检查帮助文档 | 包含 `--max-time` 参数说明 |
| 4 | 验证自定义阈值 | 执行 `python scripts/run_failover_test.py --validate --queries 100 --failures 5 --failover-time 5 --max-failures 10` 返回 0 |

### 验证点

- 脚本支持自定义最大失败数（--max-failures）
- 脚本支持自定义最大故障转移时间（--max-time）
- 自定义阈值可以改变验证结果

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: performance
- **已自动化**: Yes
- **测试引用**: tests/test_nfr07_failover.py::TestFailoverThresholdValidation::test_validate_custom_max_failures_pass
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-032-001 | NFR-007 | Given zero failures with 5s failover, then passes | test_validate_zero_failures_fast_failover_pass | Real | PASS |
| ST-FUNC-032-002 | NFR-007 | Given zero failures with 30s failover, then passes | test_validate_zero_failures_30s_failover_pass | Real | PASS |
| ST-BNDRY-032-001 | NFR-007 | Given 1 failure, then fails (zero tolerance) | test_validate_one_failure_fail | Real | PASS |
| ST-BNDRY-032-002 | NFR-007 | Given 31s failover, then fails (> 30s) | test_validate_31s_failover_fail | Real | PASS |
| ST-PERF-032-001 | NFR-007 | Custom thresholds supported | test_validate_custom_max_failures_pass | Real | PASS |

---

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 5 |
| Passed | 5 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.

---

## 测试说明

### NFR-007 测试策略

NFR-007（Single-Node Failure Tolerance）要求单节点故障期间零查询失败，故障转移时间 <= 30秒。测试采用以下策略：

1. **验证模式（--validate）**：使用预收集的指标进行验证
   - 零失败 + 快速故障转移 → 应通过
   - 零失败 + 30秒故障转移（边界）→ 应通过
   - 1个失败 → 应失败（零容忍）
   - 31秒故障转移 → 应失败（超过30秒阈值）
   - 60秒故障转移 → 应失败

2. **阈值**：
   - 最大失败数：0（零容忍）
   - 最大故障转移时间：30秒

3. **输入验证**：
   - queries > 0
   - failures >= 0
   - failures <= queries
   - failover_time >= 0

### 执行方式

所有测试用例通过运行测试脚本并验证输出来执行：

```bash
# 功能测试
python scripts/run_failover_test.py --validate --queries 1000 --failures 0 --failover-time 5

# 边界测试
python scripts/run_failover_test.py --validate --queries 1000 --failures 1 --failover-time 5
python scripts/run_failover_test.py --validate --queries 1000 --failures 0 --failover-time 31
```
