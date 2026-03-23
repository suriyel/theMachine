# 测试用例集: Code Chunking

**Feature ID**: 6
**关联需求**: FR-004
**日期**: 2026-03-21
**测试标准**: ISO/IEC/IEEE 29119-3
**模板版本**: 1.0

## 摘要

| 类别 | 用例数 |
|------|--------|
| functional | 11 |
| boundary | 6 |
| real-project | 7 |
| **合计** | **24** |

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

FR-004 (Code Chunking) — JavaScript语言支持

### 测试目标

验证JavaScript文件（含class、method_definition、function_declaration、arrow_function）经chunk_file()处理后产生正确的L1/L2/L3 chunk，包括箭头函数的检测

### 前置条件

- Chunker类已实现且可导入
- tree-sitter JavaScript解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建.js文件，含1个class（含constructor和on方法）、1个顶层function和1个const箭头函数 | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 检查chunk总数 | 共6个chunk（1 L1 + 1 L2 class + 2 L3方法 + 1 L3 function + 1 L3 arrow） |
| 4 | 检查L2 chunk的symbol | symbol == "EventEmitter" |
| 5 | 检查L3 chunk的symbol集合 | 包含constructor、on、formatDate、double |

### 验证点

- class_declaration被识别为L2 chunk
- method_definition被识别为L3 chunk（parent_class=EventEmitter）
- function_declaration被识别为L3顶层函数
- lexical_declaration中的arrow_function被检测为L3 chunk，symbol为变量名"double"
- language字段为"javascript"

### 后置检查

- 无需特殊清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestT6JavaScriptMixed
- **Test Type**: Real

---

### 用例编号

ST-FUNC-006-007

### 关联需求

FR-004 (Code Chunking) — TypeScript语言支持

### 测试目标

验证TypeScript文件（含class和interface）经chunk_file()处理后将interface视为L2 chunk，method_definition视为L3 chunk

### 前置条件

- Chunker类已实现且可导入
- tree-sitter TypeScript解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建.ts文件，含1个interface（Logger）和1个class（ConsoleLogger）各含2个方法 | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 检查chunk总数 | 共5个chunk（1 L1 + 2 L2 + 2 L3） |
| 4 | 检查L2 chunk的symbol集合 | 包含"Logger"和"ConsoleLogger" |
| 5 | 检查language字段 | 所有chunk的language == "typescript" |

### 验证点

- interface_declaration被识别为L2 chunk（与class_declaration同级）
- class内method_definition被识别为L3 chunk
- symbol和signature正确提取

### 后置检查

- 无需特殊清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestT7TypeScriptInterface
- **Test Type**: Real

---

### 用例编号

ST-FUNC-006-008

### 关联需求

FR-004 (Code Chunking) — C语言支持

### 测试目标

验证C语言文件（纯函数，无class）经chunk_file()处理后产生L1和L3 chunk，无L2 chunk，且function_declarator中的标识符被正确提取

### 前置条件

- Chunker类已实现且可导入
- tree-sitter C解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建.c文件，含#include和3个函数（add, subtract, print_result） | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 检查chunk总数 | 共4个chunk（1 L1 + 3 L3） |
| 4 | 检查L2 chunk数量 | 0个（C语言无class_nodes） |
| 5 | 检查L3 chunk的symbol集合 | {"add", "subtract", "print_result"} |

### 验证点

- C的LANGUAGE_NODE_MAPS.class_nodes为空列表 → 无L2产生
- function_definition通过function_declarator提取函数名
- preproc_include被识别为import
- language字段为"c"

### 后置检查

- 无需特殊清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestT8CThreeFunctions
- **Test Type**: Real

---

### 用例编号

ST-FUNC-006-009

### 关联需求

FR-004 (Code Chunking) — C++语言支持

### 测试目标

验证C++文件（含class_specifier、struct_specifier和顶层函数）经chunk_file()处理后正确识别class和struct为L2 chunk，内联方法为L3 chunk

### 前置条件

