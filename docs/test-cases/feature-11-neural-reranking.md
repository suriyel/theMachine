# 测试用例集: Neural Reranking

**Feature ID**: 11
**关联需求**: FR-009（Neural Reranking）, NFR-001（Query Latency）
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

ST-FUNC-011-001

### 关联需求

FR-009（Neural Reranking）

### 测试目标

验证50个融合候选项经过cross-encoder重排后返回top-6结果，每个结果包含cross-encoder相关性分数

### 前置条件

- Reranker模块已安装（sentence-transformers可用）
- 50个ScoredChunk候选项已通过RRF融合生成

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Reranker实例（模拟CrossEncoder模型） | 实例创建成功，_model不为None |
| 2 | 生成50个ScoredChunk候选项，每个有不同content和chunk_id | 50个候选项列表 |
| 3 | 调用rerank(query="spring webclient timeout", candidates=50个候选项, top_k=6) | 返回列表长度为6 |
| 4 | 验证返回结果的score字段 | 每个结果的score是cross-encoder分数（非原始融合分数） |
| 5 | 验证返回顺序 | 结果按cross-encoder分数降序排列 |

### 验证点

- 返回列表长度 == 6
- 每个结果的score字段已被cross-encoder分数替换
- 结果按score降序排列
- chunk_id与最高cross-encoder分数对应的候选项匹配

### 后置检查

- 无副作用：原始候选项列表未被修改

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_reranker.py::test_rerank_50_candidates_returns_top6_rescored
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-011-002

### 关联需求

FR-009（Neural Reranking）

### 测试目标

验证模型加载失败时，rerank回退到融合排序并记录降级警告

### 前置条件

- CrossEncoder模型无法加载（模拟OOM或加载错误）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Reranker实例，模拟CrossEncoder构造函数抛出RuntimeError | 实例创建成功（不抛出异常），_model为None |
| 2 | 准备10个ScoredChunk候选项 | 候选项列表就绪 |
| 3 | 调用rerank(query="test", candidates=10个候选项, top_k=6) | 返回列表长度为6 |
| 4 | 验证返回顺序 | 保持原始融合排序（输入顺序） |
| 5 | 验证返回结果的score字段 | 保留原始融合分数（未被cross-encoder分数替换） |
| 6 | 验证日志输出 | 包含"not loaded"降级警告 |

### 验证点

- 返回列表长度 == 6
- 结果保持输入顺序（chunk-0到chunk-5）
- 原始分数未被修改
- 日志中包含降级警告消息

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_reranker.py::test_rerank_model_load_failure_fallback
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-011-003

### 关联需求

FR-009（Neural Reranking）

### 测试目标

验证模型推理过程中发生运行时错误时，rerank回退到融合排序并记录警告

### 前置条件

- CrossEncoder模型已加载成功
- model.predict()在调用时抛出RuntimeError

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Reranker实例，模型加载成功 | 实例创建成功，_model不为None |
| 2 | 配置mock使predict()抛出RuntimeError("CUDA OOM") | mock配置完成 |
| 3 | 准备5个ScoredChunk候选项 | 候选项列表就绪 |
| 4 | 调用rerank(query="test", candidates=5个候选项, top_k=3) | 返回列表长度为3 |
| 5 | 验证返回结果 | 保持原始融合排序，原始分数保留 |
| 6 | 验证日志 | 包含fallback/failed相关警告 |

### 验证点

- 返回列表长度 == 3
- 结果保持输入顺序（chunk-0, chunk-1, chunk-2）
- 原始分数保留
- 日志包含推理失败警告

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_reranker.py::test_rerank_inference_failure_fallback
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-011-001

### 关联需求

FR-009（Neural Reranking）

### 测试目标

验证候选项数量少于top_k时，返回所有可用候选项不报错

### 前置条件

- Reranker模型已加载
- 候选项数量 < top_k

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Reranker实例 | 实例创建成功 |
| 2 | 准备2个ScoredChunk候选项 | 候选项列表就绪 |
| 3 | 调用rerank(query="test", candidates=2个候选项, top_k=6) | 返回列表长度为2（不是6） |
| 4 | 验证所有候选项都被包含 | 两个候选项都在返回结果中 |
| 5 | 验证分数 | 分数已被cross-encoder分数替换 |

### 验证点

- 返回长度 == min(top_k, len(candidates)) == 2
- 无异常抛出
- 结果按cross-encoder分数降序排列

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_reranker.py::test_rerank_fewer_than_topk
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-011-002

### 关联需求

FR-009（Neural Reranking）

### 测试目标

验证空候选项列表时返回空列表不报错

### 前置条件

- Reranker模型已加载
- 候选项列表为空

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Reranker实例 | 实例创建成功 |
| 2 | 调用rerank(query="test", candidates=[], top_k=6) | 返回空列表[] |
| 3 | 验证返回类型 | 返回值是list类型 |

### 验证点

- 返回值 == []
- 无异常抛出
- 模型predict未被调用（无必要）

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_reranker.py::test_rerank_empty_candidates
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-011-001 | FR-009 | Given 50 fused candidates and a query, when rerank() runs, then it returns top-6 candidates re-scored by the cross-encoder with relevance scores | test_rerank_50_candidates_returns_top6_rescored | Mock | PASS |
| ST-FUNC-011-002 | FR-009 | Given a reranker model failure (OOM, load error), when rerank() runs, then it falls back to the fusion-ranked order and logs a degradation warning | test_rerank_model_load_failure_fallback | Mock | PASS |
| ST-FUNC-011-003 | FR-009 | Given a reranker model failure (OOM, load error), when rerank() runs, then it falls back to the fusion-ranked order and logs a degradation warning | test_rerank_inference_failure_fallback | Mock | PASS |
| ST-BNDRY-011-001 | FR-009 | Given fewer than 3 candidates, when rerank() runs, then it returns all available candidates without error | test_rerank_fewer_than_topk | Mock | PASS |
| ST-BNDRY-011-002 | FR-009 | Given fewer than 3 candidates, when rerank() runs, then it returns all available candidates without error | test_rerank_empty_candidates | Mock | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 0 |
| Passed | 0 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> This feature is pure computation with no external I/O — all test cases use mocked CrossEncoder model.
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
