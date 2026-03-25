# 测试用例集: Web UI Index Management Page

**Feature ID**: 47
**关联需求**: FR-031
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

ST-FUNC-047-001

### 关联需求

FR-031（Web UI Index Management Page — 仓库列表页面渲染）

### 测试目标

验证 GET /admin/indexes 返回包含所有已注册仓库的表格，表格列包含 name、status、branch、last_indexed_at，并提供 Stats、Reindex、Delete 操作按钮。

### 前置条件

- query-api 服务已启动，监听 localhost:8000
- 数据库中存在至少 1 个已注册的仓库

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/admin/indexes')` | 页面开始加载 |
| 2 | `wait_for(['Index Management'])` → `evaluate_script(expression="document.readyState")` | 页面加载完成，readyState = "complete" |
| 3 | `evaluate_script(expression="(() => { const errs = []; const table = document.querySelector('table'); if(!table) errs.push('no table'); const headers = Array.from(table?.querySelectorAll('th') || []).map(th => th.textContent.trim().toLowerCase()); ['name','status','branch'].forEach(h => { if(!headers.some(hdr => hdr.includes(h))) errs.push('missing column: '+h); }); const rows = table?.querySelectorAll('tbody tr') || []; if(rows.length < 1) errs.push('no repo rows'); return {errors: errs, count: errs.length}; })()")` | Layer 1: count = 0 — 表格存在，包含 name/status/branch 列，至少 1 行仓库数据 |
| 4 | `take_snapshot()` | EXPECT: 页面标题 "Index Management"，仓库表格含 name/status/branch/indexed 列，至少 1 行数据，每行含 Stats/Reindex/Delete 操作按钮，"Reindex All" 全局按钮; REJECT: 空白页面, 错误消息, "No repositories" 当有仓库时 |
| 5 | `evaluate_script(expression="(() => { const rows = document.querySelectorAll('table tbody tr'); const firstRow = rows[0]; const btns = firstRow?.querySelectorAll('button, a[hx-post], a[hx-get], [hx-post], [hx-get]') || []; return {row_count: rows.length, action_count: btns.length}; })()")` | row_count >= 1, action_count >= 2 — 每行有操作按钮 |
| 6 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- 表格包含 name、status、branch、last_indexed_at 列
- 至少 1 个仓库行显示在表格中
- 每行包含 Stats、Reindex、Delete 操作按钮
- 全局 "Reindex All" 按钮可见
- 无控制台错误

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui_index_mgmt.py::test_index_management_page_lists_repos
- **Test Type**: Real

---

### 用例编号

ST-FUNC-047-002

### 关联需求

FR-031（Web UI Index Management Page — Stats 查询显示 ES/Qdrant 计数）

### 测试目标

验证点击某仓库的 Stats 按钮后，内联显示 ES 文档计数 (code_chunks, doc_chunks, rule_chunks) 和 Qdrant 计数 (code_embeddings, doc_embeddings)。

### 前置条件

- query-api 服务已启动，监听 localhost:8000
- 数据库中存在至少 1 个已注册的仓库
- Elasticsearch 和 Qdrant 服务运行中

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/admin/indexes')` | 页面开始加载 |
| 2 | `wait_for(['Index Management'])` → `evaluate_script(expression="document.readyState === 'complete'")` | 页面加载完成 |
| 3 | `take_snapshot()` → 识别第一个仓库行的 Stats 按钮 | EXPECT: 仓库表格可见，Stats 按钮存在 |
| 4 | `click(uid)` 点击第一个仓库的 Stats 按钮 | HTMX 请求发送至 `/admin/indexes/{repo_id}/stats`，内联展开 stats 区域 |
| 5 | `wait_for(['code_chunks'])` → `take_snapshot()` | EXPECT: 内联显示 code_chunks、doc_chunks、rule_chunks (ES 计数) 和 code_embeddings、doc_embeddings (Qdrant 计数)，均为数字值; REJECT: 错误消息, "not found", 加载中状态卡死 |
| 6 | `evaluate_script(expression="(() => { const statsEl = document.querySelector('[id*=stats], .stats-row, .index-stats, tr.stats'); if(!statsEl) return {found: false}; const text = statsEl.textContent; return {found: true, has_code_chunks: text.includes('code_chunks'), has_doc_chunks: text.includes('doc_chunks'), has_rule_chunks: text.includes('rule_chunks'), has_code_emb: text.includes('code_embeddings'), has_doc_emb: text.includes('doc_embeddings')}; })()")` | found = true, 所有 5 个指标名称均存在 |
| 7 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- Stats 内联展开显示 5 个计数指标: code_chunks, doc_chunks, rule_chunks, code_embeddings, doc_embeddings
- 每个指标显示为数字
- 无控制台错误
- HTMX 部分更新（无全页刷新）

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui_index_mgmt.py::test_index_stats_returns_counts
- **Test Type**: Real