- Chunker类已实现且可导入
- tree-sitter C++解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建.cpp文件，含1个class（Parser，含parse方法）、1个struct（Token）和2个顶层函数 | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 检查chunk总数 | 共6个chunk（1 L1 + 2 L2 + 3 L3） |
| 4 | 检查L2 chunk的symbol集合 | 包含"Parser"和"Token" |
| 5 | 检查内联方法parse的parent_class | parent_class == "Parser" |

### 验证点

- class_specifier被识别为L2 chunk
- struct_specifier被识别为L2 chunk
- class内function_definition通过field_identifier提取方法名
- 顶层函数通过function_declarator.identifier提取
- language字段为"cpp"

### 后置检查

- 无需特殊清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestT9CppClassStruct
- **Test Type**: Real

---

### 用例编号

ST-FUNC-006-010

### 关联需求

FR-004 (Code Chunking) — Java构造函数和Javadoc支持

### 测试目标

验证Java文件的constructor_declaration被识别为L3 chunk，Javadoc block_comment被提取为doc_comment

### 前置条件

- Chunker类已实现且可导入
- tree-sitter Java解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建.java文件，含1个类（带Javadoc注释），1个构造函数和1个getter方法 | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 检查构造函数是否为L3 chunk | constructor_declaration作为L3 chunk，symbol为类名 |
| 4 | 检查类的doc_comment | 包含Javadoc注释内容"Represents a user entity" |
| 5 | 检查方法的doc_comment | 包含Javadoc注释内容"Returns the user's name" |

### 验证点

- constructor_declaration被映射为L3 function chunk
- block_comment（Javadoc格式）被正确提取为doc_comment
- Javadoc标记（@author, @return等）在清理后保留
- import_declaration被提取为imports

### 后置检查

- 无需特殊清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestT11JavaConstructor, TestT17JavaJavadoc
- **Test Type**: Real

---

### 用例编号

ST-FUNC-006-011

### 关联需求

FR-004 (Code Chunking) — Python docstring和多行签名支持

### 测试目标

验证Python文件的triple-quoted docstring被提取为doc_comment，多行参数签名（带括号换行）被完整捕获

### 前置条件

- Chunker类已实现且可导入
- tree-sitter Python解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建.py文件，含1个类（带docstring）和方法（带docstring），以及1个多行签名函数 | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 检查类L2 chunk的doc_comment | 包含"Formats output strings" |
| 4 | 检查方法L3 chunk的doc_comment | 包含"Make text bold" |
| 5 | 检查多行签名函数的signature | 包含"name: str"、"email: str"、"-> dict" |

### 验证点

- triple-quoted docstring从block > expression_statement > string节点正确提取
- 多行Python签名通过括号深度追踪完整捕获（不会在类型注解中的:处截断）
- import_statement和import_from_statement均被提取为imports

### 后置检查

- 无需特殊清理

### 元数据

- **优先级**: High
- **类别**: functional
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestT16PythonDocstrings, TestT18MultiLineSig, TestT10PythonImports
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

### 用例编号

ST-BNDRY-006-005

### 关联需求

FR-004 (Code Chunking) — .tsx扩展名映射

### 测试目标

验证.tsx文件被映射为TypeScript语言并正确解析，interface和class均被识别

### 前置条件

- Chunker类已实现且可导入
- tree-sitter TypeScript解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建.tsx文件，含1个interface和1个class | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表，至少2个chunk |
| 3 | 检查所有chunk的language字段 | language == "typescript" |
| 4 | 检查L2 chunk是否包含interface | 包含interface作为L2 chunk |

### 验证点

- EXT_TO_LANGUAGE将".tsx"映射为"typescript"
- TypeScript解析器正确处理TSX语法
- interface_declaration和class_declaration均为L2 chunk

### 后置检查

- 无需特殊清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestT25TsxExtension
- **Test Type**: Real

---

### 用例编号

ST-BNDRY-006-006

### 关联需求

FR-004 (Code Chunking) — .h扩展名映射为C语言

### 测试目标

验证.h头文件被映射为C语言并正确解析

### 前置条件

