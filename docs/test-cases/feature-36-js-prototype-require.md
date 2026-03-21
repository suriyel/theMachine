# 测试用例集: JavaScript: prototype-assigned functions + require() imports

**Feature ID**: 36
**关联需求**: FR-004 (Wave 2)
**日期**: 2026-03-21
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 4 |
| boundary | 5 |
| **合计** | **9** |

---

### 用例编号

ST-FUNC-036-001

### 关联需求

FR-004 (Code Chunking — prototype-assigned function detection)

### 测试目标

验证JavaScript文件中`res.status = function(code){...}`模式的prototype-assigned function被正确识别为L3 function chunk，且symbol为属性名'status'

### 前置条件

- Chunker类已实现且可导入
- tree-sitter JavaScript解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JS文件，内容为`res.status = function(code) { return code; };` | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 筛选chunk_type='function'的chunk | 恰好1个function chunk |
| 4 | 检查该function chunk的symbol字段 | symbol == 'status' |
| 5 | 检查该function chunk的content字段 | content包含'res.status'和'function' |

### 验证点

- 返回的function chunk数量为1
- function chunk的symbol为'status'
- function chunk的language为'javascript'
- function chunk的content包含完整expression_statement文本

### 后置检查

- 无外部资源需要清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature36JsPrototypeAssign::test_js_prototype_function, test_js_prototype_content_is_full_statement
- **Test Type**: Real

---

### 用例编号

ST-FUNC-036-002

### 关联需求

FR-004 (Code Chunking — prototype-assigned arrow function detection)

### 测试目标

验证JavaScript文件中`obj.handler = (req, res) => {...}`模式的箭头函数赋值被正确识别为L3 function chunk，且symbol为属性名'handler'

### 前置条件

- Chunker类已实现且可导入
- tree-sitter JavaScript解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JS文件，内容为`obj.handler = (req, res) => { return 42; };` | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 筛选chunk_type='function'的chunk | 恰好1个function chunk |
| 4 | 检查该function chunk的symbol字段 | symbol == 'handler' |

### 验证点

- 返回的function chunk数量为1
- function chunk的symbol为'handler'
- function chunk的language为'javascript'

### 后置检查

- 无外部资源需要清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature36JsPrototypeAssign::test_js_prototype_arrow
- **Test Type**: Real

---

### 用例编号

ST-FUNC-036-003

### 关联需求

FR-004 (Code Chunking — require() import detection)

### 测试目标

验证JavaScript文件中`var express = require('express')`模式的CommonJS require()调用被正确提取到L1 file chunk的imports列表中

### 前置条件

- Chunker类已实现且可导入
- tree-sitter JavaScript解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JS文件，内容为`var express = require('express');` | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 获取L1 file chunk的imports列表 | imports列表包含'express' |

### 验证点

- L1 file chunk的imports中包含'express'

### 后置检查

- 无外部资源需要清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature36JsRequireImports::test_js_require_single
- **Test Type**: Real

---

### 用例编号

ST-FUNC-036-004

### 关联需求

FR-004 (Code Chunking — multiple require() imports)

### 测试目标

验证JavaScript文件中多个require()调用（使用var/const/let不同声明方式）全部被提取到L1 file chunk的imports列表中

### 前置条件

- Chunker类已实现且可导入
- tree-sitter JavaScript解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JS文件，包含3个require()调用（var express, const path, let lodash） | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 获取L1 file chunk的imports列表 | imports列表包含'express', 'path', 'lodash'三个模块路径 |

### 验证点

- L1 file chunk的imports中包含'express'
- L1 file chunk的imports中包含'path'
- L1 file chunk的imports中包含'lodash'

### 后置检查

- 无外部资源需要清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature36JsRequireImports::test_js_require_multiple
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-036-001

### 关联需求

FR-004 (Code Chunking — prototype coexistence with normal constructs)

### 测试目标

验证prototype-assigned function与普通function_declaration和class在同一文件中共存时，所有chunk均被正确产生且互不干扰

### 前置条件

- Chunker类已实现且可导入
- tree-sitter JavaScript解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JS文件，包含1个class（含method）、1个function_declaration、1个prototype-assigned function | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 检查function chunk列表 | 包含prototype fn(symbol='status')、normal fn(symbol='formatDate')、class method(symbol='get') |
| 4 | 检查class chunk列表 | 恰好1个class chunk，symbol='Router' |