---

### 用例编号

ST-FUNC-047-003

### 关联需求

FR-031（Web UI Index Management Page — Reindex 单仓库）

### 测试目标

验证点击某仓库的 Reindex 按钮后，系统派发 Celery 任务并显示包含 job ID 的成功消息。

### 前置条件

- query-api 服务已启动，监听 localhost:8000
- 数据库中存在至少 1 个已注册的仓库
- Celery broker (RabbitMQ) 运行中

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/admin/indexes')` | 页面开始加载 |
| 2 | `wait_for(['Index Management'])` → `evaluate_script(expression="document.readyState === 'complete'")` | 页面加载完成 |
| 3 | `take_snapshot()` → 识别第一个仓库行的 Reindex 按钮 | EXPECT: Reindex 按钮存在 |
| 4 | `click(uid)` 点击第一个仓库的 Reindex 按钮 | HTMX POST 发送至 `/admin/indexes/{repo_id}/reindex` |
| 5 | `wait_for(['queued', 'success', 'Reindex'])` → `take_snapshot()` | EXPECT: 成功消息显示 "Reindex queued" 或类似文本，包含 job ID 或 task ID; REJECT: 错误消息, "failed", 500 状态 |
| 6 | `evaluate_script(expression="(() => { const msg = document.querySelector('.success, .alert-success, [class*=success]'); return {has_success: !!msg, text: msg?.textContent?.trim() || ''}; })()")` | has_success = true, text 包含 "queued" 或 "Reindex" |
| 7 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- Reindex 按钮触发 HTMX POST 请求
- 成功消息显示，包含 job/task ID
- 无全页刷新（HTMX 部分更新）
- 无控制台错误

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui_index_mgmt.py::test_index_reindex_dispatches_celery
- **Test Type**: Real

---

### 用例编号

ST-FUNC-047-004

### 关联需求

FR-031（Web UI Index Management Page — Delete Index 含确认提示）

### 测试目标

验证点击 Delete Index 按钮后显示确认提示，确认后删除所有索引数据并显示成功消息。

### 前置条件

- query-api 服务已启动，监听 localhost:8000
- 数据库中存在至少 1 个已注册的仓库
- Elasticsearch 和 Qdrant 服务运行中

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/admin/indexes')` | 页面开始加载 |
| 2 | `wait_for(['Index Management'])` → `evaluate_script(expression="document.readyState === 'complete'")` | 页面加载完成 |
| 3 | `take_snapshot()` → 识别第一个仓库行的 Delete 按钮 | EXPECT: Delete 按钮存在，带有 hx-confirm 属性 |
| 4 | `evaluate_script(expression="(() => { const delBtn = document.querySelector('[hx-post*=delete], button[onclick*=delete], [hx-confirm]'); return {exists: !!delBtn, has_confirm: delBtn?.hasAttribute('hx-confirm') || false}; })()")` | exists = true, has_confirm = true — Delete 按钮配有 hx-confirm 确认属性 |
| 5 | `click(uid)` 点击 Delete 按钮 → `handle_dialog(accept=true)` 接受确认对话框 | 确认对话框弹出并被接受，HTMX POST 发送至 `/admin/indexes/{repo_id}/delete` |
| 6 | `wait_for(['deleted', 'success'])` → `take_snapshot()` | EXPECT: 成功消息 "Index deleted" 或类似文本; REJECT: 错误消息, "failed" |
| 7 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- Delete 按钮带有 hx-confirm 确认提示属性
- 确认后成功删除索引数据
- 显示成功消息
- 无全页刷新（HTMX 部分更新）
- 无控制台错误

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui_index_mgmt.py::test_index_delete_calls_delete_repo_index
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-047-001

