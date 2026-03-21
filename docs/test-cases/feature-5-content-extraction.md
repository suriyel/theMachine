# 测试用例集: Content Extraction

**Feature ID**: 5
**关联需求**: FR-003（Content Extraction）
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

ST-FUNC-005-001

### 关联需求

FR-003（Content Extraction）

### 测试目标

验证ContentExtractor能正确按扩展名分类源代码文件（.py, .java, .js, .ts, .c, .cpp）为CODE类型

### 前置条件

- ContentExtractor类已实现且可导入
- 临时目录包含各语言的源代码文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建临时目录，写入app.py、Main.java、index.js、app.ts、main.c、lib.cpp | 6个文件创建成功 |
| 2 | 实例化ContentExtractor并调用extract(tmp_dir) | 返回list[ExtractedFile] |
| 3 | 检查返回列表长度 | 长度为6 |
| 4 | 检查每个ExtractedFile的content_type | 全部为ContentType.CODE |
| 5 | 检查每个ExtractedFile的content字段 | 内容与写入的文本一致 |

### 验证点

- 返回6个ExtractedFile对象
- 所有文件的content_type均为ContentType.CODE
- 每个ExtractedFile的content包含正确的文件内容
- 每个ExtractedFile的path为相对路径

### 后置检查

- 临时目录自动清理（pytest tmp_path fixture）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_content_extraction.py::test_classifies_source_files_by_extension
- **Test Type**: Real

---

### 用例编号

ST-FUNC-005-002

### 关联需求

FR-003（Content Extraction）

### 测试目标

验证ContentExtractor能正确分类文档文件（README.md, docs/**/*.md）、示例文件（examples/**/*）和规则文件（CLAUDE.md, CONTRIBUTING.md）

### 前置条件

- ContentExtractor类已实现且可导入
- 临时目录包含各类型文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建临时目录，包含README.md, docs/guide.md, examples/demo.py, CLAUDE.md, CONTRIBUTING.md | 文件和目录创建成功 |
| 2 | 调用extract(tmp_dir) | 返回list[ExtractedFile] |
| 3 | 检查DOC类型文件 | README.md和docs/guide.md分类为DOC |
| 4 | 检查EXAMPLE类型文件 | examples/demo.py分类为EXAMPLE |
| 5 | 检查RULE类型文件 | CLAUDE.md和CONTRIBUTING.md分类为RULE |

### 验证点

- README.md → ContentType.DOC
- docs/guide.md → ContentType.DOC
- examples/demo.py → ContentType.EXAMPLE
- CLAUDE.md → ContentType.RULE
- CONTRIBUTING.md → ContentType.RULE

### 后置检查

- 临时目录自动清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_content_extraction.py::test_classifies_doc_files, test_classifies_example_files, test_classifies_rule_files
- **Test Type**: Real

---

### 用例编号

ST-FUNC-005-003

### 关联需求

FR-003（Content Extraction）

### 测试目标

验证ContentExtractor跳过不支持的文件类型（无错误）

### 前置条件

- 临时目录包含不支持类型的文件（.csv, Makefile, .yaml）

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建临时目录，写入data.csv、Makefile、config.yaml | 文件创建成功 |
| 2 | 调用extract(tmp_dir) | 返回空列表 |
| 3 | 验证无异常抛出 | extract()正常返回 |

### 验证点

- 返回空列表（长度0）
- 无异常抛出
- 不支持的文件被静默跳过

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_content_extraction.py::test_skips_unknown_file_types
- **Test Type**: Real

---

### 用例编号

ST-FUNC-005-004

### 关联需求

FR-003（Content Extraction）

### 测试目标

验证ContentExtractor在遇到不可读文件（编码错误）时记录警告并跳过，不中断整个作业

### 前置条件

- 临时目录包含非UTF-8编码的.py文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建临时目录，写入包含Latin-1字节的.py文件 | 文件创建成功 |
| 2 | 调用extract(tmp_dir)并捕获日志 | 返回空列表 |
| 3 | 检查日志输出 | 包含"skipping"或"unreadable"警告信息 |

### 验证点