### 验证点

- function chunk的symbol集合包含'status'、'formatDate'、'get'
- class chunk的symbol为'Router'
- prototype-assigned function不影响其他chunk的产生

### 后置检查

- 无外部资源需要清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature36JsPrototypeAssign::test_js_prototype_with_normal_functions
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-036-002

### 关联需求

FR-004 (Code Chunking — deep member chain)

### 测试目标

验证深层member_expression链（如`a.b.c.d = function(){}`）正确提取最后一个property_identifier作为symbol

### 前置条件

- Chunker类已实现且可导入
- tree-sitter JavaScript解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JS文件，内容为`a.b.c.d = function() { return 1; };` | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 筛选function chunk | 恰好1个，symbol == 'd' |

### 验证点

- function chunk的symbol为'd'（最后一个property_identifier）

### 后置检查

- 无外部资源需要清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature36JsPrototypeAssign::test_js_deep_member_chain
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-036-003

### 关联需求

FR-004 (Code Chunking — non-function assignment rejection)

### 测试目标

验证非函数赋值（如`obj.x = 42`）不会误报为prototype-assigned function chunk

### 前置条件

- Chunker类已实现且可导入
- tree-sitter JavaScript解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JS文件，内容为`obj.x = 42;` | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 筛选function chunk | 0个function chunk |

### 验证点

- 不产生任何function chunk
- 不报错或崩溃

### 后置检查

- 无外部资源需要清理

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature36JsPrototypeAssign::test_js_non_function_assign_no_chunk
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-036-004

### 关联需求

FR-004 (Code Chunking — scoped package require)

### 测试目标

验证scoped package路径（如`@scope/pkg`）在require()调用中被完整提取

### 前置条件

- Chunker类已实现且可导入
- tree-sitter JavaScript解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JS文件，内容为`const a = require('@scope/pkg');` | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 获取L1 file chunk的imports列表 | imports包含'@scope/pkg' |

### 验证点

- L1 file chunk的imports中包含完整的scoped package路径'@scope/pkg'

### 后置检查

- 无外部资源需要清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature36JsRequireImports::test_js_require_scoped_package
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-036-005

### 关联需求

FR-004 (Code Chunking — dynamic require rejection)

### 测试目标

验证动态require()调用（如`require(dynamicVar)`）不会被误提取为import

### 前置条件

- Chunker类已实现且可导入
- tree-sitter JavaScript解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建JS文件，内容为`const a = require(dynamicVar);` | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 获取L1 file chunk的imports列表 | imports列表为空 |

### 验证点

- L1 file chunk的imports长度为0
- 不报错或崩溃

### 后置检查

- 无外部资源需要清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature36JsRequireImports::test_js_require_dynamic_skipped
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-036-001 | FR-004 | VS-1: res.status = function → L3 symbol='status' | test_js_prototype_function | Real | PASS |
| ST-FUNC-036-002 | FR-004 | VS-2: obj.handler = arrow → L3 symbol='handler' | test_js_prototype_arrow | Real | PASS |
| ST-FUNC-036-003 | FR-004 | VS-3: var express = require('express') → imports includes 'express' | test_js_require_single | Real | PASS |
| ST-FUNC-036-004 | FR-004 | VS-4: multiple require() → all module paths in imports | test_js_require_multiple | Real | PASS |
| ST-BNDRY-036-001 | FR-004 | VS-1,2 (coexistence) | test_js_prototype_with_normal_functions | Real | PASS |
| ST-BNDRY-036-002 | FR-004 | VS-1 (deep chain) | test_js_deep_member_chain | Real | PASS |
| ST-BNDRY-036-003 | FR-004 | VS-1 (negative: non-function) | test_js_non_function_assign_no_chunk | Real | PASS |
| ST-BNDRY-036-004 | FR-004 | VS-3 (scoped package) | test_js_require_scoped_package | Real | PASS |
| ST-BNDRY-036-005 | FR-004 | VS-3,4 (negative: dynamic require) | test_js_require_dynamic_skipped | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 9 |
| Passed | 9 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
