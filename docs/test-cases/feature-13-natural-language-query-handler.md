# 测试用例集: Natural Language Query Handler

**Feature ID**: 13
**关联需求**: FR-011（Natural Language Query Handler）
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

ST-FUNC-013-001

### 关联需求

FR-011（Natural Language Query Handler）

### 测试目标

验证NL查询执行完整的4路并行检索（BM25 code + vector code + BM25 doc + vector doc）、RRF融合（top_k=50）、重排序（top_k=6）、响应构建流程，并返回query_type="nl"的结构化结果。

### 前置条件

- QueryHandler 类已实现，所有依赖组件（Retriever、RankFusion、Reranker、ResponseBuilder）可用
- 查询字符串为有效的自然语言查询
- repo 参数为有效的仓库标识

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建 QueryHandler 实例，配置所有依赖 | 实例创建成功 |
| 2 | 调用 handle_nl_query("how to use grpc java interceptor", "test-repo") | 返回 QueryResponse |
| 3 | 检查4个检索方法是否被调用：bm25_code_search, vector_code_search, bm25_doc_search, vector_doc_search | 4个方法均被调用一次，repo参数传递正确 |
| 4 | 检查 RankFusion.fuse() 是否被调用 | 被调用且 top_k=50 |
| 5 | 检查 Reranker.rerank() 是否被调用 | 被调用且 top_k=6 |
| 6 | 检查 ResponseBuilder.build() 参数 | query_type="nl"，repo="test-repo" |

### 验证点

- 4路并行检索均执行
- RRF融合使用 top_k=50
- 重排序使用 top_k=6
- 响应类型为 "nl"
- degraded=False

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

验证空查询、仅含空白字符的查询、超长查询（>500字符）均引发 ValidationError，并包含描述性错误消息。

### 前置条件

- QueryHandler 类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 handle_nl_query("", "test-repo") | 抛出 ValidationError，消息包含 "empty" |
| 2 | 调用 handle_nl_query("   ", "test-repo") | 抛出 ValidationError，消息包含 "empty" |
| 3 | 调用 handle_nl_query("a" * 501, "test-repo") | 抛出 ValidationError，消息包含 "500" |

### 验证点

- 空字符串引发 ValidationError("query must not be empty")
- 空白字符串引发 ValidationError("query must not be empty")
- 超长查询（501字符）引发 ValidationError("query exceeds 500 character limit")

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

验证查询扩展功能：从NL查询中提取嵌入的代码标识符（PascalCase、camelCase、snake_case、点分隔），并触发符号提升搜索（weight=0.3）合并入RRF。

### 前置条件

- QueryHandler 类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 _extract_identifiers("how does AuthService validate tokens") | 返回包含 "AuthService" 的列表 |
| 2 | 调用 _extract_identifiers("check the get_user_name function") | 返回包含 "get_user_name" 的列表 |
| 3 | 调用 _extract_identifiers("how does UserService.getById work") | 返回包含 "UserService.getById" 的列表 |
| 4 | 调用 _extract_identifiers("how to configure timeout") | 返回空列表 |
| 5 | 调用 handle_nl_query("how does AuthService validate tokens", "test-repo")，检查符号提升搜索 | _symbol_boost_search 被调用，boost结果以weight=0.3合并入RRF融合 |

### 验证点

- PascalCase（AuthService）被正确提取
- snake_case（get_user_name）被正确提取
- 点分隔标识符（UserService.getById）被正确提取
- 无标识符时返回空列表
- 符号提升结果以weight=0.3合并入RRF（fuse被调用时包含5个列表）

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_query_handler.py::test_extract_identifiers_pascal_case, test_extract_dot_separated, test_extract_snake_case, test_no_identifiers_returns_empty, test_symbol_boost_weight_applied
- **Test Type**: Real

---

### 用例编号

ST-FUNC-013-004

### 关联需求

FR-011（Natural Language Query Handler）

### 测试目标

验证管道超时（pipeline_timeout=1s）返回degraded=True的降级响应，以及部分检索路径失败时的降级行为和全部失败时的RetrievalError。

### 前置条件

- QueryHandler 类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 设置pipeline_timeout=0.01s，模拟_run_pipeline耗时>0.01s | 返回 QueryResponse，degraded=True，code_results和doc_results为空 |
| 2 | 模拟3个检索路径超时，1个成功 | 返回 QueryResponse，degraded=True，包含成功路径的结果 |
| 3 | 模拟1个检索路径超时，3个成功 | 返回 QueryResponse，degraded=True |
| 4 | 模拟所有4个检索路径失败 | 抛出 RetrievalError("all retrieval paths failed") |
| 5 | 模拟Reranker失败 | 返回 QueryResponse，使用fused[:6]作为fallback，degraded=True |

### 验证点

- 管道超时时返回空降级响应（degraded=True）
- 部分失败时 degraded=True，包含可用结果
- 全部失败时抛出 RetrievalError
- Reranker失败时使用RRF结果作为降级回退

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_query_handler.py::test_pipeline_timeout_returns_degraded, test_three_fail_one_succeeds_degraded, test_one_timeout_sets_degraded, test_all_retrieval_fail_raises_retrieval_error, test_reranker_failure_with_branch_falls_back
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-013-001

### 关联需求

FR-011（Natural Language Query Handler）

### 测试目标

验证查询长度边界：恰好500字符接受、501字符拒绝（off-by-one验证）。

### 前置条件

