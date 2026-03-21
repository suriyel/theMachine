# 测试用例集: Repository-Scoped Query

**Feature ID**: 15
**关联需求**: FR-013
**日期**: 2026-03-21
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 3 |
| boundary | 3 |
| **合计** | **6** |

---

### 用例编号

ST-FUNC-015-001

### 关联需求

FR-013 (Repository-Scoped Query)

### 测试目标

验证带repo_filter的BM25和向量检索仅返回指定仓库的chunk

### 前置条件

- Retriever类已实现并可导入
- ElasticsearchClient和QdrantClientWrapper已mock
- ES返回hits包含repo_id="spring-framework"

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Mock ES返回2个hit，repo_id="spring-framework" | Mock配置成功 |
| 2 | 调用bm25_code_search("timeout", repo_id="spring-framework") | 返回ScoredChunk列表 |
| 3 | 检查所有返回chunk的repo_id | 全部为"spring-framework" |
| 4 | 检查ES查询体的filter子句 | 包含{"term": {"repo_id": "spring-framework"}} |

### 验证点

- 返回2个ScoredChunk
- 每个chunk的repo_id == "spring-framework"
- ES查询DSL包含repo_id term filter

### 后置检查

- 无副作用需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_repo_scoped_query.py::test_bm25_code_search_with_repo_filter
- **Test Type**: Real

---

### 用例编号

ST-FUNC-015-002

### 关联需求

FR-013 (Repository-Scoped Query)

### 测试目标

验证不指定repo_filter时，检索跨越所有已索引仓库

### 前置条件

- Retriever类已实现并可导入
- ES返回包含多个不同repo_id的hits

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Mock ES返回2个hit，分别来自repo-a和repo-b | Mock配置成功 |
| 2 | 调用bm25_code_search("timeout", repo_id=None) | 返回ScoredChunk列表 |
| 3 | 检查返回chunk的repo_id集合 | 包含{"repo-a", "repo-b"} |
| 4 | 检查ES查询体 | 无repo_id filter子句 |

### 验证点

- 返回2个ScoredChunk
- chunk来自不同的仓库
- ES查询DSL不包含repo_id term filter

### 后置检查

- 无副作用需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_repo_scoped_query.py::test_bm25_code_search_without_repo_filter
- **Test Type**: Real

---

### 用例编号

ST-FUNC-015-003

### 关联需求

FR-013 (Repository-Scoped Query)

### 测试目标

验证指定不存在的仓库时返回空结果集（非错误）

### 前置条件

- Retriever类已实现并可导入
- ES返回空hits列表（0个匹配）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Mock ES返回空结果 | Mock配置成功 |
| 2 | 调用bm25_code_search("timeout", repo_id="nonexistent-repo") | 返回空列表 |
| 3 | 检查返回值类型和内容 | list类型，len == 0 |
| 4 | 确认无异常抛出 | 方法正常返回，无RetrievalError |

### 验证点

- 返回空列表[]
- 不抛出任何异常
- 返回类型是list

### 后置检查

- 无副作用需清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_repo_scoped_query.py::test_bm25_search_nonexistent_repo_returns_empty
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-015-001

### 关联需求

FR-013 (Repository-Scoped Query)

### 测试目标

验证repo_id=None且languages=None时ES查询不包含filter子句

### 前置条件

- Retriever._build_code_query可直接调用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用_build_code_query("q", repo_id=None, languages=None, top_k=10) | 返回查询字典 |
| 2 | 检查bool子句 | 包含"must"键 |
| 3 | 检查bool子句的filter | 无"filter"键或filter为空列表 |

### 验证点

- 返回的查询字典中bool子句只有must，没有filter
- multi_match查询正确构建

### 后置检查

- 无副作用需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_repo_scoped_query.py::test_build_code_query_no_repo_no_lang
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-015-002

### 关联需求

FR-013 (Repository-Scoped Query)

### 测试目标

验证Qdrant filter在repo_id=None且languages=None时返回None

### 前置条件

- Retriever._build_qdrant_filter可直接调用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用_build_qdrant_filter(repo_id=None, languages=None) | 返回None |
| 2 | 验证返回值类型 | 值为None，不是空Filter对象 |

### 验证点

- 返回值严格为None
- 不是Filter(must=[])

### 后置检查

- 无副作用需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_repo_scoped_query.py::test_build_qdrant_filter_none_none
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-015-003

### 关联需求

FR-013 (Repository-Scoped Query)

### 测试目标

验证repo_id=None但languages有值时，仅应用language filter不应用repo filter

### 前置条件

- Retriever._build_code_query和_build_qdrant_filter可调用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 调用_build_code_query("q", repo_id=None, languages=["python"], top_k=10) | 返回查询字典 |
| 2 | 检查filter子句 | 包含language terms filter |
| 3 | 确认无repo_id filter | filter中无repo_id term |
| 4 | 调用_build_qdrant_filter(repo_id=None, languages=["python"]) | 返回Filter对象 |
| 5 | 检查Filter的must条件 | 仅1个条件，key="language" |

### 验证点

- ES查询有language filter但无repo_id filter
- Qdrant Filter只有language条件，无repo_id条件

### 后置检查

- 无副作用需清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_repo_scoped_query.py::test_build_code_query_no_repo_with_lang, test_repo_scoped_query.py::test_build_qdrant_filter_no_repo_with_lang
- **Test Type**: Real

---

## 可追溯矩阵

| 用例编号 | 关联需求 | verification_step | 自动化测试 | 结果 |
|----------|----------|-------------------|------------|------|
| ST-FUNC-015-001 | FR-013 AC-1 | VS-1: repo_filter='spring-framework'时所有chunk匹配 | test_bm25_code_search_with_repo_filter, test_vector_code_search_with_repo_filter | PASS |
| ST-FUNC-015-002 | FR-013 VS-3 | VS-3: 无repo_filter时搜索所有仓库 | test_bm25_code_search_without_repo_filter, test_vector_code_search_without_repo_filter | PASS |
| ST-FUNC-015-003 | FR-013 AC-2 | VS-2: 不存在的仓库返回空结果 | test_bm25_search_nonexistent_repo_returns_empty, test_handle_nl_query_nonexistent_repo | PASS |
| ST-BNDRY-015-001 | FR-013 | 边界: 无过滤条件时查询构建 | test_build_code_query_no_repo_no_lang | PASS |
| ST-BNDRY-015-002 | FR-013 | 边界: Qdrant null filter | test_build_qdrant_filter_none_none | PASS |
| ST-BNDRY-015-003 | FR-013 | 边界: 仅language filter无repo filter | test_build_code_query_no_repo_with_lang, test_build_qdrant_filter_no_repo_with_lang | PASS |

## Real Test Case Execution Summary

| 指标 | 数值 |
|------|------|
| Real用例总数 | 6 |
| 通过 | 6 |
| 失败 | 0 |
| 待执行 | 0 |
