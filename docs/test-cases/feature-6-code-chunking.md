# 测试用例集: Code Chunking

**Feature ID**: 6
**关联需求**: FR-004
**日期**: 2026-03-21
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 6 |
| boundary | 4 |
| **合计** | **10** |

---

### 用例编号

ST-FUNC-006-001

### 关联需求

FR-004 (Code Chunking)

### 测试目标

验证Python文件（1个类含3个方法）经chunk_file()处理后产生正确的L1/L2/L3层级chunk结构及符号名称和签名

### 前置条件

- Chunker类已实现且可导入
- tree-sitter Python解析器可用
- 临时目录包含含1个类和3个方法的Python文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Python文件，包含1个类定义和3个方法 | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 检查chunk总数 | 共5个chunk（1个L1文件级 + 1个L2类级 + 3个L3方法级） |
| 4 | 检查L1 chunk的类型和内容 | level=1，覆盖整个文件 |
| 5 | 检查L2 chunk的symbol_name | 包含类名 |
| 6 | 检查3个L3 chunk的symbol_name和signature | 每个方法的名称和签名正确 |

### 验证点

- 返回5个chunk对象
- L1 chunk覆盖文件级别，level=1
- L2 chunk包含正确的类名，level=2
- 3个L3 chunk各自包含正确的方法名和签名，level=3
- 所有chunk的parent关系正确

### 后置检查

- 临时目录自动清理（pytest tmp_path fixture）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestT1PythonClassMethods
- **Test Type**: Real

---

### 用例编号

ST-FUNC-006-002

### 关联需求

FR-004 (Code Chunking)

### 测试目标

验证Java文件（含2个类）经chunk_file()处理后产生正确的chunk结构，且方法级chunk的parent_class字段正确设置

### 前置条件

- Chunker类已实现且可导入
- tree-sitter Java解析器可用
- 临时目录包含含2个类和5个方法的Java文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Java文件，包含2个类定义和共5个方法 | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 检查chunk总数 | 共8个chunk（1个L1 + 2个L2 + 5个L3） |
| 4 | 检查每个L3方法chunk的parent_class字段 | 正确指向其所属类名 |
| 5 | 检查L2类chunk的symbol_name | 2个类名正确 |

### 验证点

- 返回8个chunk对象
- L1 chunk level=1，覆盖文件级别
- 2个L2 chunk分别对应两个类
- 5个L3 chunk的parent_class字段正确指向其所属类
- 各chunk的symbol_name正确

### 后置检查

- 临时目录自动清理（pytest tmp_path fixture）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestT2JavaTwoClasses
- **Test Type**: Real

---

### 用例编号

ST-FUNC-006-003

### 关联需求

FR-004 (Code Chunking)

### 测试目标

验证Markdown文件（含H1/H2/H3标题）经chunk_markdown()处理后按H2级别拆分，生成包含面包屑路径的doc chunk

### 前置条件

- DocChunker类已实现且可导入
- 临时目录包含含H1、H2、H3标题层级的README.md

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建README.md，包含H1标题、H2标题（如Getting Started）、H3子标题（如Installation） | 文件创建成功 |
| 2 | 调用DocChunker.chunk_markdown()处理该文件 | 返回doc chunk列表 |
| 3 | 检查chunk拆分级别 | 按H2级别拆分 |
| 4 | 检查面包屑路径 | 包含"Getting Started > Installation"格式的breadcrumb trail |

### 验证点

- chunk按H2标题级别拆分
- 面包屑路径格式正确，包含"Installation"
- H3子标题内容归属于其父H2 chunk
- 每个chunk包含正确的标题层级信息

### 后置检查

- 临时目录自动清理（pytest tmp_path fixture）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_doc_chunker.py::TestT5ReadmeHeadings
- **Test Type**: Real

---

### 用例编号

ST-FUNC-006-004

### 关联需求

FR-004 (Code Chunking)

### 测试目标

验证不支持语言的文件经chunk_file()处理后回退为L1文件级chunk

