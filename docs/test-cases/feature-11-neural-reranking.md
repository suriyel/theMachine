# 测试用例集: Neural Reranking (FR-011)

**Feature ID**: 11
**关联需求**: FR-011 (Rerank Results)
**日期**: 2026-03-15
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

ST-FUNC-011-001

### 关联需求

FR-011 (Rerank Results)

### 测试目标

验证当候选列表包含2个或更多项目时，NeuralReranker使用交叉编码器模型对候选项进行相关性评分，并按分数降序重新排序

### 前置条件

- NeuralReranker已初始化，模型已加载
- 已安装sentence-transformers和torch依赖
- 可用的测试候选列表（至少2个项目）

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 准备测试数据：创建包含3个候选项的列表，每个候选项有不同的初始score | 候选列表包含3个项目 |
| 2 | 创建一个mock CrossEncoder模型，返回特定的分数 [0.9, 0.3, 0.7] | Mock模型配置完成 |
| 3 | 调用NeuralReranker.rerank(query, candidates) | 方法返回排序后的列表 |
| 4 | 验证模型被调用 | predict方法被调用1次 |
| 5 | 验证返回顺序按新的相关性分数降序排列 | 第一个候选项chunk_id应为"1"（得分0.9），第二个为"3"（得分0.7），第三个为"2"（得分0.3） |

### 验证点

- 模型predict方法被调用，传入query-document对
- 返回的候选项按相关性分数降序排列
- 候选项的score属性被更新为相关性分数

### 后置检查

- 无需清理（测试数据为内存对象）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_neural_reranker.py::test_reranker_reorders_candidates_by_score
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-011-002

### 关联需求

FR-011 (Rerank Results)

### 测试目标

验证当候选列表少于2个项目时，NeuralReranker直接返回原始顺序而不调用模型（直通行为）

### 前置条件

- NeuralReranker已初始化
- 候选列表包含0个或1个项目

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 准备测试数据：创建包含1个候选项的列表 | 候选列表包含1个项目 |
| 2 | 调用NeuralReranker.rerank(query, candidates) | 方法返回原始列表 |
| 3 | 验证模型未被调用 | 模型predict方法未被调用 |
| 4 | 验证返回顺序与输入顺序相同 | 返回的列表中唯一候选项的chunk_id为"1" |

### 验证点

- 对于单个候选项，模型不被调用（直通行为）
- 返回的候选项保持原始顺序
- 原始的score值保持不变

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_neural_reranker.py::test_reranker_passes_through_for_single_item
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-011-001

### 关联需求

FR-011 (Rerank Results)

### 测试目标

验证当候选列表为空时，NeuralReranker返回空列表而不抛出异常

### 前置条件

- NeuralReranker已初始化

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 准备测试数据：创建空候选列表 | 候选列表为空 |
| 2 | 调用NeuralReranker.rerank(query, candidates) | 返回空列表 |
| 3 | 验证返回结果为空列表 | 结果为[] |

### 验证点

- 空输入返回空输出，无异常抛出
- 方法正确处理边界情况

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_neural_reranker.py::test_reranker_handles_empty_list
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-011-002

### 关联需求

FR-011 (Rerank Results)

### 测试目标

验证当模型加载失败时，NeuralReranker抛出RerankerError异常

### 前置条件

- CrossEncoder初始化会失败（例如无效的模型名称）

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 使用无效的模型名称初始化NeuralReranker | 抛出RerankerError异常 |
| 2 | 验证异常消息包含"Failed to load reranker model" | 异常消息正确 |

### 验证点

- 异常类型为RerankerError
- 异常消息描述了模型加载失败的原因

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_neural_reranker.py::test_reranker_raises_on_model_load_failure
- **Test Type**: Mock

---

### 用例编号

ST-PERF-011-001

### 关联需求

FR-011 (Rerank Results)

### 测试目标

验证在真实评估数据集上应用reranking后，nDCG@3指标达到0.7或以上

### 前置条件

- 已加载bge-reranker-v2-m3模型
- 存在包含query和relevant documents的评估数据集

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 准备评估数据集：包含多个查询和对应的相关文档 | 数据集包含查询-文档对 |
| 2 | 对每个查询执行完整的检索管道：keyword + semantic + fusion + rerank | 获得每个查询的候选列表 |
| 3 | 计算每个查询的nDCG@3指标 | 获得nDCG@3分数 |
| 4 | 计算所有查询的平均nDCG@3 | 获得平均分数 |

### 验证点

- 平均nDCG@3 >= 0.7

### 后置检查

- 无需清理（评估数据集为只读）

### 元数据

- **优先级**: High
- **类别**: performance
- **已自动化**: No (需要外部评估数据集)
- **测试引用**: N/A
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-011-001 | FR-011 | verification_step[0] | test_reranker_reorders_candidates_by_score | Mock | PASS |
| ST-FUNC-011-002 | FR-011 | verification_step[1] | test_reranker_passes_through_for_single_item | Mock | PASS |
| ST-BNDRY-011-001 | FR-011 | verification_step[1] | test_reranker_handles_empty_list | Mock | PASS |
| ST-BNDRY-011-002 | FR-011 | verification_step[1] | test_reranker_raises_on_model_load_failure | Mock | PASS |
| ST-PERF-011-001 | FR-011 | verification_step[2] | N/A | Real | PENDING |

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

## 备注

1. **测试覆盖**: 功能测试覆盖了验证步骤1和2的核心逻辑，边界测试覆盖了异常处理和边界情况
2. **性能测试**: ST-PERF-011-001 需要外部评估数据集才能执行，属于NFR验证，当前标记为PENDING
3. **Mock vs Real**: 由于NeuralReranker依赖外部模型（bge-reranker-v2-m3），大部分测试使用Mock进行，真实的端到端测试需要实际的模型推理环境
4. **模型推理**: 真实场景需要下载和加载大型模型文件，在CI环境中难以自动化执行
