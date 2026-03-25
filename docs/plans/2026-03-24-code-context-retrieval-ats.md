# 验收测试策略: Code Context Retrieval MCP System

**SRS 参考**: docs/plans/2026-03-21-code-context-retrieval-srs.md
**设计文档参考**: docs/plans/2026-03-21-code-context-retrieval-design.md
**UCD 参考**: docs/plans/2026-03-21-code-context-retrieval-ucd.md
**日期**: 2026-03-24
**状态**: Approved
**模板版本**: 1.0

---

## 1. 测试范围与策略概览

### 1.1 测试目标

确保 SRS 中全部 29 FR、12 NFR、8 IFR、13 CON 在特性验收测试 (feature-st) 和系统测试 (ST) 阶段有充分的验收覆盖。本 ATS 为 Init 阶段的 `verification_steps` 和 feature-st 的用例派生提供约束性依据。

### 1.2 质量目标

- 每个 FR 至少覆盖 FUNC + BNDRY 类别
- 处理用户输入/认证/外部数据的 FR 必须覆盖 SEC 类别
- `ui:true` 的 Feature (#19 Web UI) 必须覆盖 UI + A11Y 类别
- 所有 NFR 必须有明确的测试工具、通过标准和负载参数
- 跨 Feature 集成路径必须在 ST 阶段验证

### 1.3 测试级别定义

| 级别 | 描述 | 执行阶段 |
|------|------|---------|
| 单元测试 | TDD Red-Green-Refactor | Worker (long-task-tdd) |
| 特性验收测试 | 黑盒 ST 测试用例 (ISO/IEC/IEEE 29119) | Worker (long-task-feature-st) |
| 系统测试 | 跨特性集成 + NFR 验证 + 探索性测试 | ST (long-task-st) |

---

## 2. 需求→验收场景映射

### 2.1 功能需求 (FR)

| Req ID | 需求摘要 | 验收场景 | 必须类别 | 最低用例数 | 优先级 | 备注 |
|--------|---------|---------|---------|----------|--------|------|
| FR-001 | 仓库注册 (含分支) | 正常注册/分支参数/无效URL/重复注册 | FUNC,BNDRY,SEC | 8 | Critical | 4条验收标准; 处理外部URL→+SEC |
| FR-002 | Git Clone & Update | 首次克隆/指定分支/增量更新/认证/失败/磁盘满/列出分支 | FUNC,BNDRY | 10 | Critical | 7条验收标准, 复杂度高 |
| FR-003 | 内容提取 | 文件分类/未知类型跳过/二进制跳过/大文件跳过/编码错误 | FUNC,BNDRY | 8 | High | 4条标准; 边界条件多 |
| FR-004 | 代码分块 (6语言) | Java/Python/TS/JS/C/C++ 各语言AST分块/装饰器/enum/record/namespace/template/fallback | FUNC,BNDRY | 15 | Critical | 16条标准, 6语言覆盖; CON-001 |
| FR-005 | Embedding 生成 | 批量生成/1024维向量/失败回滚/Qdrant不可达重试 | FUNC,BNDRY | 5 | High | 4条标准 |
| FR-006 | 关键词检索 (BM25+branch过滤) | 正常查询/空结果/ES不可达降级/branch过滤命中/branch过滤空 | FUNC,BNDRY | 6 | Critical | Wave5: +branch filter; ES降级→向量兜底 |
| FR-007 | 语义检索 (Vector+branch过滤) | 语义匹配/空结果/Qdrant不可达降级/branch过滤命中/branch过滤空 | FUNC,BNDRY | 6 | Critical | Wave5: +branch filter; Qdrant降级→BM25兜底 |
| FR-008 | RRF 融合 | 双路合并/重叠Boost/单路兜底/10ms时限 | FUNC,BNDRY,PERF | 5 | High | 含性能约束→+PERF |
| FR-009 | 神经重排序 | Top-100→Top-3/不足3条/模型失败降级 | FUNC,BNDRY | 5 | High | 3条标准; 降级路径 |
| FR-010 | 上下文响应构建 | 3结果JSON/symbol=null/content截断2000字符 | FUNC,BNDRY | 5 | High | 3条标准 |
| FR-011 | 自然语言查询 (repo必填+@branch) | NL查询+repo必填/空查询400/超长400/超时降级/@branch解析+过滤 | FUNC,BNDRY,SEC | 8 | Critical | Wave5: repo必填+branch透传; 处理用户输入→+SEC |
| FR-012 | 符号查询 (repo必填+@branch) | 符号匹配+repo必填/不存在符号200/超长400/@branch过滤 | FUNC,BNDRY,SEC | 5 | High | Wave5: repo必填+branch透传; 处理用户输入→+SEC |
| FR-013 | 仓库作用域过滤 | 限定仓库/不存在仓库200 | FUNC,BNDRY | 3 | High | 2条标准, 简单 |
| FR-014 | API Key 认证 | 有效Key/无效Key 401/过期Key 401/暴力破解429 | FUNC,BNDRY,SEC | 8 | Critical | 认证核心→SEC必选; 4条标准 |
| FR-015 | REST API (repo_id必填+@branch) | POST query+repo_id必填/缺repo_id→422/@branch解析/GET repos/GET health/Malformed 400 | FUNC,BNDRY,SEC | 10 | Critical | Wave5: repo_id必填+@branch; 6条标准 |
| FR-016 | MCP Server (两步式流程) | resolve_repository(query+libraryName必填)/search_code_context(repo必填+@branch)/无repo→TypeError/空匹配→空列表/内部错误 | FUNC,BNDRY | 8 | Critical | Wave5: Context7对齐; 7条标准 |
| FR-017 | Web UI (repo必选) | repo下拉必选(仅indexed)/未选repo→验证提示/结果展示/空结果/分支选择器 | FUNC,BNDRY,UI,A11Y | 12 | Medium | Wave5: repo必选; ui:true→+UI+A11Y |
| FR-018 | 语言过滤 | 单语言/多语言/无效语言400/空过滤 | FUNC,BNDRY,SEC | 5 | Medium | 用户输入→+SEC; 4条标准 |
| FR-019 | 定时索引刷新 | 默认周期触发/自定义cron/失败重试/去重 | FUNC,BNDRY | 5 | High | 4条标准 |
| FR-020 | 手动重建索引 | POST reindex/不存在repo 404 | FUNC,BNDRY | 3 | High | 2条标准, 简单 |
| FR-021 | Metrics 端点 | GET /metrics 含6项指标/指标源不可用时返回有效Prometheus格式/无需认证 | FUNC,BNDRY | 5 | Medium | 含异常路径: 部分指标源不可用 |
| FR-022 | 查询日志 | 结构化JSON日志/日志失败不阻塞 | FUNC,BNDRY | 3 | Medium | 2条标准 |
| FR-023 | 分支列表 API | 已克隆repo返回分支/不存在404/未克隆409 | FUNC,BNDRY | 5 | High | 3条标准 |
| FR-024 | 评估语料管理 | 语料构建/幂等/失败跳过 | FUNC,BNDRY | 5 | Medium | 3条标准 |
| FR-025 | LLM 查询生成与标注 | 多Provider切换/双标注/一致性/Golden存储 | FUNC,BNDRY | 5 | Medium | 5条标准 |
| FR-026 | 检索质量评估 | IR指标计算/缺失阶段跳过/报告生成/Delta比较 | FUNC,BNDRY | 5 | Medium | 4条标准 |
| FR-027 | query-api Docker 镜像 | 构建成功/Health 30s内200/HEALTHCHECK/无dev依赖/非root | FUNC,BNDRY,SEC | 8 | Critical | 5条标准; 容器安全→+SEC |
| FR-028 | mcp-server Docker 镜像 | 构建成功/mcp进程存活/HEALTHCHECK/无dev依赖/非root | FUNC,BNDRY,SEC | 5 | High | 4条标准 |
| FR-029 | index-worker Docker 镜像 | 构建成功/celery worker/HEALTHCHECK/无dev依赖/非root | FUNC,BNDRY,SEC | 5 | High | 4条标准 |
| FR-030 | 仓库解析MCP工具 [Wave5] | resolve_repository(query+libraryName必填)/名称匹配/无匹配→空列表/缺参数→TypeError/排序相关性/返回branches | FUNC,BNDRY | 8 | Critical | Wave5新增; 5条标准; Context7对齐 |
| FR-031 | Web UI 索引管理页 [Wave6] | 仓库列表(含索引状态)/Stats查询(ES+Qdrant计数)/单仓库Reindex(Celery派发)/Reindex All(确认提示)/Delete索引(确认提示)/操作反馈/非MCP暴露 | FUNC,BNDRY,UI,A11Y | 12 | High | Wave6新增; 7条验收标准; ui:true→+UI+A11Y; 含确认提示安全交互 |

### 2.2 非功能需求 (NFR)

| Req ID | 需求摘要 | 验收场景 | 必须类别 | 最低用例数 | 优先级 | 备注 |
|--------|---------|---------|---------|----------|--------|------|
| NFR-001 | p95延迟 < 1000ms | 100并发负载下p95测量 | PERF | 5 | Critical | Locust 5分钟持续负载 |
| NFR-002 | ≥1000 QPS 吞吐 | 1000+QPS持续5分钟 <1%错误 | PERF | 5 | Critical | Locust 渐进加压 |
| NFR-003 | 100-1000仓库容量 | 多仓库查询无退化 | PERF | 3 | Medium | 容量报告分析 |
| NFR-004 | 单仓库≤1GB | 大小验证在索引管线 | FUNC,BNDRY | 3 | Medium | Must级; 边界: 恰好1GB |
| NFR-005 | 10M-50M chunks容量 | ES+Qdrant文档计数 | PERF | 3 | Medium | 监控验证 |
| NFR-006 | ≥70%线性扩展 | N+1节点吞吐delta | PERF | 5 | High | 可扩展性分析报告 |
| NFR-007 | 99.9%可用性 | 健康监控+瞬时故障恢复 | PERF | 3 | High | 可用性报告分析 |
| NFR-008 | 单节点故障容忍 | 杀节点→无请求失败 | PERF | 3 | High | 故障容忍分析报告 |
| NFR-009 | API 认证 | 所有端点401/健康和metrics公开 | SEC | 5 | Critical | 7个端点逐一验证 |
| NFR-010 | 凭证加密存储 | SHA-256哈希/不同Key不同哈希 | SEC | 3 | High | AES-256 / SHA-256 |
| NFR-011 | ≥80%行覆盖率 | pytest --cov 报告 | FUNC | 3 | Medium | 当前实测95% |
| NFR-012 | 模块化Docker镜像 | 3镜像独立构建+运行 | FUNC | 3 | High | 与FR-027~029交叉验证 |

### 2.3 接口需求 (IFR)

| Req ID | 需求摘要 | 验收场景 | 必须类别 | 最低用例数 | 优先级 | 备注 |
|--------|---------|---------|---------|----------|--------|------|
| IFR-001 | AI 编码代理 (MCP) | MCP tool call → JSON结果 | FUNC,BNDRY | 5 | High | MCP stdio 协议 |
| IFR-002 | Web 浏览器 (HTTPS) | 浏览器搜索→HTML+JSON | FUNC,UI,A11Y | 5 | Medium | ui:true→+UI+A11Y |
| IFR-003 | Git 仓库 | HTTPS/SSH Clone/Fetch | FUNC,BNDRY | 3 | High | Git 协议 |
| IFR-004 | Elasticsearch | HTTP/REST JSON 连接+降级 | FUNC,BNDRY | 3 | High | 双向 |
| IFR-005 | Qdrant | gRPC/HTTP 连接+降级 | FUNC,BNDRY | 3 | High | 双向 |
| IFR-006 | Redis 缓存 | 缓存命中/未中/失效 | FUNC,BNDRY | 5 | High | 缓存一致性 |
| IFR-007 | Embedding 模型 | API调用→1024维向量 | FUNC,BNDRY | 3 | High | DashScope API |
| IFR-008 | Reranker 模型 | API调用→相关性评分 | FUNC,BNDRY | 3 | High | qwen3-rerank API |

### 2.4 覆盖统计

| 类别 | 涉及需求数 | 总最低用例数 |
|------|-----------|------------|
| FUNC | 51 (31FR+12NFR+8IFR) | 237 |
| BNDRY | 44 (30FR+6NFR+8IFR) | 204 |
| SEC | 12 (8FR+2NFR+2Docker) | 56 |
| PERF | 8 (1FR+7NFR) | 30 |
| UI | 3 (FR-017+FR-031+IFR-002) | 29 |
| A11Y | 3 (FR-017+FR-031+IFR-002) | 29 |
| **合计** | **64 需求 (含FR-031)** | **~332** |

---

## 3. 测试类别策略

### 3.1 功能测试 (FUNC)

- 每个 FR 至少一个正常路径 (happy-path) + 一个异常路径 (error-path) 场景
- Given/When/Then 格式，每条 SRS 验收标准至少映射一个 FUNC 用例
- 索引管线 (FR-002→005) 需端到端验证: Clone → Extract → Chunk → Embed → Write

### 3.2 边界测试 (BNDRY)

- 边界值分析: 查询长度 (0/1/500/501字符), API Key (空/有效/过期), 仓库URL (合法/非法/SSH格式)
- 等价类划分: 6种语言各为一等价类, 文件类型 (code/doc/example/rule/unknown/binary)
- 代码分块: 每种语言至少覆盖 L1(file)/L2(class)/L3(function) 三级粒度

### 3.3 安全测试 (SEC)

- 输入验证: SQL注入 (`'; DROP TABLE--`), XSS (`<script>alert(1)</script>`), 路径遍历 (`../../../../etc/passwd`), null字节
- 认证绕过: 无Key/错Key/过期Key → 401; 所有受保护端点逐一验证
- 暴力破解: 10次失败/分钟 → 429 限流
- 凭证存储: API Key 以 SHA-256 哈希存储, 不同Key产生不同哈希
- Docker安全: 非root用户 (UID≠0), 无开发依赖, 无敏感文件泄露

### 3.4 性能测试 (PERF)

- 测试工具: Locust (HTTP负载), pytest-benchmark (微基准)
- 负载模型: 100并发用户, 5分钟持续, 10用户/秒渐进加压
- 通过标准: p95 < 1000ms (NFR-001), ≥1000 QPS (NFR-002), RRF融合 < 10ms (FR-008)
- 容量验证: 通过分析报告 (CapacityReportAnalyzer, ScalabilityReportAnalyzer) 间接验证

### 3.5 可访问性测试 (A11Y)

- 标准: WCAG 2.1 AA
- 检查项: 键盘导航 (Tab/Enter/Space), 颜色对比 (4.5:1), ARIA 属性, 焦点管理, 语义HTML (h1→h2→h3)
- 工具: Chrome DevTools MCP (`take_snapshot verbose:true` 检查 a11y 树)
- 范围: Feature #19 Web UI Search Page

### 3.6 UI 测试 (UI)

- 工具: Chrome DevTools MCP
- 交互链: `navigate_page` → `take_snapshot` → `click`/`fill`/`press_key` → `take_snapshot` → `list_console_messages`
- 三层检测: Layer 1 (`evaluate_script` 断言DOM状态), Layer 2 (EXPECT/REJECT 模式匹配), Layer 3 (`list_console_messages` 零错误)
- 范围: 搜索页表单提交, 结果展示, 仓库注册表单, 分支选择器

---

## 4. NFR 测试方法矩阵

| NFR ID | 测试方法 | 工具 | 通过标准 | 负载参数 | 关联 Feature |
|--------|---------|------|---------|---------|-------------|
| NFR-001 | HTTP 负载测试 | Locust | p95 < 1000ms | 100并发, 5分钟持续 | #26 |
| NFR-002 | HTTP 吞吐测试 | Locust | ≥1000 QPS, <1%错误 | 渐进至1000+QPS, 5分钟 | #27 |
| NFR-003 | 容量报告分析 | CapacityReportAnalyzer | 100-1000仓库无退化 | 分析报告数据 | #28 |
| NFR-004 | 大小验证测试 | pytest | 克隆 ≤1GB 通过, >1GB 拒绝 | 边界: 1GB | #29 |
| NFR-005 | 监控验证 | Prometheus + ES/Qdrant API | doc_count ≥ target | 查询 _count API | #30 |
| NFR-006 | 扩展性报告分析 | ScalabilityReportAnalyzer | delta ≥ 70% 理论值 | N vs N+1 节点 | #31 |
| NFR-007 | 可用性报告分析 | AvailabilityReportAnalyzer | ≥99.9% 推算值 | 健康检查间隔30s | #30 |
| NFR-008 | 故障容忍分析 | FailureToleranceReportAnalyzer | 单节点故障→0请求失败 | kill进程+负载 | #32 |
| NFR-009 | 端点认证扫描 | pytest + httpx | 7端点: 5个401, 2个公开 | 逐端点请求 | #16 |
| NFR-010 | 哈希验证 | pytest | SHA-256 64字符, 碰撞测试 | 100个不同Key | #16 |
| NFR-011 | 覆盖率报告 | pytest-cov | ≥80% line (实测95%) | 全量测试 | #1 |
| NFR-012 | Docker构建测试 | docker build + inspect | 3镜像: build 0, HEALTHCHECK, 非root | 逐镜像验证 | #43,44,45 |

---

## 5. 跨 Feature 集成场景

| 场景 ID | 场景描述 | 涉及 Features | 数据流路径 | 验证要点 | ST 阶段覆盖 |
|---------|---------|--------------|-----------|---------|------------|
| INT-001 | 完整查询管线 (认证→缓存→双路检索→融合→重排→响应) | #14,#25,#8,#9,#10,#11,#12 | Auth → Cache → BM25∥Vector → RRF → Rerank → ResponseBuilder | degraded=false; 4路全通; top-3 rerank scores > 0 且单调递减 | System ST |
| INT-002 | 完整索引管线 (注册→克隆→提取→分块→嵌入→写入) | #3,#4,#5,#6,#7 | POST /repos → Clone → Extract → Chunk → Embed → ES+Qdrant write | ES doc_count = chunk数; Qdrant points = ES count | System ST |
| INT-003 | 缓存失效→新鲜查询 | #22,#25,#13 | POST /reindex → cache.invalidate → 下次查询→管线执行 | 重建索引后缓存清除; 不返回过期结果 | System ST |
| INT-004 | MCP→REST 同管线 | #18,#17,#13 | MCP search_code_context → 同 QueryHandler → 同 REST 结果 | MCP 和 REST 返回相同排序结果 | System ST |
| INT-005 | 语言+仓库双过滤传播 | #20,#15,#8,#9 | query(lang=python, repo=X) → BM25 filter + Qdrant filter | 结果同时满足语言和仓库约束 | System ST |
| INT-006 | 定时调度→Celery→索引管线 | #21,#4,#5,#6,#7 | Celery beat → reindex_all → worker → Clone → ... → ES+Qdrant | 任务注册+执行; 去重; 失败重试 | System ST |
| INT-007 | Web UI → REST API → 全管线 | #19,#17,#14,#13 | Browser form → /search → /api/v1/query → pipeline → HTML results | HTML渲染正确; 语法高亮; 控制台零错误 | System ST |
| INT-008 | 认证中间件→所有端点 | #16,#17 | X-API-Key header → AuthMiddleware → 各端点 | 5个受保护端点; 2个公开端点; 401一致性 | System ST |
| INT-009 | 评估管线 (语料→标注→评估→报告) | #40,#41,#42,#8,#9 | eval/repos.json → index → LLM queries → annotate → IR metrics → report | 端到端评估管线执行; golden dataset 格式正确 | System ST |
| INT-010 | 分支选择流 | #33,#4,#3,#19 | Web UI → Branch Listing API → GitCloner.list_remote_branches → 选择分支 → 注册 | 分支列表返回正确; 注册时indexed_branch设置正确 | System ST |
| INT-011 | MCP两步式流程 [Wave5] | #46,#18,#13,#14 | resolve_repository(query,name) → 选择repo → search_code_context(query,repo@branch) → 结果 | resolve返回indexed仓库+branches; search用@branch过滤; 两步连贯执行 | System ST |
| INT-012 | Web UI索引管理→Celery→索引管线 [Wave6] | #47,#21,#22,#4,#5,#6,#7 | Admin page → Reindex → Celery task → Clone → Extract → Chunk → Embed → Write | 前端操作触发后端Celery任务; 索引数据更新; 删除后计数归零 | System ST |

---

## 6. 风险驱动测试优先级

### 6.1 风险评估矩阵

| 风险区域 | 风险级别 | 影响范围 | 测试深度 | 依据 |
|---------|---------|---------|---------|------|
| 查询管线 (BM25+Vector+RRF+Rerank) | Critical | 核心功能, 3个用户角色 | 深度 (FUNC+BNDRY+PERF+SEC) | 系统核心路径; 远程API依赖 |
| API 认证 + 密钥管理 | Critical | 全系统安全 | 深度 (FUNC+BNDRY+SEC) | 安全边界; 暴力破解防护 |
| 6语言 AST 分块 | High | 索引质量, 检索召回率 | 深度 (FUNC+BNDRY, 16条标准) | 6种语言 × 3级粒度 |
| Docker 镜像安全 | High | 部署安全 | 标准 (FUNC+BNDRY+SEC) | 非root, 无dev依赖, HEALTHCHECK |
| Web UI (搜索) | Medium | Feature #19 | 标准 (FUNC+BNDRY+UI+A11Y) | 单页面; 主要面向开发者 |
| Web UI (索引管理) | Medium | Feature #47 | 标准 (FUNC+BNDRY+UI+A11Y) | 管理页面; 含破坏性操作确认提示 |
| 远程 Embedding/Reranker API | High | 检索质量 | 标准 (FUNC+BNDRY) | DashScope API 延迟+可用性 |
| 缓存一致性 | Medium | 查询新鲜度 | 标准 (FUNC+BNDRY) | Redis + L1 缓存; 失效路径 |
| 定时调度 | Medium | 索引新鲜度 | 标准 (FUNC+BNDRY) | Celery beat + worker |
| 评估管线 | Low | 质量度量 | 轻量 (FUNC+BNDRY) | 可选功能; 不影响核心查询 |

### 6.2 测试深度定义

| 深度 | 含义 |
|------|------|
| 深度 | 所有必须类别 + 额外探索性测试 + 用例数×1.5 |
| 标准 | 所有必须类别 + 最低用例数 |
| 轻量 | FUNC + BNDRY 仅, 最低用例数 |

---

## 附录: ATS 审核报告

**审核日期**: 2026-03-24
**审核轮次**: 1 (修复后通过)

### 维度结果

| ID | 维度 | 结果 | 缺陷数 |
|----|------|------|--------|
| R1 | 需求覆盖完整性 | PASS | 0 |
| R2 | 类别多样性 | PASS (修复后) | 0 (原1 Minor: FR-021单类别 → 已修复) |
| R3 | 场景充分性 | PASS (修复后) | 0 (原1 Major: FR-021缺异常路径 → 已修复) |
| R4 | 可验证性 | PASS (修复后) | 0 (原1 Minor: INT-001含模糊词 → 已修复) |
| R5 | NFR 可测性 | PASS | 0 |
| R6 | 跨Feature集成 | PASS | 0 |
| R7 | 风险一致性 | PASS (修复后) | 0 (原1 Major: NFR-004 Must/Low不匹配 → 已修复) |

### 缺陷清单 (全部已修复)

| # | 维度 | 严重性 | 描述 | 修复方式 |
|---|------|--------|------|---------|
| 1 | R3 | Major | FR-021 无异常路径场景 | 添加"指标源不可用时返回有效Prometheus格式"场景 |
| 2 | R7 | Major | NFR-004 SRS为Must但ATS标Low | 优先级改为Medium, 添加Must级备注 |
| 3 | R2 | Minor | FR-021 仅FUNC单类别 | 添加BNDRY类别, 用例数3→5 |
| 4 | R4 | Minor | INT-001 含"合理"(weasel word) | 替换为"top-3 rerank scores > 0 且单调递减" |

### 最终判定

**PASS** — 0 Critical, 0 Major, 0 Minor (全部4项缺陷已修复)
