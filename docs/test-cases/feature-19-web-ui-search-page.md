# 测试用例集: Web UI Search Page

**Feature ID**: 19
**关联需求**: FR-017, FR-018
**日期**: 2026-03-25
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 4 |
| boundary | 2 |
| ui | 4 |
| security | 1 |
| accessibility | 1 |
| **合计** | **12** |

---

### 用例编号

ST-FUNC-019-001

### 关联需求

FR-017（Web UI Search Page — 搜索页面加载及表单元素）

### 测试目标

验证 GET / 返回包含搜索输入框、仓库过滤下拉列表（仅显示 status=indexed 仓库，无 "all repos" 选项）、6 种语言过滤复选框的完整搜索页面，且应用 Developer Dark 主题。

### 前置条件

- query-api 服务已启动，监听 localhost:8000
- 数据库中存在至少 1 个 status=indexed 的仓库

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/')` | 页面开始加载 |
| 2 | `wait_for(['Search'])` → `evaluate_script(expression="document.readyState")` | 页面加载完成，readyState = "complete" |
| 3 | `evaluate_script(expression="(() => { const errs = []; if(!document.querySelector('input.search-input')) errs.push('no search input'); if(!document.querySelector('select.repo-dropdown')) errs.push('no repo dropdown'); const checks = document.querySelectorAll('input[type=checkbox][name=languages]'); if(checks.length < 6) errs.push('expected 6 language checkboxes, got '+checks.length); return {errors: errs, count: errs.length}; })()")` | Layer 1: count = 0 — 搜索输入框、仓库下拉列表、6 个语言复选框均存在 |
| 4 | `take_snapshot()` | EXPECT: 页面标题 "Code Context Retrieval"，搜索输入框，"Search" 按钮，仓库 `<select>` 下拉（含 "Select a repository" 占位），6 个语言复选框 (python, java, javascript, typescript, c, c++)，Developer Dark 背景 (#0d1117); REJECT: "All repositories" 选项, 空白页面 |
| 5 | `evaluate_script(expression="(() => { const sel = document.querySelector('select.repo-dropdown'); const opts = Array.from(sel.options).filter(o => o.value && !o.disabled); return {indexed_repo_count: opts.length, has_all_repos: Array.from(sel.options).some(o => o.textContent.toLowerCase().includes('all repo'))}; })()")` | indexed_repo_count >= 1; has_all_repos = false — 仓库下拉仅显示 indexed 仓库，无 "all repos" 选项 |
| 6 | `evaluate_script(expression="getComputedStyle(document.body).backgroundColor")` | 背景色为 rgb(13, 17, 23) 即 #0d1117 |
| 7 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- 搜索输入框 (`input.search-input`) 存在
- 仓库下拉列表 (`select.repo-dropdown`) 存在，仅含 indexed 仓库
- 无 "All repositories" 选项（repo 选择是必填的）
- 6 个语言复选框存在
- Developer Dark 主题背景色 #0d1117 已应用
- 无控制台错误

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui.py::test_search_page_renders_form
- **Test Type**: Real

---

### 用例编号

ST-FUNC-019-002

### 关联需求

FR-017（Web UI Search Page — 搜索结果展示）

### 测试目标

验证提交搜索查询（选择仓库后）返回带有语法高亮代码片段、仓库名称、文件路径、符号名称和相关性评分的结果卡片。

### 前置条件

- query-api 服务已启动
- 数据库中存在 status=indexed 仓库
- Elasticsearch 和 Qdrant 中存在已索引数据，查询 "timeout" 可命中结果

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/')` | 搜索页面加载成功 |
| 2 | `wait_for(['Search'])` → `evaluate_script(expression="document.readyState === 'complete'")` | 页面就绪 |
| 3 | `take_snapshot()` → 确认搜索表单可见，选择仓库下拉中第一个 indexed 仓库 | EXPECT: 搜索表单存在，仓库选项可选 |
| 4 | `fill(uid, 'timeout')` 在搜索输入框填入 "timeout" → `click(uid)` 选择仓库下拉第一个选项 → `click(uid)` 点击 Search 按钮 | 搜索请求通过 htmx 发送至 `/search?q=timeout&repo=...` |
| 5 | `wait_for(['result-card'])` → `take_snapshot()` | EXPECT: 至少 1 个 `.result-card` 元素，包含 `.result-card__file-path` (文件路径), `.result-card__score` (相关性评分), `.result-card__code` (语法高亮代码); REJECT: "No results found", 空白结果区 |
| 6 | `evaluate_script(expression="(() => { const cards = document.querySelectorAll('.result-card'); const firstCard = cards[0]; return { card_count: cards.length, has_file_path: !!firstCard?.querySelector('.result-card__file-path')?.textContent, has_score: !!firstCard?.querySelector('.result-card__score')?.textContent, has_code: !!firstCard?.querySelector('.result-card__code pre'), has_highlight: firstCard?.querySelector('.result-card__code span') !== null }; })()")` | card_count >= 1, has_file_path = true, has_score = true, has_code = true, has_highlight = true |
| 7 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- 结果卡片包含文件路径、相关性评分
- 代码片段使用 Pygments 语法高亮（含 `<span>` 标签）
- 无控制台错误

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui.py::test_search_results_render
- **Test Type**: Real

---

### 用例编号

ST-FUNC-019-003

### 关联需求

FR-017（Web UI Search Page — 空查询验证）

### 测试目标

验证提交空查询时，UI 显示 "Please enter a search query" 验证消息。

### 前置条件

- query-api 服务已启动

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/')` | 搜索页面加载成功 |
| 2 | `wait_for(['Search'])` → `evaluate_script(expression="document.readyState === 'complete'")` | 页面就绪 |
| 3 | `take_snapshot()` → 确认搜索输入框为空 | EXPECT: 搜索输入框存在且值为空 |
| 4 | `click(uid)` 点击 Search 按钮（不填写查询） | htmx 请求发送至 `/search?q=` |
| 5 | `wait_for(['Please enter a search query'])` → `take_snapshot()` | EXPECT: 页面显示 "Please enter a search query" 错误消息; REJECT: 服务器错误, 空白结果, 500 状态码 |
| 6 | `evaluate_script(expression="document.querySelector('.error-message')?.textContent.includes('Please enter a search query')")` | Layer 1: 返回 true — 验证消息正确显示 |
| 7 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- 空查询返回 "Please enter a search query" 验证消息
- 消息显示在 `.error-message` 元素中
- 无服务器错误或控制台错误

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui.py::test_empty_query_validation
- **Test Type**: Real

---

### 用例编号

ST-FUNC-019-004

### 关联需求

FR-017（Web UI Search Page — 无结果空状态）

### 测试目标

验证查询无匹配结果时，UI 显示 "No results found" 空状态消息。

### 前置条件

- query-api 服务已启动
- 数据库中存在 status=indexed 仓库
- 查询 "xyznonexistent99999" 预期不会命中任何结果

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/')` | 搜索页面加载成功 |
| 2 | `wait_for(['Search'])` → `evaluate_script(expression="document.readyState === 'complete'")` | 页面就绪 |
| 3 | `fill(uid, 'xyznonexistent99999')` 在搜索输入框输入无匹配查询 → `click(uid)` 选择仓库 → `click(uid)` 点击 Search | 搜索请求发送 |
| 4 | `wait_for(['No results found'])` → `take_snapshot()` | EXPECT: 显示 "No results found" 消息，Developer Dark 空状态样式 (`.empty-state` 元素); REJECT: 错误消息, 服务器异常, 结果卡片 |
| 5 | `evaluate_script(expression="!!document.querySelector('.empty-state')")` | Layer 1: 返回 true — `.empty-state` 元素存在 |
| 6 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- "No results found" 消息显示
- 使用 `.empty-state` CSS 类（Developer Dark 空状态样式）
- 无控制台错误

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui.py::test_empty_results_message
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-019-001

### 关联需求

FR-017（Web UI Search Page — 仓库下拉必选）

### 测试目标

验证仓库下拉列表是必填的（`required` 属性），且仅显示 status=indexed 的仓库（无 "all repos" 选项）。

### 前置条件

- query-api 服务已启动
- 数据库中有 indexed 和非 indexed 仓库

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/')` | 搜索页面加载成功 |
| 2 | `wait_for(['Search'])` → `evaluate_script(expression="document.readyState === 'complete'")` | 页面就绪 |
| 3 | `evaluate_script(expression="(() => { const sel = document.querySelector('select.repo-dropdown'); return { required: sel?.required === true, has_disabled_placeholder: sel?.options[0]?.disabled === true && sel?.options[0]?.selected === true }; })()")` | required = true; has_disabled_placeholder = true — 下拉列表是必填的，默认选中的是 disabled 占位选项 |
| 4 | `take_snapshot()` | EXPECT: 仓库下拉显示 "Select a repository" 占位文本; REJECT: "All repositories" 选项 |
| 5 | `evaluate_script(expression="Array.from(document.querySelector('select.repo-dropdown').options).every(o => !o.textContent.toLowerCase().includes('all'))")` | Layer 1: 返回 true — 无 "All" 选项 |
| 6 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- `select.repo-dropdown` 有 `required` 属性
- 默认占位选项为 disabled
- 无 "All repositories" 或 "All repos" 选项
- 无控制台错误

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui.py::test_repo_dropdown_required
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-019-002

### 关联需求

FR-018（Language Filter — 语言过滤行为）

### 测试目标

验证语言过滤复选框正确传递过滤参数，且选择特定语言后搜索结果受限于该语言。

### 前置条件

- query-api 服务已启动
- 数据库中存在 status=indexed 仓库
- 索引中存在多语言数据

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/')` | 搜索页面加载成功 |
| 2 | `wait_for(['Search'])` → `evaluate_script(expression="document.readyState === 'complete'")` | 页面就绪 |
| 3 | `evaluate_script(expression="document.querySelectorAll('input[type=checkbox][name=languages]').length")` | 返回 6 — 支持 6 种语言 (python, java, javascript, typescript, c, c++) |
| 4 | `take_snapshot()` → 确认 6 个语言复选框可见 | EXPECT: python, java, javascript, typescript, c, c++ 复选框均可见且未选中 |
| 5 | `click(uid)` 勾选 python 复选框 → `fill(uid, 'timeout')` 填入查询 → `click(uid)` 选择仓库 → `click(uid)` 点击 Search | 搜索请求发送，包含 `languages=python` 参数 |
| 6 | `evaluate_script(expression="document.querySelector('input[value=python]')?.checked")` | Layer 1: 返回 true — python 复选框已勾选 |
| 7 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- 6 种语言复选框存在
- 选中的语言通过查询参数传递
- 无控制台错误

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui.py::test_language_filter_checkboxes
- **Test Type**: Real

---

### 用例编号

ST-UI-019-001

### 关联需求

FR-017（Web UI Search Page — 页面加载及 UCD 主题验证）

### 测试目标

验证搜索页面在浏览器中完整渲染，Developer Dark 主题的 UCD 色彩令牌（背景 #0d1117, 文本 #e6edf3, 主色 #58a6ff）正确应用，htmx 脚本加载。

### 前置条件

- query-api 服务已启动，监听 localhost:8000
- Chrome 浏览器可通过 DevTools 访问

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/')` | 页面开始加载 |
| 2 | `wait_for(['Code Context Retrieval'])` → `evaluate_script(expression="(() => { const errs = []; const bg = getComputedStyle(document.body).backgroundColor; if(bg !== 'rgb(13, 17, 23)') errs.push('bg color: '+bg); const header = document.querySelector('.header__title'); if(!header) errs.push('no header title'); if(header && getComputedStyle(header).color !== 'rgb(230, 237, 243)') errs.push('header text color wrong'); const btn = document.querySelector('.search-btn'); if(!btn) errs.push('no search btn'); return {errors: errs, count: errs.length}; })()")` | Layer 1: count = 0 — 背景色 #0d1117，标题文本色 #e6edf3，Search 按钮存在 |
| 3 | `take_snapshot()` | EXPECT: 页面标题 "Code Context Retrieval"，56px header 栏带 `--color-bg-secondary` (#161b22) 背景，搜索输入框 44px 高度，"Search" 蓝色按钮 (`--color-accent-primary` #58a6ff)，仓库下拉 200px 宽，语言复选框横排; REJECT: 白色背景, 默认浏览器样式, 缺少 htmx |
| 4 | `evaluate_script(expression="(() => { const scripts = Array.from(document.querySelectorAll('script')); return scripts.some(s => s.src && s.src.includes('htmx')); })()")` | 返回 true — htmx 脚本已加载 |
| 5 | `evaluate_script(expression="(() => { const searchBtn = document.querySelector('.search-btn'); const btnBg = getComputedStyle(searchBtn).backgroundColor; return { btn_bg: btnBg, is_accent_primary: btnBg === 'rgb(88, 166, 255)' }; })()")` | is_accent_primary = true — Search 按钮使用 `--color-accent-primary` (#58a6ff) |
| 6 | `evaluate_script(expression="typeof htmx !== 'undefined'")` | 返回 true — htmx 全局对象可用 |
| 7 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- body 背景色 = #0d1117 (`--color-bg-primary`)
- header 标题文本色 = #e6edf3 (`--color-text-primary`)
- Search 按钮背景色 = #58a6ff (`--color-accent-primary`)
- htmx 脚本已加载且全局对象可用
- 无控制台错误

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: ui
- **已自动化**: No
- **测试引用**: N/A (Chrome DevTools MCP manual execution)
- **Test Type**: Real

---

### 用例编号

ST-UI-019-002

### 关联需求

FR-017（Web UI Search Page — 搜索交互流程 E2E）

### 测试目标

验证完整的搜索交互流程：选择仓库 → 输入查询 → 点击 Search → 结果通过 htmx 局部更新显示，结果卡片包含语法高亮代码。

### 前置条件

- query-api 服务已启动
- 数据库中存在 status=indexed 仓库
- Elasticsearch/Qdrant 中存在可命中数据

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/')` | 页面开始加载 |
| 2 | `wait_for(['Search'])` → `evaluate_script(expression="(() => { const errs=[]; if(!document.querySelector('.search-input')) errs.push('no input'); if(!document.querySelector('.repo-dropdown')) errs.push('no dropdown'); return {errors:errs, count:errs.length}; })()")` | Layer 1: count = 0 — 搜索输入框和仓库下拉存在 |
| 3 | `take_snapshot()` → 获取仓库下拉的可用选项 | EXPECT: 仓库下拉含至少 1 个 indexed 仓库选项 |
| 4 | `click(uid)` 选择仓库下拉中第一个非 disabled 选项 → `fill(uid, 'timeout')` 在搜索输入框输入 → `click(uid)` 点击 Search 按钮 | htmx 发送 GET 请求至 `/search`，results 区域更新 |
| 5 | `wait_for(['result-card'])` → `take_snapshot()` | EXPECT: `#results` 区域包含 `.result-card` 元素，卡片带有 `--color-bg-secondary` (#161b22) 背景，文件路径链接使用 `--color-accent-primary` (#58a6ff); REJECT: 整页重新加载, 空结果 |
| 6 | `evaluate_script(expression="(() => { const card = document.querySelector('.result-card'); if(!card) return {found:false}; const fp = card.querySelector('.result-card__file-path'); const score = card.querySelector('.result-card__score'); const code = card.querySelector('.result-card__code pre'); const hasSpan = card.querySelector('.result-card__code span') !== null; return {found:true, file_path:fp?.textContent, score:score?.textContent, has_code:!!code, has_syntax_highlight:hasSpan}; })()")` | found = true, file_path 非空, score 非空, has_code = true, has_syntax_highlight = true |
| 7 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- htmx 局部更新：仅 `#results` 区域更新，非整页刷新
- 结果卡片包含文件路径、相关性评分、语法高亮代码
- 结果卡片使用 UCD 样式令牌
- 无控制台错误

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: ui
- **已自动化**: No
- **测试引用**: N/A (Chrome DevTools MCP manual execution)
- **Test Type**: Real

---

### 用例编号

ST-UI-019-003

### 关联需求

FR-017（Web UI Search Page — 仓库注册及分支选择器）

### 测试目标

验证仓库注册表单中输入 URL 后触发分支列表加载（通过 Branch Listing API），分支选择器下拉填充可用分支并默认选择 main 分支，提交后显示注册成功消息。

### 前置条件

- query-api 服务已启动
- GitCloner 配置可用（git_cloner on app.state）
- 测试用的仓库 URL 已克隆（Branch Listing API 可返回分支列表）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/')` | 页面开始加载 |
| 2 | `wait_for(['Register Repository'])` → `evaluate_script(expression="(() => { const errs=[]; if(!document.querySelector('input[name=url]')) errs.push('no url input'); if(!document.querySelector('#branch-select')) errs.push('no branch select'); if(!document.querySelector('.register-btn')) errs.push('no register btn'); return {errors:errs, count:errs.length}; })()")` | Layer 1: count = 0 — URL 输入框、分支选择器、Register 按钮均存在 |
| 3 | `take_snapshot()` | EXPECT: "Register Repository" 标题，URL 输入框 (placeholder 含 "github.com")，分支选择器（含 "Default branch" 选项），Register 按钮; REJECT: 缺少分支选择器, 缺少注册表单 |
| 4 | `fill(uid, 'https://github.com/test-org/test-repo')` 在 URL 输入框填入仓库地址 → 触发 blur 事件（htmx hx-trigger=blur） | htmx 发送 GET `/branches?repo_id=...`，#branch-select 更新 |
| 5 | `wait_for(['main'])` → `take_snapshot()` | EXPECT: 分支选择器包含从 API 返回的分支列表，"main" 分支被默认选中; REJECT: 分支下拉为空, 控制台错误 |
| 6 | `evaluate_script(expression="(() => { const sel = document.querySelector('#branch-select'); const opts = Array.from(sel.options).filter(o => o.value); return {branch_count: opts.length, selected: sel.value, has_main: opts.some(o => o.value === 'main')}; })()")` | branch_count >= 1, has_main = true (如果存在 main 分支) |
| 7 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- URL 输入框 blur 事件触发分支 API 调用
- 分支选择器填充了远程分支列表
- "main" 分支被默认选中（如果存在）
- 无控制台错误

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: ui
- **已自动化**: No
- **测试引用**: N/A (Chrome DevTools MCP manual execution)
- **Test Type**: Real

---

### 用例编号

ST-UI-019-004

### 关联需求

FR-017（Web UI Search Page — 空结果空状态 UI 验证）

### 测试目标

验证搜索无结果时，UI 显示 Developer Dark 主题的空状态视觉样式（"No results found" 消息，正确的 CSS 样式）。

### 前置条件

- query-api 服务已启动
- 数据库中存在 status=indexed 仓库

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/')` | 页面开始加载 |
| 2 | `wait_for(['Search'])` → `evaluate_script(expression="document.readyState === 'complete'")` | 页面就绪 |
| 3 | `click(uid)` 选择仓库 → `fill(uid, 'xyznonexistent99999zzz')` 输入无匹配查询 → `click(uid)` 点击 Search | 搜索请求发送 |
| 4 | `wait_for(['No results found'])` → `take_snapshot()` | EXPECT: `.empty-state` 区域显示 "No results found"，文本颜色使用 `--color-text-secondary` (#8b949e); REJECT: 错误消息, 结果卡片, 空白 |
| 5 | `evaluate_script(expression="(() => { const el = document.querySelector('.empty-state'); if(!el) return {found:false}; const color = getComputedStyle(el).color; return {found:true, text_color:color}; })()")` | found = true — 空状态元素存在 |
| 6 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- `.empty-state` 元素正确渲染
- 空状态消息文本可见
- 无控制台错误

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: ui
- **已自动化**: No
- **测试引用**: N/A (Chrome DevTools MCP manual execution)
- **Test Type**: Real

---

### 用例编号

ST-SEC-019-001

### 关联需求

FR-017, FR-018（Web UI — 输入验证安全）

### 测试目标

验证搜索输入框和仓库注册 URL 输入不受 XSS 攻击影响——恶意输入被安全转义，不会在页面中执行脚本。

### 前置条件

- query-api 服务已启动

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/')` | 搜索页面加载成功 |
| 2 | `wait_for(['Search'])` | 页面就绪 |
| 3 | `fill(uid, '<script>alert("xss")</script>')` 在搜索输入框输入 XSS payload → `click(uid)` 选择仓库 → `click(uid)` 点击 Search | 搜索请求发送，payload 作为查询字符串 |
| 4 | `take_snapshot()` | EXPECT: 页面正常显示（无结果或错误消息），XSS payload 被转义为纯文本而非执行; REJECT: alert 弹窗, JavaScript 执行 |
| 5 | `evaluate_script(expression="document.querySelectorAll('script').length === document.querySelectorAll('script[src]').length + document.querySelectorAll('script:not([src])').length && !document.body.innerHTML.includes('<script>alert')")` | Layer 1: XSS payload 未被注入为可执行脚本 |
| 6 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error（非 XSS 相关） |

### 验证点

- XSS payload 在 HTML 中被转义（`<script>` 显示为文本而非执行）
- 无 JavaScript alert 弹窗
- Jinja2 auto-escaping 正常工作

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: security
- **已自动化**: No
- **测试引用**: N/A (Chrome DevTools MCP manual execution)
- **Test Type**: Real

---

### 用例编号

ST-A11Y-019-001

### 关联需求

FR-017（Web UI Search Page — WCAG 2.1 AA 可访问性）

### 测试目标

验证搜索页面的键盘导航、ARIA 属性、焦点指示器和语义 HTML 符合 WCAG 2.1 AA 标准。

### 前置条件

- query-api 服务已启动

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/')` | 页面开始加载 |
| 2 | `wait_for(['Search'])` → `evaluate_script(expression="(() => { const errs=[]; const searchInput = document.querySelector('.search-input'); if(!searchInput?.getAttribute('aria-label')) errs.push('search input missing aria-label'); const repoSelect = document.querySelector('.repo-dropdown'); if(!repoSelect?.getAttribute('aria-label')) errs.push('repo dropdown missing aria-label'); const branchSelect = document.querySelector('#branch-select'); if(!branchSelect?.getAttribute('aria-label')) errs.push('branch select missing aria-label'); const urlInput = document.querySelector('input[name=url]'); if(!urlInput?.getAttribute('aria-label')) errs.push('url input missing aria-label'); return {errors:errs, count:errs.length}; })()")` | Layer 1: count = 0 — 所有交互元素有 `aria-label` 属性 |
| 3 | `take_snapshot()` | EXPECT: 语义 HTML 结构: `<header>`, `<main>`, `<section>`, `<form>`, `<h1>`, `<h2>`; REJECT: 无语义 `<div>` 堆叠 |
| 4 | `press_key(key='Tab')` → `take_snapshot()` | EXPECT: 焦点移至搜索输入框，可见焦点指示器（蓝色边框 `--color-accent-primary` #58a6ff） |
| 5 | `press_key(key='Tab')` → `press_key(key='Tab')` → `take_snapshot()` | EXPECT: Tab 键可依次导航至搜索按钮、仓库下拉、语言复选框等交互元素 |
| 6 | `evaluate_script(expression="(() => { const h1 = document.querySelector('h1'); const h2 = document.querySelector('h2'); return { has_h1: !!h1, has_h2: !!h2, h1_text: h1?.textContent, lang: document.documentElement.lang }; })()")` | has_h1 = true, has_h2 = true, lang = "en" — 语义标题层级和页面语言属性正确 |
| 7 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- 所有交互元素有 `aria-label` 属性
- 页面使用语义 HTML (`<header>`, `<main>`, `<h1>`, `<h2>`)
- Tab 键盘导航可到达所有交互元素
- 焦点指示器可见
- `<html lang="en">` 属性存在

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: accessibility
- **已自动化**: No
- **测试引用**: N/A (Chrome DevTools MCP manual execution)
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-019-001 | FR-017 | verification_step[0] | tests/test_web_ui.py::test_search_page_renders_form | Real | PASS |
| ST-FUNC-019-002 | FR-017 | verification_step[0] | tests/test_web_ui.py::test_search_results_render | Real | PASS |
| ST-FUNC-019-003 | FR-017 | verification_step[1] | tests/test_web_ui.py::test_empty_query_validation | Real | PASS |
| ST-FUNC-019-004 | FR-017 | verification_step[2] | tests/test_web_ui.py::test_empty_results_message | Real | PASS |
| ST-BNDRY-019-001 | FR-017 | verification_step[4], verification_step[5] | tests/test_web_ui.py::test_repo_dropdown_required | Real | PASS |
| ST-BNDRY-019-002 | FR-018 | verification_step[0] | tests/test_web_ui.py::test_language_filter_checkboxes | Real | PASS |
| ST-UI-019-001 | FR-017 | verification_step[0] | N/A | Real | PASS |
| ST-UI-019-002 | FR-017 | verification_step[0] | N/A | Real | PASS |
| ST-UI-019-003 | FR-017 | verification_step[3] | N/A | Real | PASS |
| ST-UI-019-004 | FR-017 | verification_step[2] | N/A | Real | PASS |
| ST-SEC-019-001 | FR-017, FR-018 | verification_step[0] | N/A | Real | PASS |
| ST-A11Y-019-001 | FR-017 | verification_step[0] | N/A | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 12 |
| Passed | 12 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
