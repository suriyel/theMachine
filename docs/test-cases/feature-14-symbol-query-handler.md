# 测试用例集: Symbol Query Handler

**Feature ID**: 14
**关联需求**: FR-012（Symbol Query Handler）
**日期**: 2026-03-24
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 4 |
| boundary | 3 |
| security | 1 |
| **合计** | **8** |

---

### 用例编号

ST-FUNC-014-001

### 关联需求

FR-012（Symbol Query Handler）

### 测试目标

验证 detect_query_type() 对包含点号、双冒号、井号、camelCase、PascalCase、snake_case 的查询正确返回 "symbol"。

### 前置条件

- QueryHandler 类已实例化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 detect_query_type("UserService.getById") | 返回 "symbol" |
| 2 | 调用 detect_query_type("std::vector") | 返回 "symbol" |
| 3 | 调用 detect_query_type("Array#map") | 返回 "symbol" |
| 4 | 调用 detect_query_type("getUserName") (camelCase) | 返回 "symbol" |
| 5 | 调用 detect_query_type("UserService") (PascalCase) | 返回 "symbol" |
| 6 | 调用 detect_query_type("get_user_name") (snake_case) | 返回 "symbol" |

### 验证点

- 点号分隔的标识符被分类为 symbol
- 双冒号分隔的标识符被分类为 symbol
- 井号分隔的标识符被分类为 symbol
- camelCase、PascalCase、snake_case 模式被分类为 symbol

### 后置检查

- 无副作用，纯函数调用

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_symbol_query_handler.py::TestDetectQueryType::test_detect_query_type[A1-dot], [A3-doublecolon], [A7-hash], [A4-camelCase], [A5-PascalCase], [A6-snake_case]
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-014-002

### 关联需求

FR-012（Symbol Query Handler）

### 测试目标

验证 handle_symbol_query() 对 ES term 查询有结果时，返回 query_type="symbol" 的 QueryResponse，且 ES term 查询在 symbol.raw 字段上执行。

### 前置条件

- QueryHandler 已配置 Retriever、Reranker、ResponseBuilder
- ES 中存在包含目标 symbol 的 code chunks

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 handle_symbol_query("std::vector", "repo1") | 方法执行成功 |
| 2 | 检查 ES term 查询是否在 symbol.raw 字段上执行 | term 查询包含 {"term": {"symbol.raw": "std::vector"}} |
| 3 | 检查 reranker.rerank() 是否被调用 | 调用参数 top_k=20（design §4.2.5: combined code+doc candidates） |
| 4 | 检查 response_builder.build() 的 query_type 参数 | query_type="symbol" |
| 5 | 检查返回的 QueryResponse | query="std::vector", query_type="symbol" |

### 验证点

- ES term 查询在 symbol.raw 字段上执行精确匹配
- Reranker 对合并后的 code+doc 候选集进行重排序，top_k=20
- ResponseBuilder 使用 query_type="symbol" 构建响应

### 后置检查

- 无状态变更

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_symbol_query_handler.py::TestHandleSymbolQuery::test_a2_term_hits_returns_symbol_response_with_docs
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-014-003

### 关联需求

FR-012（Symbol Query Handler）

### 测试目标

验证 ES term 查询无结果时执行 fuzzy fallback；fuzzy 也无结果时执行 NL pipeline fallback。

### 前置条件

- QueryHandler 已配置所有依赖组件
- ES 中不存在目标 symbol 的 code chunks

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 handle_symbol_query("vectr", "repo1")，ES term 返回 0 结果 | 继续执行 fuzzy 查询 |
| 2 | ES fuzzy 查询（fuzziness=AUTO）返回匹配结果 | fuzzy 结果被传递给 reranker |
| 3 | 检查 reranker 和 builder 是否被调用 | query_type="symbol" |
| 4 | 调用 handle_symbol_query("nonExistentSymbol", "repo1")，term 和 fuzzy 均返回 0 | fallback 到 handle_nl_query |
| 5 | 检查返回值 | 返回 NL pipeline 的 QueryResponse |

### 验证点

- term 返回 0 结果时执行 fuzzy 查询
- fuzzy 使用 fuzziness=AUTO 参数
- term 和 fuzzy 均返回 0 时 fallback 到 NL pipeline
- NL fallback 返回有效的 QueryResponse

### 后置检查

- 无状态变更

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_symbol_query_handler.py::TestHandleSymbolQuery::test_b2_fuzzy_fallback, tests/test_symbol_query_handler.py::TestHandleSymbolQuery::test_b1_nl_fallback
- **Test Type**: Mock

---

### 用例编号