### 前置条件

- Chunker类已实现且可导入
- 临时目录包含不支持语言的.rb文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Ruby文件（.rb），包含有效的Ruby代码 | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 检查chunk数量 | 仅1个chunk |
| 4 | 检查chunk级别 | level=1（L1文件级回退） |

### 验证点

- 返回1个chunk对象
- chunk level=1，为文件级回退
- 无异常抛出
- chunk内容覆盖整个文件

### 后置检查

- 临时目录自动清理（pytest tmp_path fixture）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestT4RubyFallback
- **Test Type**: Real

---

### 用例编号

ST-FUNC-006-005

### 关联需求

FR-004 (Code Chunking)

### 测试目标

验证RuleExtractor能正确提取CLAUDE.md、CONTRIBUTING.md、.editorconfig等规则文件并映射正确的rule_type

### 前置条件

- RuleExtractor类已实现且可导入
- 临时目录包含CLAUDE.md、CONTRIBUTING.md、.editorconfig文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建CLAUDE.md文件，包含项目规则 | 文件创建成功 |
| 2 | 创建CONTRIBUTING.md文件，包含贡献指南 | 文件创建成功 |
| 3 | 创建.editorconfig文件，包含编辑器配置 | 文件创建成功 |
| 4 | 调用RuleExtractor.extract_rules()处理各文件 | 返回规则对象列表 |
| 5 | 检查各文件的rule_type映射 | CLAUDE.md、CONTRIBUTING.md、.editorconfig分别映射正确的rule_type |

### 验证点

- CLAUDE.md被正确识别并提取规则
- CONTRIBUTING.md被正确识别并提取规则
- .editorconfig被正确识别并提取规则
- 各文件的rule_type映射正确

### 后置检查

- 临时目录自动清理（pytest tmp_path fixture）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_rule_extractor.py::TestT12ClaudeMd, TestT13ContributingMd, TestT14EditorConfig
- **Test Type**: Real

---

### 用例编号

ST-FUNC-006-006

### 关联需求

FR-004 (Code Chunking)

### 测试目标

验证6种支持语言（Python, Java, JavaScript, TypeScript, C, C++）均能产生正确的L1/L2/L3层级chunk结构

### 前置条件

- Chunker类已实现且可导入
- tree-sitter各语言解析器可用
- 临时目录包含6种语言的代码文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Python (.py)、Java (.java)、JavaScript (.js)、TypeScript (.ts)、C (.c)、C++ (.cpp) 文件，各含类/函数定义 | 6个文件创建成功 |
| 2 | 对每个文件调用Chunker.chunk() | 每个文件返回chunk列表 |
| 3 | 检查每个文件的chunk层级结构 | 各文件均含L1（文件级）、L2（类/结构体级）、L3（方法/函数级）chunk |
| 4 | 检查symbol_name和signature正确性 | 各语言的符号名称和签名格式正确 |

### 验证点

- 6种语言均能成功解析
- 每种语言产生正确的L1/L2/L3层级结构
- symbol_name和signature格式符合各语言规范
- 无解析异常

### 后置检查

- 临时目录自动清理（pytest tmp_path fixture）

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestT1, TestT2, TestT6, TestT7, TestT8, TestT9
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-006-001

### 关联需求

FR-004 (Code Chunking)

### 测试目标

验证空Python文件经chunk处理后产生单个L1 chunk，imports和symbols为空

### 前置条件

- Chunker类已实现且可导入
- 临时目录包含空的.py文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建空的.py文件（0字节） | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 检查chunk数量 | 仅1个chunk |
| 4 | 检查chunk级别 | level=1（L1文件级） |
| 5 | 检查imports和symbols字段 | 均为空 |

### 验证点

- 返回1个chunk对象
- chunk level=1
- imports列表为空
- symbols列表为空
- 无异常抛出

### 后置检查

- 临时目录自动清理（pytest tmp_path fixture）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestT19EmptyPythonFile
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-006-002

### 关联需求

FR-004 (Code Chunking)

