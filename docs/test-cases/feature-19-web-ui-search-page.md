# 测试用例集: Web UI Search Page

**Feature ID**: 19
**关联需求**: FR-017
**日期**: 2026-03-22
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 3 |
| boundary | 1 |
| ui | 2 |
| accessibility | 1 |
| **合计** | **7** |

---

### 用例编号

ST-FUNC-019-001

### 关联需求

FR-017（Web UI Search Page — 搜索页面加载）

### 测试目标

验证 GET / 返回包含搜索输入框、仓库过滤下拉列表、语言过滤复选框的完整搜索页面，且应用 Developer Dark 主题样式。

### 前置条件

- Web UI 服务已启动并可访问
- 数据库连接已配置（或优雅降级）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page` 访问 `/` | 页面返回 HTTP 200，HTML 内容加载完成 |
| 2 | `take_snapshot` 获取页面 DOM | 页面包含 `<input>` 搜索输入框 |
| 3 | `evaluate_script` 检查 `document.querySelector('select')` | 存在仓库过滤 `<select>` 下拉列表 |
| 4 | `evaluate_script` 检查 `document.querySelectorAll('input[type="checkbox"]').length` | 存在至少 1 个语言过滤复选框 |
| 5 | `evaluate_script` 检查页面 CSS 中是否包含暗色主题背景色 `#0d1117` | 页面样式包含 Developer Dark 主题色 |
| 6 | `list_console_messages` 检查控制台 | 无 JavaScript 错误 |

### 验证点

- 页面 HTTP 状态码为 200
- 搜索输入框、仓库下拉列表、语言复选框均存在
- Developer Dark 主题色 `#0d1117` 在页面样式中
- 无控制台错误

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui.py::test_search_page_renders_form, tests/test_web_ui.py::test_ucd_theme_tokens, tests/test_web_ui.py::test_htmx_integration
- **Test Type**: Real

---

### 用例编号

ST-FUNC-019-002

### 关联需求

FR-017（Web UI Search Page — 搜索返回结果展示）

### 测试目标

验证提交搜索查询后，页面正确显示带有语法高亮代码片段、仓库名称、文件路径、符号名称和相关性评分的结果列表。

### 前置条件

- Web UI 服务已启动
- QueryHandler 已配置并可正常响应查询
- 索引中存在可命中的数据

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page` 访问 `/` | 搜索页面加载成功 |
| 2 | `fill` 在搜索输入框中输入 `timeout` | 输入框显示 "timeout" |
| 3 | `click` 点击搜索按钮或提交表单 | 请求发送至 `/search?q=timeout` |
| 4 | `take_snapshot` 获取结果页面 DOM | 页面包含结果列表 |
| 5 | `evaluate_script` 检查结果中是否包含文件路径（如 `src/main.py`） | 文件路径显示在结果卡片中 |
| 6 | `evaluate_script` 检查结果中是否包含符号名称（如 `timeout_handler`） | 符号名称显示在结果中 |
| 7 | `evaluate_script` 检查结果中是否包含相关性评分 | 评分数值（如 `0.95`）可见 |
| 8 | `evaluate_script` 检查代码片段是否含 `<span` 语法高亮标签 | 代码片段使用 Pygments 语法高亮渲染 |
| 9 | `list_console_messages` 检查控制台 | 无 JavaScript 错误 |

### 验证点

- 搜索结果列表非空
- 每条结果包含文件路径、符号名称、相关性评分
- 代码片段使用语法高亮（包含带颜色的 `<span>` 标签）
- 无控制台错误或样式异常

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui.py::test_search_results_with_hits, tests/test_highlighter.py::test_syntax_highlight_python_tokens
- **Test Type**: Real

---

### 用例编号

ST-FUNC-019-003

### 关联需求

FR-017（Web UI Search Page — 无结果空状态展示）

### 测试目标

验证当搜索查询无匹配结果时，页面显示 "No results found" 空状态消息，且符合 Developer Dark 主题样式。

### 前置条件

- Web UI 服务已启动
- QueryHandler 已配置

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page` 访问 `/` | 搜索页面加载成功 |
| 2 | `fill` 在搜索输入框中输入 `xyznonexistent999` | 输入框显示查询文本 |
| 3 | `click` 点击搜索按钮 | 请求发送至服务端 |
| 4 | `take_snapshot` 获取结果页面 DOM | 页面不包含结果卡片 |
| 5 | `evaluate_script` 检查页面文本是否包含 "No results found" | 空状态消息 "No results found" 可见 |
| 6 | `list_console_messages` 检查控制台 | 无 JavaScript 错误 |