### 关联需求

FR-031（Web UI Index Management Page — 空仓库列表边界）

### 测试目标

验证当数据库中无已注册仓库时，/admin/indexes 页面渲染空状态表格或提示消息，不产生错误。

### 前置条件

- query-api 服务已启动，监听 localhost:8000
- 数据库中无已注册的仓库（或所有仓库已删除）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 HTTP GET 请求至 `http://localhost:8000/admin/indexes` | 返回 HTTP 200 |
| 2 | 检查响应 HTML 内容 | EXPECT: 页面包含 "Index Management" 标题; REJECT: HTTP 500, 错误堆栈 |
| 3 | 检查表格内容 | EXPECT: 表格为空或显示 "No repositories" 类似提示; REJECT: 异常错误, 空白页面无任何内容 |

### 验证点

- HTTP 200 状态码
- 页面正常渲染，无服务器错误
- 空状态正确展示

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui_index_mgmt.py::test_index_management_page_empty_repos
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-047-002

### 关联需求

FR-031（Web UI Index Management Page — Stats 查询仓库不存在）

### 测试目标

验证当 Stats 请求的 repo_id 不存在时，返回友好的错误提示而非服务器崩溃。

### 前置条件

- query-api 服务已启动，监听 localhost:8000

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 发送 HTTP GET 请求至 `http://localhost:8000/admin/indexes/00000000-0000-0000-0000-000000000000/stats` | 返回 HTTP 200 (HTML partial) |
| 2 | 检查响应 HTML 内容 | EXPECT: 包含 "not found" 错误消息; REJECT: HTTP 500, 异常堆栈, 空响应 |
| 3 | 发送 HTTP POST 请求至 `http://localhost:8000/admin/indexes/00000000-0000-0000-0000-000000000000/reindex` | 返回 HTTP 200 (HTML partial) |
| 4 | 检查响应 HTML 内容 | EXPECT: 包含 "not found" 错误消息 |
| 5 | 发送 HTTP POST 请求至 `http://localhost:8000/admin/indexes/00000000-0000-0000-0000-000000000000/delete` | 返回 HTTP 200 (HTML partial) |
| 6 | 检查响应 HTML 内容 | EXPECT: 包含 "not found" 错误消息 |

### 验证点

- 不存在的 repo_id 返回友好错误消息
- 不产生 HTTP 500 或服务器异常
- 所有三个操作（stats/reindex/delete）均正确处理不存在的仓库

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui_index_mgmt.py::test_index_stats_repo_not_found
- **Test Type**: Real

---

### 用例编号

ST-UI-047-001

### 关联需求

FR-031（Web UI Index Management Page — 页面完整渲染及 Developer Dark 主题）

### 测试目标

验证 /admin/indexes 页面通过 Chrome DevTools MCP 正确渲染，应用 Developer Dark 主题，表格结构完整，导航链接包含 [Search] 和 [Indexes]。

### 前置条件

