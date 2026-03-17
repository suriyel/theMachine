# 测试用例集: NFR-004: Single Repository Size

**Feature ID**: 29
**关联需求**: NFR-004 (Single Repository Size)
**日期**: 2026-03-18
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

---

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 1 |
| boundary | 2 |
| performance | 1 |
| **合计** | **4** |

---

### 用例编号

ST-PERF-029-001

### 关联需求

NFR-004 (Single Repository Size) — Index repositories up to 1GB without failure

### 测试目标

验证系统能够成功索引 1GB 仓库，所有 chunks 正确索引

### 前置条件

- PostgreSQL、Redis、Qdrant、Elasticsearch 服务已启动
- 1GB 测试仓库已准备
- 索引服务（Celery worker）已运行

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 准备 1GB 测试仓库 | 仓库可用 |
| 2 | 调用索引 API 触发索引任务 | 任务已排队，返回 job_id |
| 3 | 监控索引任务直到完成 | 任务状态变为 completed |
| 4 | 查询索引统计，验证 chunks 总数 | chunks > 0 |

### 验证点

- 索引任务成功完成，状态为 completed
- chunks 数量大于 0，表示内容已被索引

### 后置检查

- 记录实际索引的 chunks 数量

### 元数据

- **优先级**: High
- **类别**: performance
- **已自动化**: Yes
- **测试引用**: scripts/run_repo_size_test.py
- **Test Type**: Real（需要真实服务运行）

---

### 用例编号

ST-FUNC-029-001

### 关联需求

NFR-004 (Single Repository Size) — 仓库大小验证脚本可执行

### 测试目标

验证仓库大小测试脚本能够正确执行并报告阈值验证结果

### 前置条件

- run_repo_size_test.py 脚本存在

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 执行 `python scripts/run_repo_size_test.py --help` | 输出帮助信息 |
| 2 | 执行 `python scripts/run_repo_size_test.py --validate --size 500 --chunks 10000` | 返回 exit code 0（通过） |
| 3 | 执行 `python scripts/run_repo_size_test.py --validate --size 2048 --chunks 40000` | 返回 exit code 1（超过 1GB 限制） |

### 验证点

- 脚本接受正确参数
- 阈值验证逻辑正确

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_nfr04_repo_size.py
- **Test Type**: Mock（使用子进程测试脚本接口）

---

### 用例编号

ST-BNDRY-029-001

### 关联需求

NFR-004 (Single Repository Size) — 边界条件验证

### 测试目标

验证仓库大小边界情况下的正确行为

### 前置条件

- run_repo_size_test.py 脚本可执行

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 执行 `python scripts/run_repo_size_test.py --validate --size 0 --chunks 0` | 返回 exit code 1（大小为 0） |
| 2 | 执行 `python scripts/run_repo_size_test.py --validate --size -100 --chunks 0` | 返回 exit code 1（负数大小） |
| 3 | 执行 `python scripts/run_repo_size_test.py --validate --size 1024 --chunks 0` | 返回 exit code 1（chunks 为 0） |

### 验证点

- 大小为 0 失败
- 负数大小失败
- chunks 为 0 失败

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_nfr04_repo_size.py::TestRepoSizeThresholdValidation
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-029-002

### 关联需求

NFR-004 (Single Repository Size) — 大文件处理边界验证

### 测试目标

验证大文件处理在边界情况下的正确行为

### 前置条件

- run_repo_size_test.py 脚本可执行

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 执行 `python scripts/run_repo_size_test.py --test-large-file --file-size 50 --file-processed` | 返回 exit code 0（成功处理） |
| 2 | 执行 `python scripts/run_repo_size_test.py --test-large-file --file-size 50` | 返回 exit code 1（未处理） |
| 3 | 执行 `python scripts/run_repo_size_test.py --test-large-file --file-size 0` | 返回 exit code 1（大小为 0） |

### 验证点

- 成功处理大文件通过
- 未处理大文件失败
- 大小为 0 失败

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_nfr04_repo_size.py::TestLargeFileHandling
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-PERF-029-001 | NFR-004 | Given 1GB repository, when indexing job runs, then job completes successfully with all chunks indexed | scripts/run_repo_size_test.py | Real | PENDING |
| ST-FUNC-029-001 | NFR-004 | 仓库大小验证脚本可执行 | tests/test_nfr04_repo_size.py | Mock | PASS |
| ST-BNDRY-029-001 | NFR-004 | 边界条件验证 | tests/test_nfr04_repo_size.py | Mock | PASS |
| ST-BNDRY-029-002 | NFR-004 | 大文件处理边界验证 | tests/test_nfr04_repo_size.py | Mock | PASS |

---

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 1 |
| Passed | 0 |
| Failed | 0 |
| Pending | 1 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.

---

## 说明

### NFR-004 测试特殊性

NFR-004 (Single Repository Size) 是非功能性需求，需要在真实运行环境下进行仓库大小测试：

1. **PERF 类测试需要真实服务**：
   - ST-PERF-029-001 需要所有后端服务运行（PostgreSQL, Redis, Qdrant, Elasticsearch）
   - 需要实际的 1GB 测试仓库数据
   - 需要 Celery worker 处理索引任务

2. **测试执行方式**：
   - 使用脚本准备 1GB 测试仓库
   - 触发索引任务并监控完成
   - 验证 chunks 数量

3. **CI/CD 环境**：
   - 在完整 CI 环境中运行完整大小测试
   - 在开发/验证阶段可使用 --validate 参数快速验证

### 执行命令

```bash
# 完整大小测试（需要服务运行）
python scripts/run_repo_size_test.py --host http://localhost:8000

# 验证已收集的指标
python scripts/run_repo_size_test.py --validate --size 500 --chunks 10000
python scripts/run_repo_size_test.py --validate --size 1024 --chunks 20000
```