- 返回空列表（文件被跳过）
- 日志包含警告信息
- 无异常传播到调用方

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: tests/test_content_extraction.py::test_skips_non_utf8_file
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-005-001

### 关联需求

FR-003（Content Extraction）

### 测试目标

验证ContentExtractor跳过大于1MB的文件，包含恰好1MB的文件

### 前置条件

- 临时目录包含两个.py文件：一个恰好1MB（1_048_576字节），一个1MB+1字节

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建恰好1_048_576字节的.py文件 | 文件大小恰好1MB |
| 2 | 创建1_048_577字节的.py文件 | 文件大小为1MB+1 |
| 3 | 调用extract(tmp_dir)并捕获日志 | 返回1个ExtractedFile |
| 4 | 检查返回的文件 | 是1MB文件，size=1_048_576 |
| 5 | 检查日志 | 包含关于超大文件的警告 |

### 验证点

- 恰好1MB的文件被包含（边界值内）
- 1MB+1字节的文件被跳过
- 跳过时记录警告日志

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_content_extraction.py::test_includes_file_exactly_1mb, test_skips_file_over_1mb
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-005-002

### 关联需求

FR-003（Content Extraction）

### 测试目标

验证ContentExtractor跳过二进制文件（通过null字节检测）并跳过.git隐藏目录

### 前置条件

- 临时目录包含二进制文件和.git子目录

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建包含null字节的.py文件 | 文件写入成功 |
| 2 | 创建.git/config文件 | .git目录和文件创建成功 |
| 3 | 创建正常的main.py文件 | 文件写入成功 |
| 4 | 调用extract(tmp_dir) | 返回1个ExtractedFile（仅main.py） |
| 5 | 检查返回文件 | 路径为main.py，类型为CODE |

### 验证点

- 二进制.py文件被跳过（null字节检测生效）
- .git目录内容被跳过（隐藏目录过滤生效）
- 正常文件被正确提取

### 后置检查

- 无

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_content_extraction.py::test_skips_binary_code_file, test_skips_hidden_directories
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-005-003

### 关联需求

FR-003（Content Extraction）

### 测试目标

验证ContentExtractor处理空目录和零字节文件的边界条件

### 前置条件

- 一个空的临时目录，以及一个包含0字节.py文件的临时目录

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 对空目录调用extract() | 返回空列表 |
| 2 | 创建0字节的empty.py文件 | 文件创建成功 |
| 3 | 调用extract()在包含empty.py的目录上 | 返回1个ExtractedFile |
| 4 | 检查ExtractedFile字段 | content=""，size=0，content_type=CODE |

### 验证点

- 空目录返回空列表，无异常
- 0字节文件被包含（不被误判为二进制）
- 0字节文件的content为空字符串，size为0

### 后置检查

- 无

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: tests/test_content_extraction.py::test_empty_directory_returns_empty_list, test_includes_zero_byte_text_file
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-005-001 | FR-003 | VS-1: classify .py, .java, .md, .png by type | test_classifies_source_files_by_extension | Real | PASS |
| ST-FUNC-005-002 | FR-003 | VS-1: classify doc, example, rule types | test_classifies_doc_files, test_classifies_example_files, test_classifies_rule_files | Real | PASS |
| ST-FUNC-005-003 | FR-003 | VS-2: skip unsupported file types | test_skips_unknown_file_types | Real | PASS |
| ST-FUNC-005-004 | FR-003 | VS-4: log warning and skip unreadable files | test_skips_non_utf8_file | Real | PASS |
| ST-BNDRY-005-001 | FR-003 | VS-2: skip files >1MB | test_includes_file_exactly_1mb, test_skips_file_over_1mb | Real | PASS |
| ST-BNDRY-005-002 | FR-003 | VS-3: skip binary files | test_skips_binary_code_file, test_skips_hidden_directories | Real | PASS |
| ST-BNDRY-005-003 | FR-003 | VS-1/VS-2: empty dir and zero-byte file | test_empty_directory_returns_empty_list, test_includes_zero_byte_text_file | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 7 |
| Passed | 7 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
