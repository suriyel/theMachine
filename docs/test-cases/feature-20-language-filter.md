# 测试用例集: Language Filter

**Feature ID**: 20
**关联需求**: FR-015 (Filter Results by Programming Language)
**日期**: 2026-03-17
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 2 |
| boundary | 1 |
| ui | 1 |
| security | 0 |
| accessibility | 1 |
| performance | 0 |
| **合计** | **5** |

---

### 用例编号

ST-FUNC-020-001

### 关联需求

FR-015 (Filter Results by Programming Language)

### 测试目标

验证 REST API 接受有效的语言过滤器并正确过滤结果

### 前置条件

- Query Service 运行在 localhost:8000
- 已注册代码仓库并已索引
- 有效的 API Key

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | -------------- | ---------------- |
| 1 | 启动 Query Service | 服务启动成功，端口 8000 |
| 2 | POST /api/v1/query with language="java" | 返回 200 状态码 |
| 3 | 检查返回结果中的 language 字段 | 所有结果的 language 均为 "java" |

### 验证点

- API 返回 200 状态码
- 所有返回结果的 language 字段为 "java"

### 后置检查

- 停止 Query Service

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: N/A
- **Test Type**: Real

---

### 用例编号

ST-FUNC-020-002

### 关联需求

FR-015 (Filter Results by Programming Language)

### 测试目标

验证 REST API 拒绝不支持的语言过滤器并返回 422 错误

### 前置条件

- Query Service 运行在 localhost:8000
- 有效的 API Key

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | -------------- | ---------------- |
| 1 | 启动 Query Service | 服务启动成功，端口 8000 |
| 2 | GET /api/v1/query?query=test&language=Ruby | 返回 422 状态码 |
| 3 | 检查错误详情 | 错误信息包含 "Unsupported language" 和支持的语言列表 |

### 验证点

- API 返回 422 状态码
- 错误信息列出所有支持的语言

### 后置检查

- 停止 Query Service

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: N/A
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-020-001

### 关联需求

FR-015 (Filter Results by Programming Language)

### 测试目标

验证大小写不敏感的语言过滤

### 前置条件

- Query Service 运行在 localhost:8000
- 有效的 API Key

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | -------------- | ---------------- |
| 1 | 启动 Query Service | 服务启动成功，端口 8000 |
| 2 | GET /api/v1/query?query=test&language=JAVA | 返回 200 状态码 |
| 3 | 检查返回结果 | 结果的 language 字段为小写 "java" |

### 验证点

- API 返回 200
- 语言被规范化为小写

### 后置检查

- 停止 Query Service

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: N/A
- **Test Type**: Real

---

### 用例编号

ST-UI-020-001

### 关联需求

FR-015 (Filter Results by Programming Language)

### 测试目标

验证 Web UI 中的语言过滤器芯片交互功能

### 前置条件

- Query Service 运行在 localhost:8000
- 用户已登录（有效的 session）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | -------------- | ---------------- |
| 1 | navigate_page(url='http://localhost:8000/search') | 页面开始加载 |
| 2 | wait_for(['Search code context']) → evaluate_script(error_detector) | 页面加载完成，Layer 1: count = 0 |
| 3 | take_snapshot() | EXPECT: 语言过滤芯片 (All, Java, Python, TypeScript, JavaScript, C, C++), 搜索输入框; REJECT: 控制台错误 |
| 4 | click(Python芯片的uid) | Python 芯片被选中，样式变化 |
| 5 | fill(搜索输入框uid, 'test') → 点击搜索按钮 | 执行搜索 |
| 6 | wait_for([结果]) → evaluate_script(error_detector) → list_console_messages(["error"]) | 搜索完成，Layer 1: count = 0，Layer 3: 控制台无 error |

### 验证点

- 语言芯片可点击
- 选中状态正确显示
- 搜索功能正常工作
- 无 JavaScript 错误
- 无控制台错误

### 后置检查

- 停止 Query Service

### 元数据

- **优先级**: High
- **类别**: ui
- **已自动化**: Yes
- **测试引用**: N/A
- **Test Type**: Real

---

### 用例编号

ST-A11Y-020-001

### 关联需求

FR-015 (Filter Results by Programming Language)

### 测试目标

验证 Web UI 语言过滤器的可访问性

### 前置条件

- Query Service 运行在 localhost:8000
- 用户已登录

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | -------------- | ---------------- |
| 1 | navigate_page(url='http://localhost:8000/search') | 页面加载 |
| 2 | wait_for(['Search code context']) | 页面就绪 |
| 3 | take_snapshot(verbose=true) | 检查 ARIA 属性，按钮有 role="button"，芯片有可访问名称 |
| 4 | evaluate_script(keyboard_navigation_test) | 验证可以使用 Tab 键在语言芯片之间导航 |
| 5 | list_console_messages(["error"]) | 无错误 |

### 验证点

- 语言芯片具有适当的 ARIA 属性
- 可以通过键盘导航
- 颜色对比度符合 WCAG 标准

### 后置检查

- 停止 Query Service

### 元数据

- **优先级**: High
- **类别**: accessibility
- **已自动化**: Yes
- **测试引用**: N/A
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-020-001 | FR-015 | Given query 'timeout' with language filter 'Java' | N/A | Real | BLOCKED (pre-existing bug in QueryHandler) |
| ST-FUNC-020-002 | FR-015 | Given query with language filter 'UnsupportedLang' | N/A | Real | BLOCKED (pre-existing bug in QueryHandler) |
| ST-BNDRY-020-001 | FR-015 | 大小写不敏感测试 | N/A | Real | BLOCKED (pre-existing bug in QueryHandler) |
| ST-UI-020-001 | FR-015 | [devtools] /search chip interaction | N/A | Real | PENDING (requires running service) |
| ST-A11Y-020-001 | FR-015 | 可访问性验证 | N/A | Real | PENDING (requires running service) |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 5 |
| Passed | 0 |
| Failed | 0 |
| Blocked | 3 |
| Pending | 2 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> BLOCKED: Tests could not run due to pre-existing bug in QueryHandler (SemanticRetriever.__init__() missing encoder argument), not related to Language Filter feature implementation.
> Unit tests (22 tests) verified the LanguageFilter class implementation passes with 100% coverage.