### 测试目标

验证超过500行的大函数被拆分为带50行重叠的多个L3 chunk窗口

### 前置条件

- Chunker类已实现且可导入
- 临时目录包含含501行函数的Python文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Python文件，包含一个501行的函数 | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 检查L3 chunk数量 | 至少2个L3 chunk |
| 4 | 检查相邻L3 chunk的行范围重叠 | 存在50行重叠区域 |

### 验证点

- 501行函数被拆分为2个L3 chunk
- 相邻chunk之间存在50行重叠
- 每个chunk的行范围正确
- L1文件级chunk仍存在

### 后置检查

- 临时目录自动清理（pytest tmp_path fixture）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestT22Function501Lines
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-006-003

### 关联需求

FR-004 (Code Chunking)

### 测试目标

验证无标题的Markdown文件经chunk_markdown()处理后使用段落回退策略，breadcrumb格式为[section N]

### 前置条件

- DocChunker类已实现且可导入
- 临时目录包含仅含段落（无标题）的.md文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建.md文件，仅包含段落文本（无H1/H2/H3标题） | 文件创建成功 |
| 2 | 调用DocChunker.chunk_markdown()处理该文件 | 返回doc chunk列表 |
| 3 | 检查chunk的breadcrumb格式 | 包含"[section N]"格式的面包屑 |

### 验证点

- 无标题文件不会导致异常
- chunk使用段落回退策略
- breadcrumb格式为[section N]
- 文件内容完整覆盖

### 后置检查

- 临时目录自动清理（pytest tmp_path fixture）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_doc_chunker.py::TestT26NoHeadings
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-006-004

### 关联需求

FR-004 (Code Chunking)

### 测试目标

验证含语法错误的Python文件经chunk处理后仍能产生chunk（tree-sitter容错解析）

### 前置条件

- Chunker类已实现且可导入
- 临时目录包含含语法错误的Python文件

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建Python文件，包含语法错误（如缺少冒号、括号不匹配） | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表，无异常 |
| 3 | 检查chunk是否产生 | 至少包含L1文件级chunk |

### 验证点

- 语法错误不导致异常抛出
- tree-sitter容错解析生效
- 至少产生L1文件级chunk
- 可识别的函数/类仍被正确分块

### 后置检查

- 临时目录自动清理（pytest tmp_path fixture）

### 元数据

- **优先级**: High
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestT24SyntaxError
- **Test Type**: Real

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-006-001 | FR-004 | VS-1: Python class 3 methods → 5 chunks | TestT1PythonClassMethods | Real | PASS |
| ST-FUNC-006-002 | FR-004 | VS-2: Java 2 classes → parent_class tracking | TestT2JavaTwoClasses | Real | PASS |
| ST-FUNC-006-003 | FR-004 | VS-3: Markdown H2 split with breadcrumbs | TestT5ReadmeHeadings | Real | PASS |
| ST-FUNC-006-004 | FR-004 | VS-4: Unsupported language → L1 fallback | TestT4RubyFallback | Real | PASS |
| ST-FUNC-006-005 | FR-004 | Rule extraction with correct type mapping | TestT12ClaudeMd, TestT13ContributingMd, TestT14EditorConfig | Real | PASS |
| ST-FUNC-006-006 | FR-004 | Six languages produce correct L1/L2/L3 chunks | TestT1, TestT2, TestT6, TestT7, TestT8, TestT9 | Real | PASS |
| ST-BNDRY-006-001 | FR-004 | Empty file → single L1 chunk | TestT19EmptyPythonFile | Real | PASS |
| ST-BNDRY-006-002 | FR-004 | 501-line function → overlapping windows | TestT22Function501Lines | Real | PASS |
| ST-BNDRY-006-003 | FR-004 | No headings → [section N] fallback | TestT26NoHeadings | Real | PASS |
| ST-BNDRY-006-004 | FR-004 | Syntax errors → error-tolerant parsing | TestT24SyntaxError | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 10 |
| Passed | 10 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