### 验证点

- 搜索结果区域为空（无结果卡片）
- 页面显示 "No results found" 空状态消息
- 无控制台错误或服务端异常

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui.py::test_no_results_empty_state
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-019-001

### 关联需求

FR-017（Web UI Search Page — 空查询验证）

### 测试目标

验证提交空查询（空字符串或仅空格）时，页面显示验证消息 "Please enter a search query"，且不触发服务端搜索请求。

### 前置条件

- Web UI 服务已启动

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page` 访问 `/` | 搜索页面加载成功 |
| 2 | `fill` 搜索输入框留空（空字符串） | 输入框为空 |
| 3 | `click` 点击搜索按钮提交空查询 | 请求 `/search?q=` 发送 |
| 4 | `take_snapshot` 获取页面 DOM | 页面显示验证消息 |
| 5 | `evaluate_script` 检查页面文本是否包含 "Please enter a search query" | 验证消息 "Please enter a search query" 可见 |
| 6 | `navigate_page` 访问 `/search?q=%20%20`（仅空格查询） | 页面加载 |
| 7 | `evaluate_script` 检查页面文本是否包含 "Please enter a search query" | 仅空格查询同样显示验证消息 |

### 验证点

- 空字符串查询显示 "Please enter a search query"
- 仅空格查询同样显示 "Please enter a search query"
- 不显示服务端错误或空白结果页

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui.py::test_empty_query_validation, tests/test_web_ui.py::test_whitespace_query_validation
- **Test Type**: Real

---

### 用例编号

ST-UI-019-001

### 关联需求

FR-017（Web UI Search Page — 搜索交互与结果展示完整流程）

### 测试目标

验证端到端搜索交互流程：页面加载 → 输入查询 → 选择仓库过滤 → 选择语言过滤 → 提交搜索 → 结果展示（含语法高亮），确认 Developer Dark 主题、htmx 动态交互和 symbol 查询分发均正常工作。

### 前置条件

- Web UI 服务已启动，浏览器 DevTools 可连接
- QueryHandler 已配置（支持 NL 和 Symbol 查询）
- 索引中存在可命中的数据

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page` 访问 `/` | 页面加载成功，Developer Dark 主题背景色 `#0d1117` 应用 |
| 2 | `take_snapshot` 截取初始页面 | 搜索输入框、仓库下拉列表、语言复选框均可见 |
| 3 | `evaluate_script` 检查 htmx 是否加载：`typeof htmx !== 'undefined'` | htmx 库已加载，返回 `true` |
| 4 | `fill` 在搜索输入框中输入 `timeout` | 输入框值为 "timeout" |
| 5 | `click` 点击搜索按钮 | NL 查询请求发送，结果页面加载 |
| 6 | `take_snapshot` 截取结果页面 | 结果列表显示，包含文件路径 `src/main.py`、符号 `timeout_handler`、评分 `0.95` |
| 7 | `evaluate_script` 检查结果代码片段中是否包含 `color:` 样式 | 语法高亮应用成功（Pygments 渲染） |
| 8 | `navigate_page` 访问 `/` 重新加载搜索页面 | 页面重新加载成功 |
| 9 | `fill` 在搜索输入框中输入 `myFunc` | 输入框值为 "myFunc" |
| 10 | `click` 点击搜索按钮 | Symbol 查询分发至 `handle_symbol_query`，结果展示 |
| 11 | `take_snapshot` 截取 Symbol 搜索结果 | 结果包含符号 `myFunc` |
| 12 | `list_console_messages` 检查全流程控制台 | 无 JavaScript 错误或样式异常 |