- Chunker类已实现且可导入
- tree-sitter C解析器可用

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 创建.h文件，含#ifndef宏和函数声明 | 文件创建成功 |
| 2 | 调用Chunker.chunk()处理该文件 | 返回chunk列表 |
| 3 | 检查所有chunk的language字段 | language == "c" |

### 验证点

- EXT_TO_LANGUAGE将".h"映射为"c"
- C解析器正确处理头文件语法
- preproc_include（#ifndef等）不干扰解析

### 后置检查

- 无需特殊清理

### 元数据

- **优先级**: Medium
- **类别**: boundary
- **已自动化**: Yes
- **测试引用**: test_chunker.py::TestT39HeaderFile
- **Test Type**: Real

---

### 用例编号

ST-REAL-006-001

### 关联需求

FR-004 (Code Chunking) — 真实项目Python解析

### 测试目标

验证Chunker对pallets/flask sessions.py（含2个类SessionMixin和SecureCookieSession、@property装饰器、多重继承）的chunk结构、符号名称、import提取和docstring正确性

### 前置条件

- Chunker类已实现且可导入
- tree-sitter Python解析器可用
- 代码片段来自GitHub pallets/flask src/flask/sessions.py

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 使用pallets/flask sessions.py真实代码片段创建ExtractedFile | 文件对象创建成功 |
| 2 | 调用Chunker.chunk()处理 | 返回chunk列表 |
| 3 | 检查L1/L2/L3结构 | 1个L1 + 2个L2（SessionMixin, SecureCookieSession） + ≥1个L3 |
| 4 | 检查class symbol_name | 包含"SessionMixin"和"SecureCookieSession" |
| 5 | 检查imports | 包含collections.abc和hashlib |
| 6 | 检查docstring提取 | SessionMixin的doc_comment包含"Expands a basic dictionary" |
| 7 | 检查__init__的parent_class | parent_class == "SecureCookieSession" |

### 验证点

- 真实Flask代码的多重继承类被正确识别为L2
- @property装饰的方法保留在L2类体内（decorated_definition包裹）
- import from ... 语句被正确提取
- triple-quoted docstring正确提取

### 后置检查

- 无需特殊清理

### 元数据

- **优先级**: High
- **类别**: real-project
- **已自动化**: Yes
- **测试引用**: test_chunker_real_projects.py::TestFlaskSessionsPy
- **Test Type**: Real
- **代码来源**: github.com/pallets/flask src/flask/sessions.py

---

### 用例编号

ST-REAL-006-002

### 关联需求

FR-004 (Code Chunking) — 真实项目Java解析

### 测试目标

验证Chunker对spring-projects/spring-framework StringUtils.java（abstract class、static方法、Javadoc注释、@Deprecated注解）的解析正确性

### 前置条件

- Chunker类已实现且可导入
- tree-sitter Java解析器可用
- 代码片段来自GitHub spring-projects/spring-framework StringUtils.java

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 使用Spring StringUtils.java真实代码片段创建ExtractedFile | 文件对象创建成功 |
| 2 | 调用Chunker.chunk()处理 | 返回chunk列表 |
| 3 | 检查chunk结构 | 1个L1 + 1个L2（StringUtils） + ≥3个L3（isEmpty, hasLength, trimLeadingWhitespace） |
| 4 | 检查方法symbol集合 | 包含isEmpty、hasLength、trimLeadingWhitespace |
| 5 | 检查Javadoc提取 | 类L2的doc_comment包含"Miscellaneous"或"String" |
| 6 | 检查imports | 包含java.nio.charset.Charset和java.util.ArrayList |
| 7 | 检查所有方法的parent_class | parent_class == "StringUtils" |

### 验证点

- abstract class被正确识别为L2 chunk
- static方法被正确识别为L3 chunk
- Javadoc block_comment被提取为doc_comment
- import_declaration被正确提取

### 后置检查

- 无需特殊清理

### 元数据

