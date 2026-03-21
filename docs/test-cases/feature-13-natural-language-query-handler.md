# 测试用例集: Natural Language Query Handler

**Feature ID**: 13
**关联需求**: FR-011（Natural Language Query Handler）
**日期**: 2026-03-21
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 4 |
| boundary | 3 |
| **合计** | **7** |

---

### 用例编号

ST-FUNC-013-001

### 关联需求

FR-011（Natural Language Query Handler）

### 测试目标

验证NL查询执行完整的4路并行检索、RRF融合、重排序、响应构建流程。

### 前置条件

- QueryHandler 类已实现，所有依赖组件（Retriever、RankFusion、Reranker、ResponseBuilder）可用
- 查询字符串为有效的自然语言查询

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 QueryHandler 实例 | 实例创建成功 |
| 2 | 调用 handle_nl_query("how to use grpc java interceptor", "test-repo") | 返回 QueryResponse |
| 3 | 检查4个检索方法是否被调用 | bm25_code, vector_code, bm25_doc, vector_doc 均被调用 |
| 4 | 检查 fuse() 是否被调用 | 被调用且 top_k=50 |
| 5 | 检查 rerank() 是否被调用 | 被调用且 top_k=6 |
| 6 | 检查 build() 是否被调用 | 被调用且 query_type="nl" |

### 验证点

- 4路并行检索均执行
- RRF融合使用 top_k=50
- 重排序使用 top_k=6
- 响应类型为 "nl"

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_query_handler.py::test_handle_nl_query_full_pipeline
- **Test Type**: Real

---

### 用例编号

ST-FUNC-013-002

### 关联需求

FR-011（Natural Language Query Handler）

### 测试目标

验证空查询或仅含空白字符的查询引发 ValidationError。

### 前置条件

- QueryHandler 类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 handle_nl_query("", "test-repo") | 抛出 ValidationError，消息包含 "empty" |
| 2 | 调用 handle_nl_query("   ", "test-repo") | 抛出 ValidationError，消息包含 "empty" |
| 3 | 调用 handle_nl_query("a" * 501, "test-repo") | 抛出 ValidationError，消息包含 "500" |

### 验证点

- 空字符串、空白字符串、超长查询均被正确验证并拒绝

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_query_handler.py::test_empty_query_raises_validation_error, test_whitespace_query_raises_validation_error, test_query_exceeds_500_chars_raises
- **Test Type**: Real

---

### 用例编号

ST-FUNC-013-003

### 关联需求

FR-011（Natural Language Query Handler）

### 测试目标

验证查询扩展功能：从NL查询中提取嵌入的代码标识符并触发符号提升搜索。

### 前置条件

- QueryHandler 类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 _extract_identifiers("how does AuthService validate tokens") | 返回包含 "AuthService" 的列表 |
| 2 | 调用 _extract_identifiers("check the get_user_name function") | 返回包含 "get_user_name" 的列表 |
| 3 | 调用 _extract_identifiers("how does UserService.getById work") | 返回包含 "UserService.getById" 的列表 |
| 4 | 调用 _extract_identifiers("how to configure timeout") | 返回空列表 |

### 验证点

- PascalCase、snake_case、点分隔标识符均被正确提取
- 无标识符时返回空列表

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_query_handler.py::test_extract_identifiers_pascal_case, test_extract_snake_case, test_extract_dot_separated, test_no_identifiers_returns_empty
- **Test Type**: Real

---

### 用例编号

ST-FUNC-013-004

### 关联需求

FR-011（Natural Language Query Handler）

### 测试目标

验证管道超时或部分检索失败时返回降级响应（degraded=True）。

### 前置条件

- QueryHandler 类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 模拟3个检索路径超时，1个成功 | 返回 QueryResponse，degraded=True |
| 2 | 模拟1个检索路径超时，3个成功 | 返回 QueryResponse，degraded=True |
| 3 | 模拟所有4个检索路径失败 | 抛出 RetrievalError |

### 验证点

- 部分失败时 degraded=True
- 全部失败时抛出 RetrievalError

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_query_handler.py::test_three_fail_one_succeeds_degraded, test_one_timeout_sets_degraded, test_all_retrieval_fail_raises_retrieval_error
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-013-001

### 关联需求

FR-011（Natural Language Query Handler）

### 测试目标

验证查询长度边界：500字符恰好接受、501字符拒绝。

### 前置条件

- QueryHandler 类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 handle_nl_query("a" * 500, "test-repo") | 正常返回，不抛异常 |
| 2 | 调用 handle_nl_query("a" * 501, "test-repo") | 抛出 ValidationError |

### 验证点

- 恰好500字符接受
- 501字符拒绝

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_query_handler.py::test_query_exactly_500_chars_valid, test_query_exceeds_500_chars_raises
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-013-002

### 关联需求

FR-011（Natural Language Query Handler）

### 测试目标

验证所有4个检索路径返回空列表时，返回空响应而非错误。

### 前置条件

- QueryHandler 类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 模拟所有4个检索返回空列表 | 正常返回 QueryResponse |
| 2 | 检查 code_results 和 doc_results | 均为空列表 |

### 验证点

- 空结果不引发异常
- 返回有效的空响应

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_query_handler.py::test_all_retrieval_return_empty_lists
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-013-003

### 关联需求

FR-011（Natural Language Query Handler）

### 测试目标

验证符号提升搜索失败时不影响主管道。

### 前置条件

- QueryHandler 类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 模拟符号提升搜索抛出异常 | 主管道继续正常执行 |
| 2 | 检查响应是否返回 | 正常返回 QueryResponse |

### 验证点

- 符号提升失败被静默忽略
- 主管道不受影响

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_query_handler.py::test_symbol_boost_failure_ignored
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-013-001 | FR-011 | VS-1: 4-way parallel retrieval + RRF + rerank | test_handle_nl_query_full_pipeline | Real | PASS |
| ST-FUNC-013-002 | FR-011 | VS-2: empty query raises ValidationError | test_empty_query_raises_validation_error | Real | PASS |
| ST-FUNC-013-003 | FR-011 | VS-3: query expansion extracts identifiers | test_extract_identifiers_pascal_case | Real | PASS |
| ST-FUNC-013-004 | FR-011 | VS-4: pipeline timeout → degraded=true | test_three_fail_one_succeeds_degraded | Real | PASS |
| ST-BNDRY-013-001 | FR-011 | VS-2 (boundary: 500 vs 501 chars) | test_query_exactly_500_chars_valid | Real | PASS |
| ST-BNDRY-013-002 | FR-011 | VS-1 (boundary: empty results) | test_all_retrieval_return_empty_lists | Real | PASS |
| ST-BNDRY-013-003 | FR-011 | VS-3 (boundary: symbol boost failure) | test_symbol_boost_failure_ignored | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 7 |
| Passed | 7 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