ST-FUNC-014-004

### 关联需求

FR-012（Symbol Query Handler）

### 测试目标

验证 ES 连接失败时 RetrievalError 被正确传播；Reranker 失败时降级使用原始 chunks[:6]。

### 前置条件

- QueryHandler 已配置 Retriever
- ES 不可达或 Reranker 模型异常

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 模拟 Retriever._execute_search 抛出 RetrievalError | 异常被设置 |
| 2 | 调用 handle_symbol_query("MyClass", "repo1") | 抛出 RetrievalError |
| 3 | 检查异常消息 | 包含 "Elasticsearch search failed" |
| 4 | 模拟 term 查询返回 8 hits，reranker.rerank 抛出 Exception("model error") | 降级路径触发 |
| 5 | 调用 handle_symbol_query("MyClass", "repo1") | 返回有效 QueryResponse，build 参数为 chunks[:6] |

### 验证点

- RetrievalError 从 Retriever 传播到 handle_symbol_query 调用方
- 异常不被静默吞噬
- Reranker 失败时降级为 chunks[:6]，仍返回有效响应

### 后置检查

- 无状态变更

### 元数据

- **优先级**: Medium
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_symbol_query_handler.py::TestSymbolQueryErrorPropagation::test_d1_es_error_propagates, tests/test_symbol_query_handler.py::TestSymbolQueryErrorPropagation::test_b4_reranker_failure_uses_raw_chunks
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-014-001

### 关联需求

FR-012（Symbol Query Handler）

### 测试目标

验证超过 200 字符的 symbol 查询触发 ValidationError，恰好 200 字符的查询被接受。

### 前置条件

- QueryHandler 已实例化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 handle_symbol_query("a" * 201, "repo1") | 抛出 ValidationError |
| 2 | 检查异常消息 | 包含 "200 character" |
| 3 | 调用 handle_symbol_query("a" * 200, "repo1") | 不抛出 ValidationError（正常执行） |

### 验证点

- 201 字符 → ValidationError
- 200 字符 → 接受（无 off-by-one 错误）

### 后置检查

- 无状态变更

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_symbol_query_handler.py::TestSymbolQueryValidation::test_c1_exceeds_200_chars, tests/test_symbol_query_handler.py::TestSymbolQueryValidation::test_c4_exactly_200_chars_no_error
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-014-002

### 关联需求

FR-012（Symbol Query Handler）

### 测试目标

验证空字符串和纯空白字符串触发 ValidationError。

### 前置条件

- QueryHandler 已实例化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 handle_symbol_query("", "repo1") | 抛出 ValidationError |
| 2 | 检查异常消息 | 包含 "must not be empty" |
| 3 | 调用 handle_symbol_query("   ", "repo1") | 抛出 ValidationError |
| 4 | 检查异常消息 | 包含 "must not be empty" |

### 验证点

- 空字符串 → ValidationError
- 纯空白字符串 → ValidationError

### 后置检查

- 无状态变更

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_symbol_query_handler.py::TestSymbolQueryValidation::test_c2_empty_query, tests/test_symbol_query_handler.py::TestSymbolQueryValidation::test_c3_whitespace_only
- **Test Type**: Mock

---

### 用例编号

ST-BNDRY-014-003

### 关联需求

FR-012（Symbol Query Handler）

### 测试目标

验证 detect_query_type 的边界分类：单词无模式 → NL，带空格且含点号 → NL（空格优先），owner/repo@branch 的 branch 解析。

### 前置条件

- QueryHandler 已实例化

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 detect_query_type("hello") (单个小写单词) | 返回 "nl" |
| 2 | 调用 detect_query_type("CONSTANT") (全大写无下划线) | 返回 "nl" |
| 3 | 调用 detect_query_type("call user.save with retry") (有空格和点号) | 返回 "nl" |
| 4 | 调用 detect_query_type("a.b") (最小点分隔) | 返回 "symbol" |
| 5 | 调用 detect_query_type("aB") (最小 camelCase) | 返回 "symbol" |
| 6 | 调用 detect_query_type("a_b") (最小 snake_case) | 返回 "symbol" |
| 7 | 调用 handle_symbol_query("MyClass", "owner/repo@main")，检查 repo_id 过滤 | ES 查询 repo_id 过滤为 "owner/repo"（branch 被剥离） |

### 验证点

- 单个无模式单词不被误分类为 symbol
- 全大写无下划线不被误分类为 symbol
- 包含空格的查询即使含点号也分类为 NL（空格检查优先）
- 最小模式输入被正确分类为 symbol
- owner/repo@branch 格式中 branch 被正确解析并剥离