- **优先级**: High
- **类别**: real-project
- **已自动化**: Yes
- **测试引用**: test_chunker_real_projects.py::TestSpringStringUtilsJava
- **Test Type**: Real
- **代码来源**: github.com/spring-projects/spring-framework StringUtils.java

---

### 用例编号

ST-REAL-006-003

### 关联需求

FR-004 (Code Chunking) — 真实项目JavaScript解析

### 测试目标

验证Chunker对expressjs/express response.js（CommonJS require()模式、prototype赋值函数、JSDoc注释）的解析行为——prototype赋值函数回退为L1-only

### 前置条件

- Chunker类已实现且可导入
- tree-sitter JavaScript解析器可用
- 代码片段来自GitHub expressjs/express lib/response.js

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 使用Express response.js真实代码片段创建ExtractedFile | 文件对象创建成功 |
| 2 | 调用Chunker.chunk()处理 | 返回chunk列表 |
| 3 | 检查L1 chunk | 1个L1 chunk，file_path == "lib/response.js" |
| 4 | 检查language | 所有chunk的language == "javascript" |

### 验证点

- CommonJS prototype赋值模式（res.status = function...）不匹配function_declaration
- 回退为L1-only chunk，覆盖整个文件
- require()调用不被误识别为import_statement
- language正确检测为"javascript"

### 后置检查

- 无需特殊清理

### 元数据

- **优先级**: High
- **类别**: real-project
- **已自动化**: Yes
- **测试引用**: test_chunker_real_projects.py::TestExpressResponseJs
- **Test Type**: Real
- **代码来源**: github.com/expressjs/express lib/response.js

---

### 用例编号

ST-REAL-006-004

### 关联需求

FR-004 (Code Chunking) — 真实项目TypeScript解析

### 测试目标

验证Chunker对microsoft/TypeScript compiler/core.ts（export function、泛型函数签名、ES module import）的解析——export_statement内的function_declaration被正确展开为L3 chunk

### 前置条件

- Chunker类已实现且可导入
- tree-sitter TypeScript解析器可用
- 代码片段来自GitHub microsoft/TypeScript src/compiler/core.ts

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 使用TypeScript core.ts真实代码片段创建ExtractedFile | 文件对象创建成功 |
| 2 | 调用Chunker.chunk()处理 | 返回chunk列表 |
| 3 | 检查L3函数数量 | ≥4个L3（length, forEach, forEachRight, firstDefined） |
| 4 | 检查function symbol集合 | 包含"length"、"forEach"、"forEachRight"、"firstDefined" |
| 5 | 检查language | 所有chunk为"typescript" |
| 6 | 检查imports | 包含"_namespaces/ts"路径 |
| 7 | 检查L2 class数量 | 0个（core.ts仅有导出函数） |

### 验证点

- export_statement包裹的function_declaration被正确展开为L3 chunk
- 泛型类型参数（<T, U>）不干扰符号名称提取
- ES module import语句被正确提取
- 无class定义时不产生L2 chunk

### 后置检查

- 无需特殊清理

### 元数据

- **优先级**: High
- **类别**: real-project
- **已自动化**: Yes
- **测试引用**: test_chunker_real_projects.py::TestTypeScriptCoreTs
- **Test Type**: Real
- **代码来源**: github.com/microsoft/TypeScript src/compiler/core.ts

---

### 用例编号

ST-REAL-006-005

### 关联需求

FR-004 (Code Chunking) — 真实项目C语言解析

### 测试目标

验证Chunker对redis/redis adlist.h（C头文件：typedef struct、宏定义、函数声明）的解析——C语言无class_nodes，#ifndef header guard内的#include被正确提取

### 前置条件

- Chunker类已实现且可导入
- tree-sitter C解析器可用
- 代码片段来自GitHub redis/redis src/adlist.h

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 使用Redis adlist.h真实代码片段创建ExtractedFile | 文件对象创建成功 |
| 2 | 调用Chunker.chunk()处理 | 返回chunk列表 |
| 3 | 检查L1 chunk | 1个L1 chunk |
| 4 | 检查language | 所有chunk为"c" |
| 5 | 检查chunk_id格式 | 包含repo_id和branch |
| 6 | 检查L2数量 | 0个（C语言无class_nodes） |

