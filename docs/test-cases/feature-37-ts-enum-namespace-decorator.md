# 测试用例集: TypeScript: enum + namespace + decorator unwrapping

**Feature ID**: 37
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

ST-FUNC-037-001

### 关联需求

FR-004 (Code Chunking — TS enum detection)

### 测试目标

验证TypeScript enum声明产生L2 class chunk，symbol为enum名

### 前置条件

- Chunker类已实现且可导入
- tree-sitter TypeScript解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建TS文件，内容为`enum Color { Red, Green, Blue }` | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 筛选chunk_type='class'的chunk | 恰好1个class chunk |
| 4 | 检查该class chunk的symbol字段 | symbol == 'Color' |

### 验证点

- L2 chunk数量为1
- L2 chunk的symbol为'Color'

### 后置检查

- 无外部资源需要清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature37TsEnum::test_ts_enum_produces_l2
- **Test Type**: Real

---

### 用例编号

ST-FUNC-037-002

### 关联需求

FR-004 (Code Chunking — TS namespace class detection)

### 测试目标

验证namespace内的class和method被正确检测并产生L2和L3 chunks

### 前置条件

- Chunker类已实现且可导入
- tree-sitter TypeScript解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建TS文件，内容为`namespace Foo { class Bar { method() {} } }` | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 筛选class和function chunks | L2: Bar, L3: method |

### 验证点

- L2 chunk symbol == 'Bar'
- L3 chunk symbol == 'method'

### 后置检查

- 无外部资源需要清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature37TsNamespace::test_ts_namespace_class_method
- **Test Type**: Real

---

### 用例编号

ST-FUNC-037-003

### 关联需求

FR-004 (Code Chunking — nested namespace detection)

### 测试目标

验证嵌套namespace内的class被正确检测

### 前置条件

- Chunker类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建TS文件，内容为嵌套namespace A > B > class C | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 筛选class chunks | L2 chunk symbol == 'C' |

### 验证点

- 嵌套namespace内的class C被找到

### 后置检查

- 无外部资源需要清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature37TsNamespace::test_ts_nested_namespace
- **Test Type**: Real

---

### 用例编号

ST-FUNC-037-004

### 关联需求

FR-004 (Code Chunking — TS decorator verification)

### 测试目标

验证@Component装饰器修饰的class产生正确的L2 chunk

### 前置条件

- Chunker类已实现且可导入

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建TS文件，内容为`@Component class AppComponent { render() {} }` | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 筛选class和function chunks | L2: AppComponent, L3: render |

### 验证点

- L2 chunk symbol == 'AppComponent'
- L3 chunk symbol == 'render'

### 后置检查

- 无外部资源需要清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature37TsDecorator::test_ts_decorator_class
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-037-001

### 关联需求

FR-004 (Empty namespace)

### 测试目标

验证空namespace不产生多余chunks且不崩溃

### 前置条件

- Chunker类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建TS文件: `namespace Empty {}` | 文件创建成功 |
| 2 | Chunker.chunk() | 无L2/L3 chunks |

### 验证点

- 0个class/function chunks

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature37TsNamespace::test_ts_empty_namespace
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-037-002

### 关联需求

FR-004 (Coexistence)

### 测试目标

验证enum, class, namespace在同一文件中共存

### 前置条件

- Chunker类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建TS文件: enum Status + class Router + namespace Utils { class Helper } | 文件创建成功 |
| 2 | Chunker.chunk() | 所有chunks正确 |
| 3 | 检查class symbols | Status, Router, Helper均出现 |

### 验证点

- enum、class、namespace class均被检测

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature37TsNamespace::test_ts_enum_class_namespace_coexist
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-037-003

### 关联需求

FR-004 (Namespace functions)

### 测试目标

验证namespace内的函数（无class）产生L3 chunks

### 前置条件

- Chunker类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建TS文件: namespace MathUtils { function add() {}, function sub() {} } | 文件创建成功 |
| 2 | Chunker.chunk() | L3 chunks: add, sub |

### 验证点

- function chunks包含add和sub

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature37TsNamespace::test_ts_namespace_functions
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-037-004

### 关联需求

FR-004 (Exported namespace)

### 测试目标

验证export namespace内的class被正确检测

### 前置条件

- Chunker类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建TS文件: `export namespace Foo { class Bar {} }` | 文件创建成功 |
| 2 | Chunker.chunk() | L2 chunk: Bar |

### 验证点

- class Bar在exported namespace中被找到

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature37TsNamespace::test_ts_export_namespace
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-037-005

### 关联需求

FR-004 (Normal TS file unaffected)

### 测试目标

验证无namespace/enum的普通TS文件不受影响

### 前置条件

- Chunker类已实现

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建普通TS文件: class + interface | 文件创建成功 |
| 2 | Chunker.chunk() | 正常chunks |

### 验证点

- 已有的class/interface检测不受影响

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestFeature37TsNamespace::test_ts_normal_file_unaffected
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-037-001 | FR-004 | VS-1: enum → L2 chunk | test_ts_enum_produces_l2 | Real | PASS |
| ST-FUNC-037-002 | FR-004 | VS-2: namespace class → L2 + L3 | test_ts_namespace_class_method | Real | PASS |
| ST-FUNC-037-003 | FR-004 | VS-3: nested namespace → L2 | test_ts_nested_namespace | Real | PASS |
| ST-FUNC-037-004 | FR-004 | VS-4: @Component class → L2 | test_ts_decorator_class | Real | PASS |
| ST-BNDRY-037-001 | FR-004 | VS-2 (empty) | test_ts_empty_namespace | Real | PASS |
| ST-BNDRY-037-002 | FR-004 | VS-1,2 (coexistence) | test_ts_enum_class_namespace_coexist | Real | PASS |
| ST-BNDRY-037-003 | FR-004 | VS-2 (functions only) | test_ts_namespace_functions | Real | PASS |
| ST-BNDRY-037-004 | FR-004 | VS-2 (exported) | test_ts_export_namespace | Real | PASS |
| ST-BNDRY-037-005 | FR-004 | VS-1-4 (no regression) | test_ts_normal_file_unaffected | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 9 |
| Passed | 9 |
| Failed | 0 |
| Pending | 0 |