### 后置检查

- 无副作用

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_symbol_query_handler.py::TestDetectQueryType::test_detect_query_type[C8-single-word], [C9-all-caps], [A8b-spaces-with-dot], [C5-minimal-dot], [C6-minimal-camelCase], [C7-minimal-snake]; tests/test_symbol_query_handler.py::TestSymbolQueryBranchParsing::test_a8_branch_parsed_and_repo_filter_applied
- **Test Type**: Mock

---

### 用例编号

ST-SEC-014-001

### 关联需求

FR-012（Symbol Query Handler）

### 测试目标

验证 symbol 查询输入的安全边界：注入攻击字符串被安全处理，不会导致 ES 查询注入或系统异常。

### 前置条件

- QueryHandler 已配置所有依赖组件
- ES mock 正常响应

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 handle_symbol_query 传入包含 SQL 注入的查询: `"'; DROP TABLE--"` (含空格，18 字符) | detect_query_type 分类为 "nl"（因含空格），进入 NL 路径，不会直接拼接到 ES term 查询 |
| 2 | 调用 handle_symbol_query 传入路径遍历查询: `"../../../../etc/passwd"` (含 `/`，22 字符，无空格) | 查询被传递给 ES term 查询，ES 返回 0 结果（无匹配），不会产生文件系统访问 |
| 3 | 调用 handle_symbol_query 传入 null 字节查询: `"symbol\x00inject"` (含 null，13 字符) | 查询被安全传递，不会截断或导致未定义行为，返回正常结果或空结果 |
| 4 | 调用 handle_symbol_query 传入 200 字符的重复 XSS payload: `"<script>" * 25` (200 字符) | 通过长度校验（= 200），XSS payload 被视为普通文本传递给 ES，不会被执行 |
| 5 | 调用 handle_symbol_query 传入超过 200 字符的恶意 payload | 触发 ValidationError（200 字符限制阻止超长注入） |

### 验证点

- 含空格的注入字符串被 detect_query_type 分类为 NL，不会走 ES term 精确匹配路径
- 路径遍历和 null 字节不会导致文件系统访问或未定义行为
- XSS payload 被视为普通文本，不会在响应中被执行
- 200 字符限制作为输入长度安全门控有效防止超长恶意输入

### 后置检查

- 无状态变更
- 无异常日志（除 ValidationError 外）

### 元数据

- **优先级**: Medium
- **类别**: security
- **已自动化**: Yes
- **测试引用**: tests/test_symbol_query_handler.py::TestSymbolQuerySecurity::test_sec1_sql_injection_in_query, test_sec2_path_traversal_in_query, test_sec3_null_byte_in_query, test_sec4_xss_payload_rejected_by_length, test_sec5_short_xss_handled_safely
- **Test Type**: Mock

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-014-001 | FR-012 | VS-1: detect_query_type classifies dot notation as 'symbol' | test_detect_query_type[A1-dot,...] | Mock | PASS |
| ST-FUNC-014-002 | FR-012 | VS-2: handle_symbol_query ES term query on symbol.raw returns results | test_a2_term_hits_returns_symbol_response_with_docs | Mock | PASS |
| ST-FUNC-014-003 | FR-012 | VS-3: non-existent symbol falls back to NL pipeline | test_b1_nl_fallback, test_b2_fuzzy_fallback | Mock | PASS |
| ST-FUNC-014-004 | FR-012 | VS-2: ES error propagation and reranker degradation | test_d1_es_error_propagates, test_b4_reranker_failure | Mock | PASS |
| ST-BNDRY-014-001 | FR-012 | VS-4: symbol query exceeding 200 chars raises ValidationError | test_c1_exceeds_200_chars, test_c4_exactly_200_chars | Mock | PASS |
| ST-BNDRY-014-002 | FR-012 | VS-4: empty/whitespace query raises ValidationError | test_c2_empty_query, test_c3_whitespace_only | Mock | PASS |
| ST-BNDRY-014-003 | FR-012 | VS-1,VS-5: boundary detection heuristic + branch parsing | test_detect_query_type[C8,C9,...], test_a8_branch_parsed | Mock | PASS |
| ST-SEC-014-001 | FR-012 | VS-4: injection/malicious input safely handled by length limit and type detection | TestSymbolQuerySecurity::test_sec1-sec5 | Mock | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 0 |
| Passed | 0 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Feature #14 introduces no new external dependencies — pure computation (detect_query_type) and ES delegation reusing Feature #8 infrastructure. All test cases use Mock type as the feature's observable interface is an internal Python API, not an HTTP endpoint.
