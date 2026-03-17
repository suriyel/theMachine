# 测试用例集: NFR-002: Query Throughput

**Feature ID**: 27
**关联需求**: NFR-002 (Query Throughput)
**日期**: 2026-03-17
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

ST-PERF-027-001

### 关联需求

NFR-002 (Query Throughput) — Query service shall sustain target throughput

### 测试目标

验证系统在持续负载下能够达到 1000 QPS 的吞吐量要求

### 前置条件

- PostgreSQL、Redis、Qdrant、Elasticsearch、Query Service 服务已启动并正常运行
- Query Service 已在 http://localhost:8000 启动
- 已配置有效的 API Key（环境变量或测试 Key）
- 系统已索引足够的测试数据用于查询

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 启动 Query Service（如果未运行） | 服务在 8000 端口响应 |
| 2 | 执行持续负载测试：`locust -f locustfile.py --headless -u 1000 -r 100 -t 600s --host http://localhost:8000` | 测试启动并运行 10 分钟 |
| 3 | 等待测试完成，收集统计数据 | 测试完成，输出吞吐量指标 |
| 4 | 解析 locust 输出，提取 RPS（每秒请求数） | 获得实际吞吐量数值 |

### 验证点

- RPS >= 1000 表示通过 NFR-002 持续吞吐量要求
- 测试期间失败率应小于 1%
- P95 延迟应 <= 1000ms（NFR-001 相关）

### 后置检查

- 记录实际吞吐量数值到测试报告
- 清理测试产生的数据（如需要）

### 元数据

- **优先级**: High
- **类别**: performance
- **已自动化**: Yes
- **测试引用**: tests/test_nfr02_throughput.py, locustfile.py
- **Test Type**: Real（需要真实服务运行）

---

### 用例编号

ST-PERF-027-002

### 关联需求

NFR-002 (Query Throughput) — Peak burst >= 2000 QPS

### 测试目标

验证系统在突发负载下能够达到 2000 QPS 的峰值吞吐量

### 前置条件

- PostgreSQL、Redis、Qdrant、Elasticsearch、Query Service 服务已启动并正常运行
- Query Service 已在 http://localhost:8000 启动

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 启动 Query Service（如果未运行） | 服务在 8000 端口响应 |
| 2 | 执行突发负载测试：`locust -f locustfile.py --headless -u 2000 -r 500 -t 30s --host http://localhost:8000` | 测试以高并发启动 |
| 3 | 等待测试完成，收集统计数据 | 测试完成，输出峰值吞吐量 |
| 4 | 解析 locust 输出，提取峰值 RPS | 获得实际峰值吞吐量数值 |

### 验证点

- Peak RPS >= 2000 表示通过 NFR-002 峰值吞吐量要求
- 测试期间失败率应小于 5%（突发场景容许略高失败率）

### 后置检查

- 记录实际峰值吞吐量到测试报告

### 元数据

- **优先级**: High
- **类别**: performance
- **已自动化**: Yes
- **测试引用**: tests/test_nfr02_throughput.py, locustfile.py
- **Test Type**: Real

---

### 用例编号

ST-FUNC-027-001

### 关联需求

NFR-002 (Query Throughput) — 系统吞吐量可测量

### 测试目标

验证负载测试工具能够正确执行并报告吞吐量指标

### 前置条件

- locust 已安装（pip install locust）
- Python 环境可运行 locustfile.py

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 验证 locustfile.py 存在 | 文件存在于项目根目录 |
| 2 | 验证 run_throughput_test.py 存在 | 脚本存在于 scripts/ 目录 |
| 3 | 执行 `python scripts/run_throughput_test.py --help` | 输出帮助信息，包含 --sustained 和 --burst 参数 |
| 4 | 执行 `python scripts/run_throughput_test.py --validate --rps 1200 --duration 600` | 返回 exit code 0（1200 > 1000 阈值） |
| 5 | 执行 `python scripts/run_throughput_test.py --validate --rps 800 --duration 600` | 返回 exit code 1（800 < 1000 阈值） |

### 验证点

- 脚本接受正确的参数
- 阈值验证逻辑正确（>= 1000 返回成功，< 1000 返回失败）

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_nfr02_throughput.py
- **Test Type**: Mock（使用子进程测试脚本接口）

---

### 用例编号

ST-BNDRY-027-001

### 关联需求

NFR-002 (Query Throughput) — 边界条件验证

### 测试目标

验证阈值边界情况下的正确行为

### 前置条件

- run_throughput_test.py 脚本可执行

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 执行 `python scripts/run_throughput_test.py --validate --rps 1000 --duration 600` | 返回 exit code 0（正好等于阈值） |
| 2 | 执行 `python scripts/run_throughput_test.py --validate --rps 999 --duration 600` | 返回 exit code 1（低于阈值） |
| 3 | 执行 `python scripts/run_throughput_test.py --validate --peak-rps 2000` | 返回 exit code 0（正好等于峰值阈值） |
| 4 | 执行 `python scripts/run_throughput_test.py --validate --peak-rps 1999` | 返回 exit code 1（低于峰值阈值） |

### 验证点

- 1000 RPS 边界值通过
- 999 RPS 边界值失败
- 2000 峰值边界值通过
- 1999 峰值边界值失败

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_nfr02_throughput.py::TestThroughputThresholdValidation
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-PERF-027-001 | NFR-002 | Given k6 load test targeting 1000 QPS for 10 minutes, when measuring throughput, then sustained >= 1000 QPS | locustfile.py + run_throughput_test.py | Real | PENDING |
| ST-PERF-027-002 | NFR-002 | Given k6 load test targeting 2000 QPS burst, when measuring peak, then peak >= 2000 QPS achieved | locustfile.py + run_throughput_test.py | Real | PENDING |
| ST-FUNC-027-001 | NFR-002 | 负载测试工具可执行并正确报告吞吐量 | tests/test_nfr02_throughput.py | Mock | PASS |
| ST-BNDRY-027-001 | NFR-002 | 阈值边界验证 | tests/test_nfr02_throughput.py | Mock | PASS |

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

### NFR-002 测试特殊性

NFR-002 (Query Throughput) 是非功能性需求，需要在真实运行环境下进行负载测试：

1. **PERF 类测试需要真实服务**：
   - ST-PERF-027-001 和 ST-PERF-027-002 需要所有后端服务运行（PostgreSQL, Redis, Qdrant, Elasticsearch）
   - 需要实际的查询数据已索引

2. **测试执行方式**：
   - 使用 locust 进行负载测试
   - 使用 scripts/run_throughput_test.py 进行阈值验证

3. **CI/CD 环境**：
   - 在完整 CI 环境中运行完整负载测试（10 分钟持续 + 30 秒突发）
   - 在开发/验证阶段可使用缩短参数（如 -t 60s）

### 执行命令

```bash
# 完整持续负载测试（10分钟）
python scripts/run_throughput_test.py --host http://localhost:8000 --sustained

# 完整突发负载测试
python scripts/run_throughput_test.py --host http://localhost:8000 --burst

# 验证已收集的指标
python scripts/run_throughput_test.py --validate --rps 1200 --duration 600
python scripts/run_throughput_test.py --validate --peak-rps 2500
```