### 验证点

- typedef struct不被识别为class（C的class_nodes为空）
- .h扩展名正确映射为"c"语言
- chunk_id包含repo_id和branch信息
- header guard不干扰解析

### 后置检查

- 无需特殊清理

### 元数据

- **优先级**: High
- **类别**: real-project
- **已自动化**: Yes
- **测试引用**: test_chunker_real_projects.py::TestRedisAdlistH
- **Test Type**: Real
- **代码来源**: github.com/redis/redis src/adlist.h

---

### 用例编号

ST-REAL-006-006

### 关联需求

FR-004 (Code Chunking) — 真实项目C++解析

### 测试目标

验证Chunker对nlohmann/json json_fwd.hpp（C++头文件：template class前向声明、template struct、#include在#ifndef内）的解析——preproc_ifdef内的#include被递归提取

### 前置条件

- Chunker类已实现且可导入
- tree-sitter C++解析器可用
- 代码片段来自GitHub nlohmann/json include/nlohmann/json_fwd.hpp

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 使用nlohmann/json json_fwd.hpp真实代码片段创建ExtractedFile | 文件对象创建成功 |
| 2 | 调用Chunker.chunk()处理 | 返回chunk列表 |
| 3 | 检查language | 所有chunk为"cpp" |
| 4 | 检查chunk数量 | ≥1个（至少L1） |
| 5 | 检查imports | 包含"cstdint"、"map"、"string" |
| 6 | 检查chunk_id格式 | 包含repo_id和branch |

### 验证点

- .hpp扩展名正确映射为"cpp"
- #ifndef包裹的#include通过递归_collect_imports正确提取
- template前向声明不导致解析异常
- chunk_id格式正确

### 后置检查

- 无需特殊清理

### 元数据

- **优先级**: High
- **类别**: real-project
- **已自动化**: Yes
- **测试引用**: test_chunker_real_projects.py::TestNlohmannJsonFwdHpp
- **Test Type**: Real
- **代码来源**: github.com/nlohmann/json include/nlohmann/json_fwd.hpp

---

### 用例编号

ST-REAL-006-007

### 关联需求

FR-004 (Code Chunking) — 真实项目Markdown解析

### 测试目标

验证DocChunker对pallets/flask README.md（H1标题、H2节、fenced code block with language tag、链接引用）的chunk拆分、breadcrumb路径和代码块提取

### 前置条件

- DocChunker类已实现且可导入
- 代码片段来自GitHub pallets/flask README.md

### 测试步骤

| Step | 操作 | 预期结果 |
| ---- | ---- | -------- |
| 1 | 使用Flask README.md真实内容创建ExtractedFile | 文件对象创建成功 |
| 2 | 调用DocChunker.chunk_markdown()处理 | 返回doc chunk列表 |
| 3 | 检查chunk数量 | ≥3个（A Simple Example, Donate, Contributing） |
| 4 | 检查breadcrumb | 包含"A Simple Example"、"Donate"、"Contributing" |
| 5 | 检查code_examples | 包含language=="python"的代码块，含"Flask(__name__)" |
| 6 | 检查H1内容保留 | 全部内容中包含"WSGI"和"web application framework" |
| 7 | 检查chunk_id | 包含repo_id和branch |

### 验证点

- H2标题正确作为拆分点
- H1标题内容保留在首个chunk中
- fenced code block的language标签和代码内容被正确提取
- breadcrumb路径格式正确
- 链接引用语法不干扰解析

### 后置检查

- 无需特殊清理

### 元数据

- **优先级**: High
- **类别**: real-project
- **已自动化**: Yes
- **测试引用**: test_chunker_real_projects.py::TestFlaskReadmeMd
- **Test Type**: Real
- **代码来源**: github.com/pallets/flask README.md

---

## 可追溯矩阵

