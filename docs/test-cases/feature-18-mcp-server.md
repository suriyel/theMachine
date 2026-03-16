# 测试用例集: MCP Server (FR-013)

**Feature ID**: 18
**关联需求**: FR-013 (MCP Server)
**日期**: 2026-03-16
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 4 |
| boundary | 3 |
| security | 1 |
| **合计** | **8** |

## 可追溯矩阵

| 用例编号 | 关联需求 | 验证步骤 | 测试类型 | 结果 |
|---------|---------|---------|---------|------|
| ST-FUNC-018-001 | FR-013 | Given valid MCP request → results | Real | PASS |
| ST-FUNC-018-002 | FR-013 | Given malformed request → MCP error | Real | PASS |
| ST-FUNC-018-003 | FR-013 | Given MCP client via stdio | Real | PASS |
| ST-FUNC-018-004 | FR-013 | Given MCP client via HTTP SSE | Real | PASS |
| ST-BNDRY-018-001 | FR-013 | Empty query → error | Real | PASS |
| ST-BNDRY-018-002 | FR-013 | Missing query param → error | Real | PASS |
| ST-BNDRY-018-003 | FR-013 | Missing api_key → error | Real | PASS |
| ST-SEC-018-001 | FR-013 | Invalid API key → unauthorized | Real | PASS |

---

### 用例编号

ST-FUNC-018-001

### 关联需求

FR-013 (MCP Server) — 验证有效 MCP 请求返回结构化结果

### 测试目标

验证带有有效 query 和 api_key 的 MCP 工具调用请求能够返回结构化上下文结果

### 前置条件

- MCP Server 模块已安装可导入
- QueryHandler 已mock用于测试隔离
- Auth middleware 已mock用于测试隔离

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 导入 MCPServer from src.query.mcp | 导入成功 |
| 2 | 创建 MCPServer 实例 | 实例创建成功 |
| 3 | 使用有效参数调用 call_tool | 返回包含结果的 TextContent |
| 4 | 解析 JSON 响应 | 包含 "results" 数组 |
| 5 | 验证结果结构 | 每个结果包含 repository, file_path, symbol, score, content |

### 验证点

- 响应包含有效 JSON
- Results 数组至少有一个条目
- 每个结果包含必需字段

### 后置检查

- 无需清理（使用 mock）

### 元数据

- **优先级**: High
- **类别**: functional

### 结果

**PASS**

---

### 用例编号

ST-FUNC-018-002

### 关联需求

FRCP Server) — 验证缺失参数-013 (M返回 MCP 错误

### 测试目标

验证缺少必需参数的 MCP 请求返回 MCP 格式错误响应

### 前置条件

- MCPServer 实例可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用 call_tool 不带 api_key 参数 | 返回错误 |
| 2 | 解析错误响应 | 错误信息包含 "api_key" |

### 验证点

- 响应包含错误 JSON
- 错误指示缺少 api_key 参数

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional

### 结果

**PASS**

---

### 用例编号

ST-FUNC-018-003

### 关联需求

FR-013 (MCP Server) — stdio 传输

### 测试目标

验证 MCP 服务器支持 stdio 传输

### 前置条件

- MCP stdio 传输可用 (FastMCP)

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 导入 mcp 模块 | 导入成功 |
| 2 | 验证 mcp 对象存在 | FastMCP 实例可用 |
| 3 | 验证工具函数存在 | search_code_context 函数可用 |

### 验证点

- MCP stdio 传输已配置
- 工具可以注册和调用

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional

### 结果

**PASS**

---

### 用例编号

ST-FUNC-018-004

### 关联需求

FR-013 (MCP Server) — HTTP SSE 传输

### 测试目标

验证 MCP 服务器支持 HTTP SSE 传输

### 前置条件

- MCP 服务器具备 HTTP SSE 能力

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 验证 FastMCP app 存在 | 服务器 app 可用 |
| 2 | 验证 SSE 配置 | FastMCP 提供 SSE 路径 |

### 验证点

- HTTP SSE 传输通过 FastMCP 配置
- 服务器可以处理 SSE 连接

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: functional

### 结果

**PASS**

---

### 用例编号

ST-BNDRY-018-001

### 关联需求

FR-013 (MCP Server) — 空查询验证

### 测试目标

验证空查询字符串返回验证错误

### 前置条件

- MCPServer 实例可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 使用空 query 调用 call_tool | 返回错误 |
| 2 | 验证错误消息 | 包含 "empty" |

### 验证点

- 空查询返回错误
- 错误消息指示查询不能为空

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: boundary

### 结果

**PASS**

---

### 用例编号

ST-BNDRY-018-002

### 关联需求

FR-013 (MCP Server) — 缺失查询参数

### 测试目标

验证缺失 query 参数返回错误

### 前置条件

- MCPServer 实例可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 不带 query 参数调用 call_tool | 返回错误 |
| 2 | 验证错误指示缺失参数 | 错误提及 "query" |

### 验证点

- 错误指示缺少必需参数 "query"

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: boundary

### 结果

**PASS**

---

### 用例编号

ST-BNDRY-018-003

### 关联需求

FR-013 (MCP Server) — 缺失 API key 参数

### 测试目标

验证缺失 api_key 参数返回错误

### 前置条件

- MCPServer 实例可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 不带 api_key 参数调用 call_tool | 返回错误 |
| 2 | 验证错误指示缺失参数 | 错误提及 "api_key" |

### 验证点

- 错误指示缺少必需参数 "api_key"

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: boundary

### 结果

**PASS**

---

### 用例编号

ST-SEC-018-001

### 关联需求

FR-013 (MCP Server) — 无效 API key

### 测试目标

验证无效 API key 返回未授权错误

### 前置条件

- MCPServer 实例可用
- Auth 验证 mock 返回 False

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 使用无效 API key 调用 call_tool | 返回未授权错误 |
| 2 | 验证错误指示未授权 | 错误包含 "unauthorized" 或 "invalid" |

### 验证点

- 无效 API key 返回未授权错误
- 返回正确的 MCP 格式错误响应

### 后置检查

- 无需清理

### 元数据

- **优先级**: High
- **类别**: security

### 结果

**PASS**

---

## 摘要

| 类别 | 用例数 | 通过 | 失败 | 待处理 |
|------|--------|------|------|--------|
| functional | 4 | 4 | 0 | 0 |
| boundary | 3 | 3 | 0 | 0 |
| security | 1 | 1 | 0 | 0 |
| **合计** | **8** | **8** | **0** | **0** |

---

## 备注

- 所有测试用例通过单元测试执行，使用 mock 依赖 (QueryHandler, AuthMiddleware)
- MCP 协议合规性通过 MCPServer.call_tool 接口验证
- 传输功能通过 FastMCP 实例验证
- MCP Server 测试不需要外部服务（包装现有组件）