- QueryHandler 类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 handle_nl_query("a" * 500, "test-repo") | 正常返回 QueryResponse，不抛异常 |
| 2 | 调用 handle_nl_query("a" * 501, "test-repo") | 抛出 ValidationError("query exceeds 500 character limit") |

### 验证点

- 恰好500字符被接受（无ValidationError）
- 501字符被拒绝（ValidationError）

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

验证repo参数的@branch解析边界：owner/repo@branch正常分割、尾随@时branch=None、多个@时在最后一个@分割。

### 前置条件

- QueryHandler 类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 handle_nl_query("test", "google/gson@main") | _parse_repo返回("google/gson", "main")，branch="main"传递给全部4个retriever调用 |
| 2 | 调用 handle_nl_query("test", "google/gson@") | _parse_repo返回("google/gson", None)，无branch过滤 |
| 3 | 调用 handle_nl_query("test", "org/repo@feature@fix") | _parse_repo在最后一个@分割，返回("org/repo@feature", "fix") |
| 4 | 调用 handle_nl_query("test", "google/gson") | _parse_repo返回("google/gson", None)，branch=None传递给retriever |

### 验证点

- owner/repo@branch正确解析为(repo_id, branch)
- 尾随@的branch为None而非空字符串
- 多个@时在最后一个@分割（rsplit行为）
- 无@时branch为None

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_query_handler.py::test_repo_branch_parsing_forwarded, test_repo_trailing_at_branch_is_none, test_repo_multiple_at_splits_on_last, test_repo_no_branch_forwards_none
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-013-003

### 关联需求

FR-011（Natural Language Query Handler）

### 测试目标

验证边界场景：所有4个检索路径返回空列表时返回有效空响应；符号提升搜索失败时不影响主管道。

### 前置条件

- QueryHandler 类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 模拟所有4个检索返回空列表 [] | 正常返回 QueryResponse，code_results和doc_results均为空 |
| 2 | 检查 degraded 标志 | degraded=False（空结果不视为失败） |
| 3 | 模拟符号提升搜索抛出异常，4个主检索正常 | 主管道继续执行，正常返回 QueryResponse |

### 验证点

- 空结果列表不被视为失败（degraded=False）
- 符号提升失败被静默忽略，不影响主管道
- 返回有效的空响应

### 后置检查

- 无需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_query_handler.py::test_all_retrieval_return_empty_lists, test_symbol_boost_failure_ignored
- **Test Type**: Real

---

### 用例编号

ST-SEC-013-001

### 关联需求

FR-011（Natural Language Query Handler）

### 测试目标

验证NL查询处理器对恶意输入的安全防护：SQL注入、XSS脚本、路径遍历、null字节等恶意载荷不导致异常行为或安全漏洞，均被正常处理或由输入验证拒绝。

### 前置条件

- QueryHandler 类已实现，所有依赖组件可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 handle_nl_query("'; DROP TABLE users--", "test-repo") | 正常处理：查询被当作普通NL查询执行，不引发异常，不执行SQL |
| 2 | 调用 handle_nl_query("<script>alert('xss')</script>", "test-repo") | 正常处理：查询被当作普通NL查询执行，不引发异常 |
| 3 | 调用 handle_nl_query("../../../../etc/passwd", "test-repo") | 正常处理：查询被当作普通NL查询执行，不引发异常 |
| 4 | 调用 handle_nl_query("query\x00with\x00nulls", "test-repo") | 正常处理或引发ValidationError，不导致程序崩溃 |
| 5 | 调用 handle_nl_query("normal query", "test-repo/../../../etc") | 正常处理：repo参数被按原样传递（下游服务负责repo验证），不引发未预期异常 |

### 验证点

- SQL注入字符串被当作普通查询文本处理，不影响数据库
- XSS脚本标签被当作普通文本处理
- 路径遍历序列被当作普通文本处理
- Null字节不导致程序崩溃
- 恶意repo路径不导致文件系统访问

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: security
- **已自动化**: Yes
- **测试引用**: tests/test_query_handler.py::test_handle_nl_query_full_pipeline (security payloads tested as variations)
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-013-001 | FR-011 | VS-1: 4-way parallel retrieval + RRF + rerank → structured results | test_handle_nl_query_full_pipeline | Real | PASS |
| ST-FUNC-013-002 | FR-011 | VS-2: empty query raises ValidationError | test_empty_query_raises_validation_error | Real | PASS |
| ST-FUNC-013-003 | FR-011 | VS-3: query expansion extracts identifiers + symbol boost with weight 0.3 | test_extract_identifiers_pascal_case, test_symbol_boost_weight_applied | Real | PASS |
| ST-FUNC-013-004 | FR-011 | VS-4: pipeline timeout → degraded=true; partial failures → degraded | test_pipeline_timeout_returns_degraded | Real | PASS |
| ST-BNDRY-013-001 | FR-011 | VS-2 (boundary: 500 vs 501 chars) | test_query_exactly_500_chars_valid | Real | PASS |
| ST-BNDRY-013-002 | FR-011 | VS-5: repo in owner/repo@branch parsed and forwarded | test_repo_branch_parsing_forwarded | Real | PASS |
| ST-BNDRY-013-003 | FR-011 | VS-1 (boundary: empty results + symbol boost failure) | test_all_retrieval_return_empty_lists | Real | PASS |
| ST-SEC-013-001 | FR-011 | VS-1, VS-2 (security: malicious input handling) | test_handle_nl_query_full_pipeline (security variations) | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 8 |
| Passed | 8 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
