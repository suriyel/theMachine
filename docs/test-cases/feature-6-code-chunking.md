# Test Case Document — Feature #6: Code Chunking with tree-sitter (FR-004)

**Feature ID**: 6
**Feature Title**: Code Chunking with tree-sitter (FR-004)
**Related Requirements**: FR-004
**Date**: 2026-03-15
**Standard**: ISO/IEC/IEEE 29119-3

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 2 |
| boundary | 2 |
| security | 0 |
| accessibility | 0 |
| performance | 0 |
| **合计** | **4** |

## 测试用例块

---

### 用例编号

ST-FUNC-006-001

### 关联需求

FR-004 (Code Chunking)

### 测试目标

验证 Java 代码多粒度分块：2 个类，每个类 3 个方法

### 前置条件

1. CodeChunker 模块可导入
2. tree-sitter-java 已安装

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 创建包含 2 个类（每个类 3 个方法）的 Java 代码的 RawContent | RawContent 对象创建成功 |
| 2 | 实例化 CodeChunker | 对象创建成功 |
| 3 | 调用 chunker.chunk(raw_content) | 返回 CodeChunk 列表 |
| 4 | 验证总块数 | 恰好 9 个块（1 个文件级 + 2 个类级 + 6 个方法级） |
| 5 | 验证存在文件级块 | 一个块的 chunk_type = FILE |
| 6 | 验证类级块 | 两个块的 chunk_type = CLASS |
| 7 | 验证方法级块 | 六个块的 chunk_type = FUNCTION |
| 8 | 验证块内容包含代码 | 每个块都有非空内容 |

### 验证点

- Java 文件正确生成 9 个块
- 块类型分布正确：1 文件 + 2 类 + 6 方法

### 后置检查

无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_chunker.py::test_java_chunking_creates_file_class_and_method_chunks
- **Test Type**: Real

**实际结果:** Java 分块生成 1 个文件 + 2 个类 + 6 个方法 = 9 个块。所有块类型正确识别。

**结果:** PASS

---

### 用例编号

ST-FUNC-006-002

### 关联需求

FR-004 (Code Chunking)

### 测试目标

验证 Python 代码分块及正确的行号范围

### 前置条件

1. CodeChunker 模块可导入
2. tree-sitter-python 已安装

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 创建包含 4 个函数和 2 个类的 Python 代码的 RawContent | RawContent 对象创建成功 |
| 2 | 实例化 CodeChunker | 对象创建成功 |
| 3 | 调用 chunker.chunk(raw_content) | 返回 CodeChunk 列表 |
| 4 | 验证至少 7 个块 | 至少 1 个文件 + 2 个类 + 4 个函数 = 7 个块 |
| 5 | 验证文件级块行号范围正确 | start_line >= 1, end_line >= start_line |
| 6 | 验证类块行号范围有效 | start_line < end_line |
| 7 | 验证函数块行号范围有效 | start_line < end_line |
| 8 | 验证所有块都有内容 | 每个块都有非空内容 |

### 验证点

- Python 代码正确生成文件、类和函数块
- 行号范围正确

### 后置检查

无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_chunker.py::test_python_chunking_creates_file_class_and_function_chunks
- **Test Type**: Real

**实际结果:** Python 分块生成文件、类和函数块，具有有效的行号范围。生成了 7+ 个块。

**结果:** PASS

---

### 用例编号

ST-BNDRY-006-001

### 关联需求

FR-004 (Code Chunking)

### 测试目标

验证不支持的语言回退到文件级分块

### 前置条件

1. CodeChunker 模块可导入

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 创建 Ruby 代码且 language="ruby" 的 RawContent | RawContent 对象创建成功 |
| 2 | 实例化 CodeChunker | 对象创建成功 |
| 3 | 调用 chunker.chunk(raw_content) | 返回 CodeChunk 列表 |
| 4 | 验证恰好 1 个块 | 列表长度 = 1 |
| 5 | 验证块是文件级 | chunk_type = FILE |
| 6 | 验证无符号分解 | symbol_name 为 None 或空 |
| 7 | 验证内容完整保留 | chunk.content 等于原始内容 |

### 验证点

- 不支持的语言正确回退到单文件级块
- 无符号提取

### 后置检查

无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_chunker.py::test_unsupported_language_fallback_creates_single_file_chunk
- **Test Type**: Real

**实际结果:** 不支持的语言（Ruby）正确回退到单文件级块，无符号提取。

**结果:** PASS

---

### 用例编号

ST-BNDRY-006-002

### 关联需求

FR-004 (Code Chunking)

### 测试目标

验证 TypeScript 类型信息提取

### 前置条件

1. CodeChunker 模块可导入
2. tree-sitter-typescript 已安装

### 测试步骤

| Step | 操作 | 预期结果 |
|------|------|----------|
| 1 | 创建包含接口和类型别名的 TypeScript 代码的 RawContent | RawContent 对象创建成功 |
| 2 | 实例化 CodeChunker | 对象创建成功 |
| 3 | 调用 chunker.chunk(raw_content) | 返回 CodeChunk 列表 |
| 4 | 验证至少 3 个块 | 至少 1 个文件 + 接口 + 类型 |
| 5 | 验证接口块 | 至少一个块的 chunk_type = INTERFACE |
| 6 | 验证类型块 | 至少一个块的 chunk_type = TYPE |
| 7 | 验证符号名称被捕获 | symbol_name 为接口/类型块填充 |
| 8 | 验证类型信息包含 | symbol_type = "interface" 或 "type" |

### 验证点

- TypeScript 正确提取接口和类型别名块
- 符号名称和类型正确

### 后置检查

无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_chunker.py::test_typescript_chunking_includes_type_information
- **Test Type**: Real

**实际结果:** TypeScript 分块提取接口和类型别名块，具有正确的符号名称和类型。

**结果:** PASS

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|-----------|------|
| ST-FUNC-006-001 | FR-004 | VS-1: Java 2 classes x 3 methods | tests/test_chunker.py::test_java_chunking_creates_file_class_and_method_chunks | Real | PASS |
| ST-FUNC-006-002 | FR-004 | VS-2: Python 4 functions + 2 classes | tests/test_chunker.py::test_python_chunking_creates_file_class_and_function_chunks | Real | PASS |
| ST-BNDRY-006-001 | FR-004 | VS-3: Unsupported language fallback | tests/test_chunker.py::test_unsupported_language_fallback_creates_single_file_chunk | Real | PASS |
| ST-BNDRY-006-002 | FR-004 | VS-4: TypeScript interfaces/types | tests/test_chunker.py::test_typescript_chunking_includes_type_information | Real | PASS |

## Real Test Case Execution Summary

| Metric | Value |
|--------|-------|
| Total Real Test Cases | 4 |
| Passed | 4 |
| Failed | 0 |
| Pending | 0 |

## Execution Notes

- This is a backend-only feature (not UI) - no Chrome DevTools MCP testing required
- Test cases verify CodeChunker behavior through direct Python API calls
- All tests use tree-sitter parsers (real parsing, not mocked)
- The TDD unit tests already provide comprehensive coverage; ST adds acceptance-level verification
- All 4 verification steps are covered by test cases
