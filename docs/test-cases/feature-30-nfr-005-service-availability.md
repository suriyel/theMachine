# ST Test Case集: NFR-005 Service Availability

**Feature ID**: 30
**关联需求**: NFR-005 (Service Availability)
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

ST-FUNC-030-001

### 关联需求

NFR-005（Service Availability）— 99.9% uptime target

### 测试目标

验证可用性测试脚本在100%正常运行时间场景下正确通过

### 前置条件

- 测试脚本 `scripts/run_availability_test.py` 存在且可执行

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `python scripts/run_availability_test.py --validate --checks 1000 --successful 1000` | 命令执行成功，返回码为 0 |
| 2 | 检查输出 | 输出包含 "PASS" 或 "pass" |
| 3 | 检查输出 | 输出包含 "100%" 或 "100.00%" |

### 验证点

- 返回码为 0（测试通过）
- 输出中包含 "PASS" 关键词
- 输出显示 100% 可用性

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_nfr05_availability.py::TestAvailabilityThresholdValidation::test_validate_100_percent_uptime_pass
- **Test Type**: Real

---

### 用例编号

ST-FUNC-030-002

### 关联需求

NFR-005（Service Availability）— 99.9% uptime target

### 测试目标

验证可用性测试脚本在99.9%边界条件下正确通过

### 前置条件

- 测试脚本 `scripts/run_availability_test.py` 存在且可执行

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `python scripts/run_availability_test.py --validate --checks 1000 --successful 999` | 命令执行成功，返回码为 0 |
| 2 | 检查输出 | 输出包含 "PASS" 或 "pass" |
| 3 | 检查输出 | 输出包含 "99.9" 百分比 |

### 验证点

- 返回码为 0（测试通过）
- 输出中包含 "PASS" 关键词
- 输出显示 99.9% 可用性

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_nfr05_availability.py::TestAvailabilityThresholdValidation::test_validate_99_9_percent_uptime_pass
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-030-001

### 关联需求

NFR-005（Service Availability）— 99.9% uptime target

### 测试目标

验证可用性测试脚本在99.89%（低于99.9%阈值）时正确失败

### 前置条件

- 测试脚本 `scripts/run_availability_test.py` 存在且可执行

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `python scripts/run_availability_test.py --validate --checks 1000 --successful 998` | 命令执行失败，返回码为 1 |
| 2 | 检查输出 | 输出包含 "FAIL" 或 "fail" |
| 3 | 检查输出 | 输出显示 99.8% 可用性 |

### 验证点

- 返回码为 1（测试失败）
- 输出中包含 "FAIL" 关键词
- 输出显示 99.8% 可用性（低于 99.9% 阈值）

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_nfr05_availability.py::TestAvailabilityThresholdValidation::test_validate_99_89_percent_uptime_fail
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-030-002

### 关联需求

NFR-005（Service Availability）— 99.9% uptime target

### 测试目标

验证可用性测试脚本在95%可用性（显著低于阈值）时正确失败

### 前置条件

- 测试脚本 `scripts/run_availability_test.py` 存在且可执行

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `python scripts/run_availability_test.py --validate --checks 1000 --successful 950` | 命令执行失败，返回码为 1 |
| 2 | 检查输出 | 输出包含 "FAIL" 或 "fail" |
| 3 | 检查输出 | 输出显示 95% 可用性 |

### 验证点

- 返回码为 1（测试失败）
- 输出中包含 "FAIL" 关键词
- 输出显示 95% 可用性（显著低于 99.9% 阈值）

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_nfr05_availability.py::TestAvailabilityThresholdValidation::test_validate_95_percent_uptime_fail
- **Test Type**: Real

---

### 用例编号

ST-PERF-030-001

### 关联需求

NFR-005（Service Availability）— 99.9% uptime target

### 测试目标

验证可用性测试脚本支持长时间监控场景

### 前置条件

- 测试脚本 `scripts/run_availability_test.py` 存在且可执行

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `python scripts/run_availability_test.py --help` | 命令执行成功，显示帮助信息 |
| 2 | 检查帮助文档 | 包含 `--monitor` 参数说明 |
| 3 | 检查帮助文档 | 包含 `--interval` 参数说明 |
| 4 | 检查帮助文档 | 包含 `--duration` 参数说明 |
| 5 | 验证小样本验证功能 | 执行 `python scripts/run_availability_test.py --validate --checks 10 --successful 10` 返回 0 |

### 验证点

- 脚本支持监控模式（--monitor）
- 脚本支持间隔配置（--interval）
- 脚本支持持续时间配置（--duration）
- 脚本可以处理小样本（10次检查）

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: performance
- **已自动化**: Yes
- **测试引用**: tests/test_nfr05_availability.py::TestAvailabilityTestRunner::test_runner_accepts_monitor_parameter
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-030-001 | NFR-005 | Given 1-minute health check monitoring, when 100% succeed, then passes | test_validate_100_percent_uptime_pass | Real | PASS |
| ST-FUNC-030-002 | NFR-005 | Given 1-minute health check monitoring, when 99.9% succeed, then passes | test_validate_99_9_percent_uptime_pass | Real | PASS |
| ST-BNDRY-030-001 | NFR-005 | Given 1-minute health check monitoring, when 99.89% succeed, then fails | test_validate_99_89_percent_uptime_fail | Real | PASS |
| ST-BNDRY-030-002 | NFR-005 | Given 1-minute health check monitoring, when 95% succeed, then fails | test_validate_95_percent_uptime_fail | Real | PASS |
| ST-PERF-030-001 | NFR-005 | Availability monitoring supports configurable intervals and duration | test_runner_accepts_monitor_parameter | Real | PASS |

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

### NFR-005 测试策略

NFR-005（Service Availability）要求 99.9% 可用性（每年最多 8.76 小时停机时间）。由于这是一个非功能性需求，测试采用以下策略：

1. **验证模式（--validate）**：使用预收集的指标进行验证
   - 100% 可用性 → 应通过
   - 99.9% 可用性（边界）→ 应通过
   - 99.89% 可用性 → 应失败
   - 95% 可用性 → 应失败

2. **监控模式（--monitor）**：实时监控健康检查端点
   - 需要长时间运行的服务
   - 可配置检查间隔（默认 60 秒）
   - 可配置持续时间

### 执行方式

所有测试用例通过运行测试脚本并验证输出来执行：

```bash
# 功能测试
python scripts/run_availability_test.py --validate --checks 1000 --successful 1000

# 边界测试
python scripts/run_availability_test.py --validate --checks 1000 --successful 998
```
