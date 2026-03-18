# ST Test Case集: NFR-006 Linear Scalability

**Feature ID**: 31
**关联需求**: NFR-006 (Linear Scalability)
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

ST-FUNC-031-001

### 关联需求

NFR-006（Linear Scalability）— 80-120% linear scaling

### 测试目标

验证可扩展性测试脚本在100%线性扩展场景下正确通过

### 前置条件

- 测试脚本 `scripts/run_scalability_test.py` 存在且可执行

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `python scripts/run_scalability_test.py --validate --nodes 1 --throughput 1000 --nodes1 2 --throughput1 2000` | 命令执行成功，返回码为 0 |
| 2 | 检查输出 | 输出包含 "PASS" 或 "pass" |
| 3 | 检查输出 | 输出显示 "100.00%" |

### 验证点

- 返回码为 0（测试通过）
- 输出中包含 "PASS" 关键词
- 输出显示 100% 扩展

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_nfr06_scalability.py::TestScalabilityThresholdValidation::test_validate_100_percent_scaling_pass
- **Test Type**: Real

---

### 用例编号

ST-FUNC-031-002

### 关联需求

NFR-006（Linear Scalability）— 80-120% linear scaling

### 测试目标

验证可扩展性测试脚本在3节点到4节点扩展场景下正确通过

### 前置条件

- 测试脚本 `scripts/run_scalability_test.py` 存在且可执行

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `python scripts/run_scalability_test.py --validate --nodes 3 --throughput 3000 --nodes1 4 --throughput1 4000` | 命令执行成功，返回码为 0 |
| 2 | 检查输出 | 输出包含 "PASS" 或 "pass" |
| 3 | 检查输出 | 输出显示 "100.00%" |

### 验证点

- 返回码为 0（测试通过）
- 输出中包含 "PASS" 关键词

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_nfr06_scalability.py::TestScalabilityThresholdValidation::test_validate_4_nodes_scaling_pass
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-031-001

### 关联需求

NFR-006（Linear Scalability）— 80-120% linear scaling

### 测试目标

验证可扩展性测试脚本在79%（低于80%阈值）时正确失败

### 前置条件

- 测试脚本 `scripts/run_scalability_test.py` 存在且可执行

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `python scripts/run_scalability_test.py --validate --nodes 1 --throughput 1000 --nodes1 2 --throughput1 1790` | 命令执行失败，返回码为 1 |
| 2 | 检查输出 | 输出包含 "FAIL" 或 "fail" |

### 验证点

- 返回码为 1（测试失败）
- 输出中包含 "FAIL" 关键词
- 输出显示 79% 扩展（低于 80% 阈值）

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_nfr06_scalability.py::TestScalabilityThresholdValidation::test_validate_79_percent_scaling_fail
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-031-002

### 关联需求

NFR-006（Linear Scalability）— 80-120% linear scaling

### 测试目标

验证可扩展性测试脚本在121%（高于120%阈值）时正确失败

### 前置条件

- 测试脚本 `scripts/run_scalability_test.py` 存在且可执行

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `python scripts/run_scalability_test.py --validate --nodes 1 --throughput 1000 --nodes1 2 --throughput1 2210` | 命令执行失败，返回码为 1 |
| 2 | 检查输出 | 输出包含 "FAIL" 或 "fail" |

### 验证点

- 返回码为 1（测试失败）
- 输出中包含 "FAIL" 关键词
- 输出显示 121% 扩展（高于 120% 阈值）

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_nfr06_scalability.py::TestScalabilityThresholdValidation::test_validate_121_percent_scaling_fail
- **Test Type**: Real

---

### 用例编号

ST-PERF-031-001

### 关联需求

NFR-006（Linear Scalability）— 80-120% linear scaling

### 测试目标

验证可扩展性测试脚本支持自定义阈值配置

### 前置条件

- 测试脚本 `scripts/run_scalability_test.py` 存在且可执行

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 执行 `python scripts/run_scalability_test.py --help` | 命令执行成功，显示帮助信息 |
| 2 | 检查帮助文档 | 包含 `--threshold-min` 参数说明 |
| 3 | 检查帮助文档 | 包含 `--threshold-max` 参数说明 |
| 4 | 验证自定义阈值 | 执行 `python scripts/run_scalability_test.py --validate --nodes 1 --throughput 1000 --nodes1 2 --throughput1 1500 --threshold-min 40 --threshold-max 160` 返回 0 |

### 验证点

- 脚本支持自定义阈值最小值（--threshold-min）
- 脚本支持自定义阈值最大值（--threshold-max）
- 自定义阈值可以改变验证结果

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: performance
- **已自动化**: Yes
- **测试引用**: tests/test_nfr06_scalability.py::TestScalabilityThresholdValidation::test_validate_custom_threshold_pass
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-031-001 | NFR-006 | Given N nodes, when adding 1 node provides 100% gain, then passes | test_validate_100_percent_scaling_pass | Real | PASS |
| ST-FUNC-031-002 | NFR-006 | Given 3 nodes, when adding 1 node provides 100% gain, then passes | test_validate_4_nodes_scaling_pass | Real | PASS |
| ST-BNDRY-031-001 | NFR-006 | Given 1 node scaling to 2 nodes, when 79% gain, then fails | test_validate_79_percent_scaling_fail | Real | PASS |
| ST-BNDRY-031-002 | NFR-006 | Given 1 node scaling to 2 nodes, when 121% gain, then fails | test_validate_121_percent_scaling_fail | Real | PASS |
| ST-PERF-031-001 | NFR-006 | Custom thresholds supported | test_validate_custom_threshold_pass | Real | PASS |

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

### NFR-006 测试策略

NFR-006（Linear Scalability）要求添加一个节点时吞吐量增加 80-120%（线性扩展）。测试采用以下策略：

1. **验证模式（--validate）**：使用预收集的指标进行验证
   - 100% 扩展 → 应通过
   - 80% 扩展（边界）→ 应通过
   - 120% 扩展（边界）→ 应通过
   - 79% 扩展 → 应失败
   - 121% 扩展 → 应失败

2. **公式**：
   ```
   每节点容量 = 吞吐量 / 节点数
   吞吐量增益 = 吞吐量1 - 吞吐量
   扩展百分比 = (实际增益 / 每节点容量) * 100
   ```

### 执行方式

所有测试用例通过运行测试脚本并验证输出来执行：

```bash
# 功能测试
python scripts/run_scalability_test.py --validate --nodes 1 --throughput 1000 --nodes1 2 --throughput1 2000

# 边界测试
python scripts/run_scalability_test.py --validate --nodes 1 --throughput 1000 --nodes1 2 --throughput1 1790
```