| 用例 ID | 关联需求 | verification_step | 自动化测试 | Test Type | 结果 |
|---------|----------|-------------------|-----------|---------|------|
| ST-FUNC-006-001 | FR-004 | VS-1: Python class 3 methods → 5 chunks | TestT1PythonClassMethods | Real | PASS |
| ST-FUNC-006-002 | FR-004 | VS-2: Java 2 classes → parent_class tracking | TestT2JavaTwoClasses | Real | PASS |
| ST-FUNC-006-003 | FR-004 | VS-3: Markdown H2 split with breadcrumbs | TestT5ReadmeHeadings | Real | PASS |
| ST-FUNC-006-004 | FR-004 | VS-4: Unsupported language → L1 fallback | TestT4RubyFallback | Real | PASS |
| ST-FUNC-006-005 | FR-004 | Rule extraction with correct type mapping | TestT12-T15 | Real | PASS |
| ST-FUNC-006-006 | FR-004 | JavaScript: class + arrow_function + function | TestT6JavaScriptMixed | Real | PASS |
| ST-FUNC-006-007 | FR-004 | TypeScript: class + interface → L2 | TestT7TypeScriptInterface | Real | PASS |
| ST-FUNC-006-008 | FR-004 | C: 函数通过function_declarator提取名称 | TestT8CThreeFunctions | Real | PASS |
| ST-FUNC-006-009 | FR-004 | C++: class_specifier + struct_specifier → L2 | TestT9CppClassStruct | Real | PASS |
| ST-FUNC-006-010 | FR-004 | Java: constructor + Javadoc doc_comment | TestT11, TestT17 | Real | PASS |
| ST-FUNC-006-011 | FR-004 | Python: docstring + multi-line signature | TestT16, TestT18, TestT10 | Real | PASS |
| ST-BNDRY-006-001 | FR-004 | Empty file → single L1 chunk | TestT19EmptyPythonFile | Real | PASS |
| ST-BNDRY-006-002 | FR-004 | 501-line function → overlapping windows | TestT22Function501Lines | Real | PASS |
| ST-BNDRY-006-003 | FR-004 | No headings → [section N] fallback | TestT26NoHeadings | Real | PASS |
| ST-BNDRY-006-004 | FR-004 | Syntax errors → error-tolerant parsing | TestT24SyntaxError | Real | PASS |
| ST-BNDRY-006-005 | FR-004 | .tsx → TypeScript语言映射 | TestT25TsxExtension | Real | PASS |
| ST-BNDRY-006-006 | FR-004 | .h → C语言映射 | TestT39HeaderFile | Real | PASS |
| ST-REAL-006-001 | FR-004 | Flask sessions.py: 多重继承类 + @property + docstring | TestFlaskSessionsPy | Real | PASS |
| ST-REAL-006-002 | FR-004 | Spring StringUtils.java: abstract class + Javadoc + static方法 | TestSpringStringUtilsJava | Real | PASS |
| ST-REAL-006-003 | FR-004 | Express response.js: CommonJS prototype赋值回退 | TestExpressResponseJs | Real | PASS |
| ST-REAL-006-004 | FR-004 | TS compiler core.ts: export function展开 + 泛型 | TestTypeScriptCoreTs | Real | PASS |
| ST-REAL-006-005 | FR-004 | Redis adlist.h: C头文件 typedef struct + header guard | TestRedisAdlistH | Real | PASS |
| ST-REAL-006-006 | FR-004 | nlohmann json_fwd.hpp: C++ template + #ifndef内#include | TestNlohmannJsonFwdHpp | Real | PASS |
| ST-REAL-006-007 | FR-004 | Flask README.md: H2拆分 + fenced code block提取 | TestFlaskReadmeMd | Real | PASS |

## Real Test Case Execution Summary

| Metric | Count |
|--------|-------|
| Total Real Test Cases | 24 |
| Passed | 24 |
| Failed | 0 |
| Pending | 0 |

> Real test cases = test cases with Test Type `Real` (executed against a real running environment, not Mock).
> Any Real test case FAIL blocks the feature from being marked `"passing"` — must be fixed and re-executed.
