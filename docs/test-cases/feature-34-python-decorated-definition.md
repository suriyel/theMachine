# 测试用例集: Python: decorated_definition Unwrapping

**Feature ID**: 34
**关联需求**: FR-004 (Wave 2, acceptance criterion 5)
**日期**: 2026-03-21
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 4 |
| boundary | 3 |
| **合计** | **7** |

---

### 用例编号

ST-FUNC-034-001

### 关联需求

FR-004（Code Chunking — @property decorated functions produce L3 chunks）

### 测试目标

Verify that @property-decorated getter and @property.setter-decorated setter methods inside a class produce L3 function chunks with correct symbol and parent_class.

### 前置条件

- Chunker initialized
- Python tree-sitter grammar available

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create Python file with class Foo containing @property def name(self) and @name.setter def name(self, val) | File created |
| 2 | Run chunker.chunk() on the file | Chunks produced without error |
| 3 | Filter chunks by chunk_type == "function" and symbol == "name" | Exactly 2 function chunks found (getter + setter) |
| 4 | Verify parent_class on both chunks | Both have parent_class == "Foo" |

### 验证点

- Exactly 2 L3 chunks with symbol="name" are produced
- Both chunks have parent_class="Foo"
- No error or fallback to file-level chunking

### 后置检查

- None required (stateless operation)

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_feature_34_decorated_definition.py::TestPropertyDecorators::test_property_getter_produces_l3_with_parent_class, test_feature_34_decorated_definition.py::TestPropertyDecorators::test_property_setter_produces_l3_with_parent_class
- **Test Type**: Real

---

### 用例编号

ST-FUNC-034-002

### 关联需求

FR-004（Code Chunking — @staticmethod/@classmethod produce L3 chunks）

### 测试目标

Verify that @staticmethod and @classmethod decorated functions inside a class produce L3 function chunks with correct parent_class.

### 前置条件

- Chunker initialized
- Python tree-sitter grammar available

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create Python file with class Svc containing @staticmethod def create() and @classmethod def from_config(cls) | File created |
| 2 | Run chunker.chunk() on each file | Chunks produced |
| 3 | Filter for function chunks with symbol "create" | 1 L3 chunk with parent_class="Svc" |
| 4 | Filter for function chunks with symbol "from_config" | 1 L3 chunk with parent_class="Svc" |

### 验证点

- @staticmethod function → L3 chunk with symbol="create", parent_class="Svc"
- @classmethod function → L3 chunk with symbol="from_config", parent_class="Svc"

### 后置检查

- None required

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_feature_34_decorated_definition.py::TestStaticAndClassMethod::test_staticmethod_produces_l3_with_parent_class, test_feature_34_decorated_definition.py::TestStaticAndClassMethod::test_classmethod_produces_l3_with_parent_class
- **Test Type**: Real

---

### 用例编号

ST-FUNC-034-003

### 关联需求

FR-004（Code Chunking — @dataclass decorated class produces L2 chunk）

### 测试目标

Verify that a @dataclass-decorated class produces an L2 class chunk with correct symbol name.

### 前置条件

- Chunker initialized
- Python tree-sitter grammar available

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create Python file with @dataclass class Config containing host: str and port: int fields | File created |
| 2 | Run chunker.chunk() | Chunks produced |
| 3 | Filter chunks by chunk_type == "class" | Exactly 1 class chunk found |
| 4 | Verify symbol name | symbol == "Config" |

### 验证点

- @dataclass class produces L2 chunk with symbol="Config"
- Decorator does not prevent class detection

### 后置检查

- None required

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_feature_34_decorated_definition.py::TestDecoratedClass::test_dataclass_decorated_class_produces_l2
- **Test Type**: Real

---

### 用例编号

ST-FUNC-034-004

### 关联需求

FR-004（Code Chunking — @app.route top-level decorated function produces L3 chunk with empty parent_class）

### 测试目标

Verify that a top-level @app.route('/') decorated function produces an L3 chunk with empty parent_class and decorator text preserved in content.

### 前置条件