### 验证点

- 页面加载包含 Developer Dark 主题色
- htmx 库已加载并生效（存在 `hx-get` 或 `hx-post` 属性）
- NL 查询正确返回结果，包含文件路径、符号名称、相关性评分
- 代码片段含语法高亮（`<span>` + `color:` 样式）
- Symbol 查询正确分发至 `handle_symbol_query`
- 全流程无控制台错误

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: ui
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui.py::test_search_results_with_hits, tests/test_web_ui.py::test_symbol_query_dispatch, tests/test_web_ui.py::test_search_results_repo_filter, tests/test_web_ui.py::test_search_results_language_filter, tests/test_web_ui.py::test_htmx_integration, tests/test_web_ui.py::test_ucd_theme_tokens
- **Test Type**: Real

---

### 用例编号

ST-UI-019-002

### 关联需求

FR-017（Web UI Search Page — 仓库注册与分支选择器）

### 测试目标

验证仓库注册表单包含分支选择器下拉框：输入仓库 URL 后通过 Branch Listing API 动态加载可用分支列表，默认选中默认分支，提交后仓库按所选分支注册成功。同时验证错误场景（空 URL、重复注册）的用户提示。

### 前置条件

- Web UI 服务已启动，浏览器 DevTools 可连接
- GitCloner 已配置（`list_remote_branches_by_url` 可用）
- 数据库 session_factory 已配置

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page` 访问 `/` | 页面加载成功，仓库注册表单可见 |
| 2 | `take_snapshot` 截取注册表单区域 | 表单包含 URL 输入框和分支选择器 |
| 3 | `fill` 在 URL 输入框中输入 `https://github.com/org/repo` | URL 输入框显示仓库地址 |
| 4 | `evaluate_script` 触发分支列表加载（通过 htmx 或手动请求 `/branches?repo_id=...`） | 分支列表 API 请求发送 |
| 5 | `navigate_page` 访问 `/branches?repo_id=https://github.com/org/repo` 验证分支列表端点 | 返回 HTML `<option>` 元素，包含 `main` 和 `develop` |
| 6 | `evaluate_script` 检查返回 HTML 中是否包含 `selected` 属性 | 默认分支（`main`）标记为 `selected` |
| 7 | `navigate_page` 返回 `/` | 页面重新加载 |
| 8 | `fill` 在 URL 输入框输入 `https://github.com/org/repo` | URL 已填入 |
| 9 | `fill` 在分支选择器中选择 `develop` | 分支选择器值为 "develop" |
| 10 | `click` 点击注册/提交按钮 | POST `/register` 请求发送，参数包含 `branch=develop` |
| 11 | `take_snapshot` 截取注册结果 | 页面显示注册成功信息 |
| 12 | `list_console_messages` 检查控制台 | 无 JavaScript 错误，分支下拉框无空状态 |

### 验证点

- 注册表单包含 URL 输入框和分支选择器下拉框
- `/branches` 端点返回 `<option>` 元素，包含 `main` 和 `develop`
- 默认分支标记为 `selected`
- 提交注册时 `branch` 参数正确传递
- 无控制台错误、无空分支下拉框

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: ui
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui.py::test_list_branches, tests/test_web_ui.py::test_register_repo_with_branch, tests/test_web_ui.py::test_branches_no_main_defaults_to_first, tests/test_web_ui.py::test_register_empty_url, tests/test_web_ui.py::test_register_duplicate_url
- **Test Type**: Real

---

### 用例编号

ST-A11Y-019-001

### 关联需求

FR-017（Web UI Search Page — 无障碍访问：键盘导航、焦点状态、ARIA 属性）

### 测试目标