- query-api 服务已启动，监听 localhost:8000
- 数据库中存在至少 1 个已注册的仓库
- Chrome 浏览器可通过 Chrome DevTools MCP 访问

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/admin/indexes')` | 页面开始加载 |
| 2 | `wait_for(['Index Management'])` → `evaluate_script(expression="document.readyState")` | 页面加载完成，readyState = "complete" |
| 3 | `evaluate_script(expression="(() => { const errs = []; const bg = getComputedStyle(document.body).backgroundColor; if(bg !== 'rgb(13, 17, 23)') errs.push('wrong bg: '+bg); const table = document.querySelector('table'); if(!table) errs.push('no table'); const nav = document.querySelector('nav, header, [class*=nav]'); if(!nav) errs.push('no nav'); return {errors: errs, count: errs.length}; })()")` | Layer 1: count = 0 — Developer Dark 背景色 #0d1117, 表格存在, 导航栏存在 |
| 4 | `take_snapshot()` | EXPECT: 页面标题 "Index Management"，Developer Dark 背景 (#0d1117)，仓库表格含 name/status/branch/indexed 列，导航含 Search 和 Indexes 链接，"Reindex All" 按钮可见，字体使用 `--font-heading-2` (Inter 18px 600) 用于标题，`--font-body` (Inter 14px 400) 用于表格数据; REJECT: 白色背景, 无表格, 无导航 |
| 5 | `evaluate_script(expression="(() => { const heading = document.querySelector('h1, h2, [class*=title]'); const style = heading ? getComputedStyle(heading) : null; return {has_heading: !!heading, font_weight: style?.fontWeight, color: style?.color}; })()")` | has_heading = true, font_weight 为 "600" 或 "bold", color 为 `--color-text-primary` (#e6edf3) |
| 6 | `evaluate_script(expression="getComputedStyle(document.body).backgroundColor")` | 背景色为 rgb(13, 17, 23) 即 #0d1117 |
| 7 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- Developer Dark 主题已应用（背景色 #0d1117）
- 页面标题使用 `--font-heading-2` 样式 (Inter, 600 weight)
- 文字颜色为 `--color-text-primary` (#e6edf3)
- 表格正确渲染，包含所有必需列
- 导航栏包含 Search 和 Indexes 链接
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

ST-UI-047-002

### 关联需求

FR-031（Web UI Index Management Page — HTMX Stats 内联展开交互）

### 测试目标

验证点击 Stats 按钮后，通过 HTMX 部分更新在表格行内展开 stats 区域，无全页刷新。

### 前置条件

- query-api 服务已启动，监听 localhost:8000
- 数据库中存在至少 1 个已注册的仓库
- Elasticsearch 和 Qdrant 运行中
- Chrome 浏览器可通过 Chrome DevTools MCP 访问

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/admin/indexes')` | 页面开始加载 |
| 2 | `wait_for(['Index Management'])` → `evaluate_script(expression="document.readyState === 'complete'")` | 页面加载完成 |
| 3 | `evaluate_script(expression="window.__pageLoadId = Date.now(); true")` | 设置页面标识用于检测是否发生全页刷新 |
| 4 | `take_snapshot()` → `click(uid)` 点击第一个仓库的 Stats 按钮 | HTMX 请求发送，Stats 区域开始加载 |
| 5 | `wait_for(['code_chunks'])` → `take_snapshot()` | EXPECT: 内联显示 code_chunks, doc_chunks, rule_chunks, code_embeddings, doc_embeddings 计数; REJECT: 全页刷新, 新页面导航, 错误消息 |
| 6 | `evaluate_script(expression="window.__pageLoadId !== undefined")` | 返回 true — 页面未刷新（__pageLoadId 仍存在），证明是 HTMX 部分更新 |
| 7 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- Stats 按钮通过 HTMX 触发部分更新
- 内联 stats 区域正确渲染 5 个计数指标
- 页面未发生全页刷新（window 变量保持）
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

ST-UI-047-003

### 关联需求

FR-031（Web UI Index Management Page — Reindex All 确认提示交互）

### 测试目标

验证 Reindex All 按钮点击后显示浏览器确认对话框，确认后通过 HTMX 派发所有仓库的 reindex 任务并显示汇总消息。

### 前置条件

- query-api 服务已启动，监听 localhost:8000
- 数据库中存在至少 1 个已注册的仓库
- Celery broker (RabbitMQ) 运行中
- Chrome 浏览器可通过 Chrome DevTools MCP 访问

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/admin/indexes')` | 页面开始加载 |
| 2 | `wait_for(['Index Management'])` → `evaluate_script(expression="document.readyState === 'complete'")` | 页面加载完成 |
| 3 | `take_snapshot()` → 识别 "Reindex All" 按钮 | EXPECT: "Reindex All" 按钮可见，带有 hx-confirm 属性 |
| 4 | `evaluate_script(expression="(() => { const btn = document.querySelector('[hx-post*=reindex-all]'); return {exists: !!btn, has_confirm: btn?.hasAttribute('hx-confirm') || false, text: btn?.textContent?.trim() || ''}; })()")` | exists = true, has_confirm = true — Reindex All 按钮配有确认提示 |
| 5 | `click(uid)` 点击 Reindex All 按钮 → `handle_dialog(accept=true)` 接受确认 | 确认对话框弹出并被接受，HTMX POST 发送至 `/admin/indexes/reindex-all` |
| 6 | `wait_for(['queued', 'repos'])` → `take_snapshot()` | EXPECT: 汇总消息显示 "N repos queued" 或类似文本; REJECT: 错误消息, "failed" |
| 7 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- Reindex All 按钮带有 hx-confirm 确认属性
- 确认后成功派发任务
- 汇总消息正确显示已队列的仓库数量
- 无全页刷新（HTMX 部分更新）
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

ST-UI-047-004

### 关联需求

FR-031（Web UI Index Management Page — Delete Index 确认交互及成功反馈）

### 测试目标

验证 Delete 按钮点击后显示确认对话框，确认后删除索引数据，通过 HTMX 部分更新显示成功消息，不发生全页刷新。

### 前置条件

- query-api 服务已启动，监听 localhost:8000
- 数据库中存在至少 1 个已注册的仓库
- Elasticsearch 和 Qdrant 运行中
- Chrome 浏览器可通过 Chrome DevTools MCP 访问

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/admin/indexes')` | 页面开始加载 |
| 2 | `wait_for(['Index Management'])` → `evaluate_script(expression="document.readyState === 'complete'")` | 页面加载完成 |
| 3 | `evaluate_script(expression="window.__deleteTestId = Date.now(); true")` | 设置页面标识用于检测全页刷新 |
| 4 | `take_snapshot()` → 识别第一个仓库的 Delete 按钮 | EXPECT: Delete 按钮可见 |
| 5 | `click(uid)` 点击 Delete 按钮 → `handle_dialog(accept=true)` 接受确认 | 确认对话框弹出并被接受，HTMX POST 发送至 `/admin/indexes/{repo_id}/delete` |
| 6 | `wait_for(['deleted', 'success'])` → `take_snapshot()` | EXPECT: 成功消息 "Index deleted" 或类似文本; REJECT: 错误消息, "failed" |
| 7 | `evaluate_script(expression="window.__deleteTestId !== undefined")` → `list_console_messages(types=["error"])` | __deleteTestId 仍存在（无全页刷新）; Layer 3: 控制台无 error |

### 验证点

- Delete 确认对话框正确弹出
- 确认后删除成功
- 成功消息正确显示
- 无全页刷新
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

ST-SEC-047-001

### 关联需求

FR-031（Web UI Index Management Page — 非 MCP 暴露验证）

### 测试目标

验证索引管理路由 (/admin/indexes) 不通过 MCP 服务器暴露，MCP 工具无法访问管理功能。

### 前置条件

- query-api 服务已启动
- MCP 服务器已启动（如有）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 检查 MCP 服务器注册的工具列表 | EXPECT: 无 "admin"、"indexes"、"index_management" 相关工具; REJECT: 存在任何管理路由的 MCP 工具 |
| 2 | 检查 MCP 服务器源代码中是否注册了 admin 路由 | EXPECT: MCP 服务器模块不导入或注册 /admin/ 路由 |
| 3 | 通过 HTTP 向 query-api 发送 GET `http://localhost:8000/admin/indexes` 并包含有效 API Key Cookie | EXPECT: HTTP 200, 页面正常渲染（仅 Web UI 可访问） |

### 验证点

- MCP 服务器不暴露 admin 相关工具
- 索引管理路由仅通过 Web UI (HTTP) 可访问
- MCP 工具列表中无 admin/indexes 相关条目

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: security
- **已自动化**: Yes
- **测试引用**: tests/test_web_ui_index_mgmt.py::test_no_mcp_exposure
- **Test Type**: Real

---

### 用例编号

ST-A11Y-047-001

### 关联需求

FR-031（Web UI Index Management Page — WCAG 2.1 AA 可访问性）

### 测试目标

验证索引管理页面满足 WCAG 2.1 AA 基本要求：键盘可导航、颜色对比达标、语义 HTML 正确、交互元素有适当的 ARIA 标签。

### 前置条件

- query-api 服务已启动，监听 localhost:8000
- 数据库中存在至少 1 个已注册的仓库
- Chrome 浏览器可通过 Chrome DevTools MCP 访问

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | `navigate_page(url='http://localhost:8000/admin/indexes')` | 页面开始加载 |
| 2 | `wait_for(['Index Management'])` → `evaluate_script(expression="document.readyState === 'complete'")` | 页面加载完成 |
| 3 | `evaluate_script(expression="(() => { const checks = []; const table = document.querySelector('table'); if(!table) checks.push('no table element'); if(table && !table.querySelector('thead')) checks.push('table missing thead'); if(table && !table.querySelector('th')) checks.push('table missing th headers'); const btns = document.querySelectorAll('button, [role=button]'); btns.forEach((b,i) => { if(!b.textContent.trim() && !b.getAttribute('aria-label')) checks.push('button '+i+' has no accessible name'); }); const heading = document.querySelector('h1, h2'); if(!heading) checks.push('no heading element'); return {issues: checks, count: checks.length}; })()")` | Layer 1: count = 0 — 表格使用语义 HTML (thead, th), 按钮有可访问名称, 页面有标题元素 |
| 4 | `take_snapshot()` | EXPECT: 页面使用语义 HTML (table/thead/th/tbody/tr/td), 标题使用 h1 或 h2, 按钮有文字或 aria-label; REJECT: div 模拟表格, 按钮无文字 |
| 5 | `press_key(key='Tab')` → `press_key(key='Tab')` → `take_snapshot()` | EXPECT: Tab 键可导航至交互元素，焦点指示器可见 |
| 6 | `evaluate_script(expression="(() => { const focused = document.activeElement; return {tag: focused?.tagName, type: focused?.type, has_focus_style: getComputedStyle(focused).outlineStyle !== 'none' || getComputedStyle(focused).boxShadow !== 'none'}; })()")` | 焦点在交互元素上，焦点样式可见（outline 或 box-shadow） |
| 7 | `list_console_messages(types=["error"])` | Layer 3: 控制台无 error |

### 验证点

- 表格使用语义 HTML 结构 (table, thead, th, tbody)
- 所有按钮有可访问名称 (textContent 或 aria-label)
- 页面有标题元素 (h1 或 h2)
- Tab 键可导航至交互元素
- 焦点指示器可见
- 文字颜色对比满足 WCAG AA 标准（#e6edf3 on #0d1117 = 13.5:1）
- 无控制台错误

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
| ST-FUNC-047-001 | FR-031 | verification_step[0]: Navigate to /admin/indexes — page renders with table | tests/test_web_ui_index_mgmt.py::test_index_management_page_lists_repos | Real | PASS |
| ST-FUNC-047-002 | FR-031 | verification_step[1]: Click Stats — inline ES/Qdrant doc counts | tests/test_web_ui_index_mgmt.py::test_index_stats_returns_counts | Real | PASS |
| ST-FUNC-047-003 | FR-031 | verification_step[2]: Click Reindex — Celery task dispatched, success message | tests/test_web_ui_index_mgmt.py::test_index_reindex_dispatches_celery | Real | PASS |
| ST-FUNC-047-004 | FR-031 | verification_step[4]: Click Delete Index — confirmation, delete, success | tests/test_web_ui_index_mgmt.py::test_index_delete_calls_delete_repo_index | Real | PASS |
| ST-BNDRY-047-001 | FR-031 | verification_step[0]: Empty repos boundary | tests/test_web_ui_index_mgmt.py::test_index_management_page_empty_repos | Real | PASS |
| ST-BNDRY-047-002 | FR-031 | verification_step[1,2,4]: Repo not found boundary | tests/test_web_ui_index_mgmt.py::test_index_stats_repo_not_found | Real | PASS |
| ST-UI-047-001 | FR-031 | verification_step[0]: Page renders with Developer Dark theme | N/A (Chrome DevTools MCP) | Real | PASS |
| ST-UI-047-002 | FR-031 | verification_step[1,5]: Stats HTMX partial update without full page reload | N/A (Chrome DevTools MCP) | Real | PASS |
| ST-UI-047-003 | FR-031 | verification_step[3]: Reindex All confirmation prompt | N/A (Chrome DevTools MCP) | Real | PASS |
| ST-UI-047-004 | FR-031 | verification_step[4,5]: Delete confirmation + HTMX partial | N/A (Chrome DevTools MCP) | Real | PASS |
| ST-SEC-047-001 | FR-031 | verification_step[6]: Not accessible via MCP tools | tests/test_web_ui_index_mgmt.py::test_no_mcp_exposure | Real | PASS |
| ST-A11Y-047-001 | FR-031 | verification_step[0]: WCAG 2.1 AA accessibility | N/A (Chrome DevTools MCP) | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 12 |
| Passed | 12 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