- Chunker initialized
- Python tree-sitter grammar available

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create Python file with @app.route('/') def index() at top level | File created |
| 2 | Run chunker.chunk() | Chunks produced |
| 3 | Filter for function chunks with symbol "index" | Exactly 1 function chunk found |
| 4 | Verify parent_class | parent_class == "" (empty — top-level) |
| 5 | Verify chunk content | Content includes "@app.route" decorator text |

### 验证点

- L3 chunk with symbol="index" and parent_class="" produced
- Decorator text "@app.route('/')" is preserved in the chunk content

### 后置检查

- None required

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_feature_34_decorated_definition.py::TestTopLevelDecoratedFunction::test_app_route_top_level_produces_l3_no_parent, test_feature_34_decorated_definition.py::TestTopLevelDecoratedFunction::test_decorated_chunk_content_includes_decorator
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-034-001

### 关联需求

FR-004（Code Chunking — stacked decorators）

### 测试目标

Verify that a function with multiple stacked decorators produces a single L3 chunk with all decorator text preserved.

### 前置条件

- Chunker initialized
- Python tree-sitter grammar available

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create Python file with @decorator1 @decorator2 def multi() | File created |
| 2 | Run chunker.chunk() | Chunks produced |
| 3 | Filter for function chunks with symbol "multi" | Exactly 1 function chunk |
| 4 | Verify content includes both decorators | "@decorator1" and "@decorator2" both present |

### 验证点

- Stacked decorators produce exactly 1 L3 chunk (not duplicated)
- Both decorator texts preserved in chunk content

### 后置检查

- None required

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_feature_34_decorated_definition.py::TestBoundaryEdgeCases::test_stacked_decorators_produce_l3
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-034-002

### 关联需求

FR-004（Code Chunking — no regression on plain functions）

### 测试目标

Verify that adding decorated_definition unwrapping does not break existing behavior for plain (non-decorated) functions and classes.

### 前置条件

- Chunker initialized
- Python tree-sitter grammar available

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create Python file with plain def foo(), def bar(), and class Baz with method() | File created |
| 2 | Run chunker.chunk() | Chunks produced |
| 3 | Filter for function chunks | foo, bar, method all present |
| 4 | Filter for class chunks | Baz present |

### 验证点

- Plain functions produce L3 chunks as before
- Plain class produces L2 chunk as before
- No regression from decorated_definition handling

### 后置检查

- None required

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_feature_34_decorated_definition.py::TestBoundaryEdgeCases::test_plain_functions_no_regression
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-034-003

### 关联需求

FR-004（Code Chunking — decorated class with methods）

### 测试目标

Verify that a @dataclass class with methods produces both L2 class chunk and L3 method chunks with correct parent_class.

### 前置条件

- Chunker initialized
- Python tree-sitter grammar available

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | Create Python file with @dataclass class Config with fields and def validate(self) | File created |
| 2 | Run chunker.chunk() | Chunks produced |
| 3 | Filter for class chunks | 1 class chunk with symbol="Config" |
| 4 | Filter for function chunks with symbol "validate" | 1 function chunk with parent_class="Config" |

### 验证点

- Decorated class produces L2 chunk
- Method inside decorated class produces L3 chunk with correct parent_class
- Both class and method extraction work together

### 后置检查

- None required

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_feature_34_decorated_definition.py::TestBoundaryEdgeCases::test_decorated_class_with_methods
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-034-001 | FR-004 | VS-1: @property getter/setter → L3 with parent_class | test_property_getter/setter | Real | PASS |
| ST-FUNC-034-002 | FR-004 | VS-2: @staticmethod/@classmethod → L3 with parent_class | test_staticmethod/classmethod | Real | PASS |
| ST-FUNC-034-003 | FR-004 | VS-3: @dataclass class → L2 chunk | test_dataclass_decorated_class | Real | PASS |
| ST-FUNC-034-004 | FR-004 | VS-4: @app.route top-level → L3, empty parent_class | test_app_route_top_level | Real | PASS |
| ST-BNDRY-034-001 | FR-004 | VS-4 (boundary) | test_stacked_decorators | Real | PASS |
| ST-BNDRY-034-002 | FR-004 | (regression) | test_plain_functions_no_regression | Real | PASS |
| ST-BNDRY-034-003 | FR-004 | VS-3 (boundary) | test_decorated_class_with_methods | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 7 |
| Passed | 7 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