验证搜索页面满足基本无障碍访问要求：所有交互元素可通过键盘 Tab 键导航，焦点状态可见，表单元素具有 ARIA 标签或 `<label>` 关联，搜索结果区域具有 ARIA `role` 或 `aria-live` 属性以支持屏幕阅读器。

### 前置条件

- Web UI 服务已启动，浏览器 DevTools 可连接

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page` 访问 `/` | 搜索页面加载成功 |
| 2 | `press_key` 按 Tab 键 | 焦点移至搜索输入框 |
| 3 | `evaluate_script` 检查 `document.activeElement.tagName` 和 `document.activeElement.type` | 焦点在搜索输入框上（`INPUT` 类型 `text` 或 `search`） |
| 4 | `press_key` 继续按 Tab 键遍历所有交互元素 | 焦点依次移至仓库下拉列表、语言复选框、搜索按钮等 |
| 5 | `evaluate_script` 检查搜索输入框是否具有 `aria-label` 或关联 `<label>` | 搜索输入框具有无障碍标签（`aria-label` 或 `<label for="...">` 匹配） |
| 6 | `evaluate_script` 检查仓库 `<select>` 是否具有 `aria-label` 或关联 `<label>` | 仓库下拉列表具有无障碍标签 |
| 7 | `evaluate_script` 检查语言复选框是否具有 `aria-label` 或关联 `<label>` | 每个复选框有关联标签 |
| 8 | `evaluate_script` 检查搜索按钮 `type="submit"` 是否可通过 Enter 键触发 | 搜索按钮可通过键盘回车提交 |
| 9 | `evaluate_script` 检查结果区域是否具有 `role` 或 `aria-live` 属性 | 结果区域具有 `role="region"` 或 `aria-live="polite"` 以通知屏幕阅读器 |
| 10 | `take_snapshot` 截取焦点状态可视确认 | 焦点状态有可见的视觉指示（outline 或 border 变化） |

### 验证点

- 所有交互元素（输入框、下拉列表、复选框、按钮）可通过 Tab 键依次导航
- 焦点状态具有可见的视觉指示
- 表单元素具有 `aria-label` 或关联 `<label>` 无障碍标签
- 搜索按钮可通过 Enter 键触发表单提交
- 结果区域具有 ARIA 属性以支持屏幕阅读器动态内容通知

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: accessibility
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui.py::test_search_page_renders_form, tests/test_web_ui.py::test_htmx_integration
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-019-001 | FR-017 | VS-1: 搜索输入框、仓库过滤、语言过滤、Developer Dark 主题渲染 | test_search_page_renders_form, test_ucd_theme_tokens, test_htmx_integration | Real | PASS |
| ST-FUNC-019-002 | FR-017 | VS-1: 搜索结果含语法高亮代码、仓库名、文件路径、符号名、评分 | test_search_results_with_hits, test_syntax_highlight_python_tokens | Real | PASS |
| ST-FUNC-019-003 | FR-017 | VS-3: 无结果时显示 "No results found" 空状态 | test_no_results_empty_state | Real | PASS |
| ST-BNDRY-019-001 | FR-017 | VS-2: 空查询显示 "Please enter a search query" 验证消息 | test_empty_query_validation, test_whitespace_query_validation | Real | PASS |
| ST-UI-019-001 | FR-017 | VS-1: 完整搜索交互流程含主题、htmx、NL 和 Symbol 查询 | test_search_results_with_hits, test_symbol_query_dispatch, test_search_results_repo_filter, test_search_results_language_filter | Real | PASS |
| ST-UI-019-002 | FR-017 | VS-4: 仓库注册表单含分支选择器、Branch Listing API 加载、默认分支选中 | test_list_branches, test_register_repo_with_branch, test_branches_no_main_defaults_to_first | Real | PASS |
| ST-A11Y-019-001 | FR-017 | VS-1: 键盘导航、焦点状态、ARIA 标签、屏幕阅读器支持 | test_search_page_renders_form, test_htmx_integration | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 7 |
| Passed | 7 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
