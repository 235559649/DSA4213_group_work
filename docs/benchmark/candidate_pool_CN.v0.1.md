# Group 25：SWE-bench Verified 开发候选池 v0.1

整理日期：2026-10-12。名单状态：`shortlist_complete`（20 道开发候选已补齐）。

本文件给出完整的 20 道开发题候选名单：Django 6 道、SymPy 6 道、Sphinx 4 道、pytest 4 道。原有 12 道保留，新增 8 道补足既定配额。题目、任务元数据及官方历史环境清单均已核对；尚未构建镜像、启动任务、确认修复前失败或运行官方评估。名单筛选已完成，实际可运行性仍待验证。

这里的 20 道是用于开发和预实验的完整名单，不是 proposal 中另行保留的最多 100 道正式评价题。正式评价题需要另外选择，避免使用已经用于开发调试的任务。

## 1. 数据来源与筛选范围

- 数据集：`SWE-bench/SWE-bench_Verified`。
- 数据集 revision：`78f471bf655a3137b2e8a75af1501690ec009ec3`。
- 配置与 split：`default` / `test`。从该 split 另外划分小组自己的开发题和正式评价题。
- 数据文件：`data/test-00000-of-00001.parquet`。
- 四个仓库共有 369 道任务：Django 231、SymPy 75、Sphinx 44、pytest 19。
- 本轮依据原始 `problem_statement`、任务版本、人工难度标签和环境清单筛选；没有使用 `patch`、`test_patch`、`FAIL_TO_PASS`、`PASS_TO_PASS` 或 `hints_text` 进行选题。
- 所有题号均已在上述固定数据版本中核对。原题保持原样，A–D 使用相同原始输入。

数据来源：[固定版本的数据集目录](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/tree/78f471bf655a3137b2e8a75af1501690ec009ec3)。

环境清单来源：[SWE-bench 官方资源目录](https://github.com/SWE-bench/SWE-bench/tree/02e7a74ffd0b707aab73d203fe87bdc7c76afc8e/swebench/resources/swebench-og)。该仓库快照仅用于本轮静态环境信息核对，不代表团队已经采用或验证了这一 Harness 版本。

## 2. 统一环境的约定建议

采用统一的运行与评估流程，并保留每道题的 benchmark 指定环境。这与 proposal 3.2 的任务容器设计一致。

| 层次 | 统一内容 | 允许的任务差异 |
|---|---|---|
| 执行平台 | 固定 Linux/WSL2、Docker 版本与资源设置；记录硬件和并发规则 | 不按 A–D 改变同一道题的资源配置 |
| Agent 与评估控制环境 | 固定兼容的控制端 Python、mini-SWE-agent、Harness、模型、工具接口、公共提示及预算 | 四种条件只改变 proposal 规定的定位上下文 |
| 任务容器 | 同一道题固定镜像 digest、源码 `base_commit`、依赖和测试环境；A–D 每次从相同干净状态开始 | 不同题可以使用不同 Python 和依赖版本 |

**公平比较的单位是同一道题上的 A–D。** 例如某道 Django 题的四个条件都使用该题的同一个容器；某道 SymPy 题的四个条件使用另一个固定容器。所有条件再在同一批任务上进行配对比较。

不直接将所有历史项目升级到同一个 Python 版本。这样可能造成旧依赖安装失败、运行行为变化或额外修复需求，改变原本的题目。若小组另做统一任务 Python 的实验，应单独定义与验证，不能将其当作官方任务环境结果。

本轮查到的 `environment.yml` 中：Django 的 11133、12262、13158、13417 四道题记录 Python 3.6.13；14017、14539 两道题记录 Python 3.8.20；其余 14 道记录 Python 3.9.20。它们是历史环境清单记录，不是当前实际容器中的 `python --version`。运行前须结合团队选定的 Harness、镜像及有效配置核对并记录实际版本。也不能仅因两题的 Python 版本相同就认定完整环境相同。

控制端 Python 和库版本暂记为 `to_be_pinned`；实际容器 digest、CPU/内存限制、测试入口及构建结果暂未验证，不在本文件中虚填。

参考：[官方 Docker 环境说明](https://www.swebench.com/SWE-bench/guides/docker_setup/)、[官方评价说明](https://www.swebench.com/SWE-bench/guides/evaluation/)。

## 3. 候选共有记录

以下字段适用于全部 20 道候选，逐题记录继承这些值：

| 字段 | 值与含义 |
|---|---|
| `dataset` | `SWE-bench/SWE-bench_Verified` |
| `dataset_revision` | `78f471bf655a3137b2e8a75af1501690ec009ec3` |
| `intended_use` | `development_candidate`：完整开发候选名单，实际运行资格待环境检查 |
| `selection_status` | `shortlist_complete`：20 道候选筛选完成，环境检查另行记录 |
| `environment_manifest_status` | `inspected`：已静态阅读清单 |
| `environment_check_status` | `not_checked`：实际环境尚未运行验证 |
| `evaluation_status` | `not_run` |
| `exclusion_reason` | `null`：当前没有排除，不等于已通过全部可行性检查 |
| `has_localization_hint` | `yes`：按下面的宽口径标注，待小组复核后冻结 |
| `annotation_status` | `proposed`：本轮提出的标注 |

线索口径：原题中出现明确文件、类、函数、堆栈、代码片段或修改方向即标记为 `yes`；复现代码也计入本轮既有宽口径。`annotation_basis` 只依据原始题目，不依据参考修复。该标记不衡量线索强弱，也不意味着知道真实修改位置。

因此，本轮候选池适合开发验证，不能代表有线索/无线索均衡的正式样本。正式选题时另外检查线索分布，先报告全部任务 A–D 结果，再报告子组结果。

`version` 是数据集里的仓库版本分组，不保证等于原题作者报告的精确发行版本；以 `base_commit` 固定初始源码。

`difficulty` 直接读取官方数据集的人工难度标注。官方要求标注者估计：一位有经验、已用几小时熟悉该代码库的软件工程师，需要多少时间确定并实现修复。每题由三位独立标注者评价，难度按多数意见汇总；没有多数意见时取中位档位。四档为 `<15 min fix`、`15 min - 1 hour`、`1-4 hours`、`>4 hours`。

这些标签是人工估计的时间分组，不是逐题实测耗时，也不是 Agent 运行时长或预算。它们可用于描述和分层分析候选难度；Agent 的预算仍依据开发预实验中实际记录的步数、Token、费用和耗时确定。来源：[官方标注方法与难度定义](https://openai.com/index/introducing-swe-bench-verified/#our-approach)。

## 4. Django 候选

### D1：django__django-11133

- `instance_id`：`django__django-11133`
- `repo`：`django/django`
- `base_commit`：`879cc3da6249e920b8d54518a0ae06de835d7373`
- `version`：`3.0`
- `environment_setup_commit`：`419a78300f7cd27611196e1e464d50fd0385ff27`
- `difficulty`：`<15 min fix`
- 原题摘要：HttpResponse 接收 memoryview 时，输出内存对象描述，而不是原始字节内容。
- 选择理由：原文比较字符串、字节与 memoryview 三类输入，实际/预期差异清楚；适合首先验证词法检索、候选上下文和修复评估闭环。
- 场景：明确复现、错误输出，无完整项目异常栈。
- `annotation_basis`：原题包含 HttpResponse 类名及三类输入的复现代码。
- 环境风险：原文提及 PostgreSQL，但也提供直接构造 memoryview 的示例；不能据背景描述预先认定必须部署数据库服务，须核对任务环境。
- 建议优先级：第一批。

### D2：django__django-12262

- `instance_id`：`django__django-12262`
- `repo`：`django/django`
- `base_commit`：`69331bb851c34f05bc77e9fc24020fe6908b9cd5`
- `version`：`3.1`
- `environment_setup_commit`：`0668164b4ac93a5be79f5b87fae83c657124d9ab`
- `difficulty`：`15 min - 1 hour`
- 原题摘要：模板标签使用带默认值的 keyword-only 参数时被错误拒绝；重复参数报错也不正确。
- 选择理由：小型复现展示模板调用与 Python 参数处理之间的关系，适合观察 Agent 是否能从表面报错追踪到负责处理的代码。
- 场景：明确复现、异常消息、组件间交互；没有完整 traceback。
- `annotation_basis`：原文含 register.simple_tag、标签函数定义和模板调用片段，并提及 inclusion tag。
- 环境风险：需要模板编译/渲染测试；原题涉及两类标签，不能仅核对单一入口。
- 建议优先级：第二批。

### D3：django__django-13158

- `instance_id`：`django__django-13158`
- `repo`：`django/django`
- `base_commit`：`7af8f4127397279d19ef7c7899e93018274e2f9b`
- `version`：`3.2`
- `environment_setup_commit`：`65dfb06a1ab56c238cc80f5e1c31f61210c4577d`
- `difficulty`：`15 min - 1 hour`
- 原题摘要：用 union() 查询作为表单选项时，空提交反而关联了全部匹配对象。
- 选择理由：用户看到的错误在表单层，题意同时涉及查询和多对多关系，适合开发结构关系索引及跨组件定位。
- 场景：跨组件交互、错误结果，无完整 traceback。
- `annotation_basis`：标题包含 QuerySet.none()，正文给出 ModelForm、ModelMultipleChoiceField 与 union() 的复现代码。
- 环境风险：需要模型及数据库状态；按任务规定的数据库与测试环境验证，不自行升级后端。
- 建议优先级：第二批。

### D4：django__django-13417

- `instance_id`：`django__django-13417`
- `repo`：`django/django`
- `base_commit`：`71ae1ab0123582cc5bfe0f7d5f4cc19a9412f396`
- `version`：`3.2`
- `environment_setup_commit`：`65dfb06a1ab56c238cc80f5e1c31f61210c4577d`
- `difficulty`：`<15 min fix`
- 原题摘要：带默认排序的模型做分组聚合后，SQL 已无 ORDER BY，但 QuerySet.ordered 仍返回 True。
- 选择理由：对比 QuerySet 的状态属性和实际生成 SQL，补充查询元数据与执行语义不一致的场景；用于词法定位和查询组件之间结构联系的开发检查。
- 场景：明确代码/SQL 对照、错误状态，无完整 traceback。
- `annotation_basis`：原文包含 QuerySet.ordered、Meta.ordering、annotate 和生成 SQL 的示例。
- 环境风险：需要数据库与模型状态；原文使用 PostgreSQL，须先检查官方任务后端，不能提前承诺所有后端行为相同。

### D5：django__django-14017

- `instance_id`：`django__django-14017`
- `repo`：`django/django`
- `base_commit`：`466920f6d726eee90d5566e0a9948e92b33a122e`
- `version`：`4.0`
- `environment_setup_commit`：`475cffd1d64c690cdad16ede4d5e81985738ceb4`
- `difficulty`：`15 min - 1 hour`
- 原题摘要：Exists(...) & Q(...) 可以执行，调换为 Q(...) & Exists(...) 后抛出 TypeError。
- 选择理由：短复现对照操作数顺序，并给出项目异常栈，补充 Django 侧的失败路径映射与表达式组件交互检查。
- 场景：完整短 traceback、操作顺序差异、组件交互。
- `annotation_basis`：原文含 django/db/models/query_utils.py、__and__、_combine 和反向运算方法的猜测。
- 环境风险：需要任务模型与指定后端；官方清单记录 Python 3.8.20，不与旧 Django 任务强行合并环境。

### D6：django__django-14539

- `instance_id`：`django__django-14539`
- `repo`：`django/django`
- `base_commit`：`6a5ef557f80a8eb6a758ebe99c8bb477ca47459e`
- `version`：`4.0`
- `environment_setup_commit`：`475cffd1d64c690cdad16ede4d5e81985738ceb4`
- `difficulty`：`<15 min fix`
- 原题摘要：urlize() 处理 HTML 转义文本与末尾标点时，生成链接周围的文字不正确。
- 选择理由：补充数据库之外的文本处理场景，输入、实际输出和预期输出都短而明确，适合词法定位和精确回归验证。
- 场景：错误字符串输出、边界输入，无 traceback。
- `annotation_basis`：原文直接给出 urlize() 调用以及实际/预期 HTML。
- 环境风险：文本转链接不等于访问网站；先用本地字符串复现，并检查转义与标点行为。

## 5. SymPy 候选

### M1：sympy__sympy-23262

- `instance_id`：`sympy__sympy-23262`
- `repo`：`sympy/sympy`
- `base_commit`：`fdc707f73a65a429935c01532cd3970d3355eab6`
- `version`：`1.11`
- `environment_setup_commit`：`9a6104eab0ea7ac191a09c24f3e2d79dcd66bda5`
- `difficulty`：`15 min - 1 hour`
- 原题摘要：生成单元素元组的 Python 代码时遗漏逗号，导致返回值成为整数。
- 选择理由：输出差异容易理解；从 lambdify 操作观察代码打印结果，适合检查用户入口与处理位置之间的联系。
- 场景：明确复现、错误输出、组件间交互，无完整 traceback。
- `annotation_basis`：原文包含 lambdify、inspect.getsource 和单元素/多元素元组示例。
- 环境风险：核对任务指定的 mpmath 等依赖；验证应区分单元素和多元素行为。
- 建议优先级：第一批。

### M2：sympy__sympy-17630

- `instance_id`：`sympy__sympy-17630`
- `repo`：`sympy/sympy`
- `base_commit`：`58e78209c8577b9890e957b624466e5beed7eb08`
- `version`：`1.5`
- `environment_setup_commit`：`70381f282f2d9d039da860e391fe51649df2779d`
- `difficulty`：`1-4 hours`
- 原题摘要：含零矩阵块的 BlockMatrix 连续相乘时抛出 AttributeError。
- 选择理由：题目包含经过矩阵处理和策略执行的多层调用栈，适合检验项目内路径映射、结构关系和失败事件提取。
- 场景：完整 traceback、多层调用、对象类型差异。
- `annotation_basis`：原题包含 blockmatrix.py、strategies/core.py、_blockmul 等位置和符号，并指出 Zero/ZeroMatrix 的差异。
- 环境风险：人工难度较高；不把数学算法理解困难误记为环境故障，不因某条件失败而排除题目。
- 建议优先级：第三批。

### M3：sympy__sympy-21379

- `instance_id`：`sympy__sympy-21379`
- `repo`：`sympy/sympy`
- `base_commit`：`624217179aaf8d094e6ff75b7493ad1ee47599b0`
- `version`：`1.9`
- `environment_setup_commit`：`f9a6f50ec0c74d935c50a6e9c9b2cb0469570d91`
- `difficulty`：`15 min - 1 hour`
- 原题摘要：对特定分段表达式执行 subs() 时抛出 PolynomialError，清缓存后首次执行与再次执行表现不同。
- 选择理由：复现涉及表达式、假设和缓存状态，可以检验 Agent 是否准确复现失败，并开发状态敏感的失败记录。
- 场景：异常消息、状态敏感复现、组件间交互；原文没有完整 traceback。
- `annotation_basis`：原题包含 clear_cache、Piecewise、subs、real=True 等复现代码。
- 环境风险：必须控制缓存和执行顺序；原文已给出 SymPy 最小例子，不因背景提及 TensorFlow 就认定必须安装它。
- 建议优先级：第二批。

### M4：sympy__sympy-19346

- `instance_id`：`sympy__sympy-19346`
- `repo`：`sympy/sympy`
- `base_commit`：`94fb720696f5f5d12bad8bc813699fd696afd2fb`
- `version`：`1.7`
- `environment_setup_commit`：`cffd4e0f86fefd4802349a9f9b19ed70934ea354`
- `difficulty`：`15 min - 1 hour`
- 原题摘要：srepr() 正确表示列表/元组中的符号，却没有正确表示字典/集合里的符号。
- 选择理由：将不同容器类型的行为进行直接对照，补充递归打印与实体检索的开发场景；数学背景需求相对少。
- 场景：明确输出对照、多种容器输入，无 traceback。
- `annotation_basis`：原文提供 srepr() 对 list、tuple、dict、set 的调用与输出。
- 环境风险：集合输出顺序需要适当处理，不能仅把排列差异当作错误；保留任务指定 SymPy 与 mpmath 依赖。

### M5：sympy__sympy-20154

- `instance_id`：`sympy__sympy-20154`
- `repo`：`sympy/sympy`
- `base_commit`：`bdb49c4abfb35554a3c8ce761696ffff3bb837fe`
- `version`：`1.7`
- `environment_setup_commit`：`cffd4e0f86fefd4802349a9f9b19ed70934ea354`
- `difficulty`：`15 min - 1 hour`
- 原题摘要：partitions() 迭代器重复使用同一个输出字典，收集输出后出现令人意外的结果。
- 选择理由：补充对象别名和迭代状态问题，检查 Agent 能否区分单次输出与保存全部输出后的行为，避免只验证最表面的结果。
- 场景：状态/对象共享、行为描述，原文未给出完整复现或 traceback。
- `annotation_basis`：原文点名 sympy.utilities.iterables、partitions()，并提出复制字典的方向。
- 环境风险：原文 list(partitions()) 是概括性表达；复现需要提供实际参数，并检查保存下来的多个输出是否共享对象。

### M6：sympy__sympy-20438

- `instance_id`：`sympy__sympy-20438`
- `repo`：`sympy/sympy`
- `base_commit`：`33b47e4bd60e2302e42616141e76285038b724d6`
- `version`：`1.8`
- `environment_setup_commit`：`3ac1464b8840d5f8b618a654f9fbf09c452fe969`
- `difficulty`：`15 min - 1 hour`
- 原题摘要：ProductSet 和 FiniteSet 的子集判断不一致，对相等关系做 simplify() 又出现 AttributeError。
- 选择理由：同一原题包含错误返回值和跨模块异常栈，适合同时开发词法候选、结构联系与运行失败证据映射。
- 场景：返回值异常、跨模块 traceback、集合与关系运算交互。
- `annotation_basis`：原文含 is_subset、ProductSet、FiniteSet，以及 core/basic.py、simplify/simplify.py、core/relational.py 栈帧。
- 环境风险：原例可能返回不确定值；不能将 None 与 False 混为一谈。按原始源码复现，不访问原文链接里的后续修复。

已有 `sympy__sympy-15599` 试跑继续保留在已有开发证据中，不计入本轮 20 道候选，也不用于正式保留评价。

## 6. Sphinx 候选

### S1：sphinx-doc__sphinx-8595

- `instance_id`：`sphinx-doc__sphinx-8595`
- `repo`：`sphinx-doc/sphinx`
- `base_commit`：`b19bce971e82f2497d67fdacdeca8db08ae0ba56`
- `version`：`3.5`
- `environment_setup_commit`：`4f8cb861e3b29186b38248fe81e4944fd987fcce`
- `difficulty`：`<15 min fix`
- 原题摘要：模块设置 __all__ = [] 后，autodoc 仍展示其中的函数。
- 选择理由：小型模块与文档片段即可表达问题，期望是没有成员条目，适合首先验证文档工具的运行闭环。
- 场景：明确复现、错误输出，无完整 traceback。
- `annotation_basis`：原文包含 __all__、模块函数、automodule 文档片段及 sphinx.ext.autodoc 扩展名称。
- 环境风险：需要实际生成文档；导入成功不等于问题已修复。旧 Sphinx 与 docutils/Jinja2 的配套关系需按官方环境核验。
- 建议优先级：第一批。

### S2：sphinx-doc__sphinx-7462

- `instance_id`：`sphinx-doc__sphinx-7462`
- `repo`：`sphinx-doc/sphinx`
- `base_commit`：`b3e26a6c851133b82b50f4b68b53692076574d13`
- `version`：`3.1`
- `environment_setup_commit`：`5afc77ee27fc01c57165ab260d3a76751f9ddb35`
- `difficulty`：`<15 min fix`
- 原题摘要：空元组类型注解 Tuple[()] 导致文档构建出现 IndexError。
- 选择理由：边界输入与短异常栈都清楚，适合核对失败解析和项目内路径映射。
- 场景：traceback、边界输入、明确复现。
- `annotation_basis`：原文直接出现 sphinx/domains/python.py、unparse 及 Tuple[()] 示例。
- 环境风险：类型注解行为和文档依赖有版本差异，不能换到最新版本后验证历史题。
- 建议优先级：第二批。

### S3：sphinx-doc__sphinx-9673

- `instance_id`：`sphinx-doc__sphinx-9673`
- `repo`：`sphinx-doc/sphinx`
- `base_commit`：`5fb51fb1467dc5eea7505402c3c5d9b378d3b441`
- `version`：`4.3`
- `environment_setup_commit`：`6c6cc8a6f50b18331cb818160d168d7bb9c03e55`
- `difficulty`：`15 min - 1 hour`
- 原题摘要：autodoc 的类型提示配置与 Napoleon 配合使用时，返回类型没有出现在生成文档中。
- 选择理由：涉及两个扩展的共同工作，适合检查结构关系与候选上下文是否有助于理解组件交互。
- 场景：跨扩展交互、错误输出，无完整 traceback。
- `annotation_basis`：原题列出 autodoc_typehints_description_target、autodoc/Napoleon 扩展及 docstring 片段。
- 环境风险：需要同时启用有关扩展并核对生成内容；不必因此完整下载原文提及的外部项目。
- 建议优先级：第二批。

### S4：sphinx-doc__sphinx-8721

- `instance_id`：`sphinx-doc__sphinx-8721`
- `repo`：`sphinx-doc/sphinx`
- `base_commit`：`82ef497a8c88f0f6e50d84520e7276bfbf65025d`
- `version`：`3.5`
- `environment_setup_commit`：`4f8cb861e3b29186b38248fe81e4944fd987fcce`
- `difficulty`：`<15 min fix`
- 原题摘要：连续构建 HTML 和 EPUB 时，即使 viewcode_enable_epub=False，EPUB 仍产生源码页面。
- 选择理由：补充不同构建器和扩展之间的状态/配置交互，检查系统是否仅验证第一次构建而漏掉后续行为。
- 场景：多阶段构建、配置行为、错误输出，无 traceback。
- `annotation_basis`：原文给出 sphinx.ext.viewcode、viewcode_enable_epub 和 make html epub。
- 环境风险：需要按顺序构建 HTML 和 EPUB；应检查 EPUB 产物是否包含源码页，不能只看命令退出状态。

## 7. pytest 候选

### P1：pytest-dev__pytest-7571

- `instance_id`：`pytest-dev__pytest-7571`
- `repo`：`pytest-dev/pytest`
- `base_commit`：`422685d0bdc110547535036c1ff398b5e1c44145`
- `version`：`6.0`
- `environment_setup_commit`：`634cde9506eb1f48dec3ec77974ee8dc952207c6`
- `difficulty`：`15 min - 1 hour`
- 原题摘要：一个测试通过 caplog 修改日志级别后，下一个测试仍受到影响。
- 选择理由：两个短测试即可展示跨测试状态泄漏，适合分析状态恢复和生命周期；错误可以通过结果差异观察。
- 场景：跨测试状态、执行顺序、错误结果，无完整 traceback。
- `annotation_basis`：原文包含 caplog.set_level、caplog.handler.level 和两个复现测试。
- 环境风险：复现依赖执行顺序；只单独运行第二个测试可能看不到问题。核对历史 pluggy 等依赖。
- 建议优先级：第一批。

### P2：pytest-dev__pytest-7205

- `instance_id`：`pytest-dev__pytest-7205`
- `repo`：`pytest-dev/pytest`
- `base_commit`：`5e7f1ab4bf58e473e5d7f878eb2b499d7deabd29`
- `version`：`5.4`
- `environment_setup_commit`：`678c1a0745f1cf175c442c719906a1f13e496910`
- `difficulty`：`<15 min fix`
- 原题摘要：字节参数配合 --setup-show，在 Python -bb 模式下触发 BytesWarning。
- 选择理由：触发条件明确，原文完整堆栈同时包含 pytest 和 pluggy，适合核对项目代码/依赖代码区分与失败路径映射。
- 场景：完整异常栈、运行参数敏感、明确复现。
- `annotation_basis`：原题包含 src/_pytest/setuponly.py 等项目栈帧、字节参数示例，并提出 saferepr 修改方向。
- 环境风险：必须保留 -bb；普通运行可能不触发。错误来自本题触发条件，不能自动归类为环境错误。
- 建议优先级：第二批。

### P3：pytest-dev__pytest-7490

- `instance_id`：`pytest-dev__pytest-7490`
- `repo`：`pytest-dev/pytest`
- `base_commit`：`7f7a36478abe7dd1fa993b115d22606aa0e35e88`
- `version`：`6.0`
- `environment_setup_commit`：`634cde9506eb1f48dec3ec77974ee8dc952207c6`
- `difficulty`：`15 min - 1 hour`
- 原题摘要：测试运行过程中动态添加 xfail 标记后，失败没有按预期被处理。
- 选择理由：题目比较不同版本的结果分类，涉及标记、执行和报告阶段，适合观察组件交互以及失败语义理解。
- 场景：跨执行阶段、错误结果分类、测试失败输出；不是完整项目 traceback。
- `annotation_basis`：原文包含 request.node.add_marker、pytest.mark.xfail 及复现测试和结果输出。
- 环境风险：复现里的断言失败是刻意制造的；目标是正确分类，不能将消除断言当作修复。不要照搬原文作者的大型个人依赖列表。
- 建议优先级：第二批。

### P4：pytest-dev__pytest-10356

- `instance_id`：`pytest-dev__pytest-10356`
- `repo`：`pytest-dev/pytest`
- `base_commit`：`3c1534944cbd34e8a41bc9e76818018fadefc9a1`
- `version`：`7.2`
- `environment_setup_commit`：`572b5657d7ca557593418ce0319fabff88800c73`
- `difficulty`：`1-4 hours`
- 原题摘要：测试类多重继承两个带标记的基类时，部分继承标记丢失。
- 选择理由：补充类结构与标记收集场景，检查索引能否保留类/方法提示、Agent 能否理解 MRO；作为结构方法能力边界的开发案例。
- 场景：多重继承、结果/标记缺失，原文包含较长的 workaround 和重复描述，无完整项目 traceback。
- `annotation_basis`：原文提供 pytestmark、__mro__、多个基类和测试类的示例及 metaclass workaround。
- 环境风险：原文含 Python 2 风格 metaclass 写法，复现须适配任务运行解释器，原始 Issue 不改写；不要照搬作者的 workaround 就视为完成修复。
- 方法边界：当前 C 只融合一跳内部导入关系，不解析 MRO；不能把本题与继承相关就当作 C 已支持继承图或必然受益。

pytest 的修复目标是测试框架本身。业务索引范围应包含 `src/_pytest`，不能因项目名称带 pytest 就当成测试目录排除。

## 8. 覆盖范围与优先顺序

| 目标场景 | 代表候选 |
|---|---|
| 描述明确、实际和预期容易比较 | D1、D4、D6、M1、M4、S1 |
| 组件间交互 | D3、D4、D5、M1、M6、S3、S4、P3 |
| 原题包含项目异常栈 | D5、M2、M6、S2、P2 |
| 没有完整项目异常栈，主要依靠错误结果复现 | D1、D4、D6、M1、M4、S1、S4、P1 |
| 状态或执行顺序影响复现 | M3、M5、S4、P1 |
| 类结构与现有静态方法的能力边界 | P4 |

类别可重叠；所有“跨组件”判断只根据原题，不宣称实际修复必然跨文件。任务描述里的异常栈也不等于 D 在运行过程中一定产生了新的可用失败证据，须另行记录真实覆盖情况。

建议先核验 D1、M1、S1、P1 四道任务的环境和复现链路，再逐步扩展其余候选。M2 放在后面。不依据 A–D 谁成功或谁失败决定是否保留正式任务。

### 8.1 每道候选与小组研究方法的对应关系

小组的核心问题是：额外的定位信息，能否让 Agent 更准确地找到相关代码，并改善修复结果或减少探索成本？以下对应关系是开发阶段的验证目标和待验证假设，不是已验证的增强效果，也不预设 C、D 在这些题上优于 A、B。

A 是原始 mini-SWE-agent，全部候选都需要 A 作为对照。B 用 BM25 将 Issue 文字匹配到代码实体并形成文件排名；C 在词法排名基础上通过静态可解析的一跳内部导入邻居生成结构排名，再进行融合；D 将运行过程中真实产生的可用失败证据映射回索引，并更新候选排名。

| 候选任务 | 主要验证目标 | 与小组选题的具体对应 |
|---|---|---|
| D1：`django__django-11133` | B＋完整流程 | 从 HttpResponse、memoryview 等词找到相关实体；实际与预期差异清楚，便于首先验证修复与独立评估链路。 |
| D2：`django__django-12262` | B；C 场景候选 | 从模板标签和参数报错进入源码；检查标签入口与参数处理位置之间是否存在可利用的结构联系。 |
| D3：`django__django-13158` | C 场景候选 | 用户看到的是表单提交错误，题意同时涉及查询和模型关系；适合检查候选是否能沿结构关系向相关组件扩展。 |
| D4：`django__django-13417` | B；C 场景候选 | 对比查询状态属性与生成 SQL，检查查询元数据和编译组件之间的联系。 |
| D5：`django__django-14017` | D；C 场景候选 | 操作数顺序触发 TypeError，补充 Django 项目异常栈映射与表达式组件交互。 |
| D6：`django__django-14539` | B＋回归评价 | 短字符串输入和预期 HTML 明确，补充非数据库文本处理场景。 |
| M1：`sympy__sympy-23262` | B；C 场景候选 | 用户调用 lambdify，错误表现为生成代码不正确；检查能否从用户入口找到代码打印相关组件。 |
| M2：`sympy__sympy-17630` | D＋失败解析 | 多层异常栈适合验证路径、函数和异常类型提取，以及真实运行失败后对候选排名的更新。 |
| M3：`sympy__sympy-21379` | D＋准确复现 | 缓存和执行顺序影响异常；检查系统是否准确记录真实失败，并在有可用证据时重排，避免无法复现时错误更新。 |
| M4：`sympy__sympy-19346` | B＋回归评价 | 对比不同容器中的符号打印，检查相关实体检索和容器行为覆盖。 |
| M5：`sympy__sympy-20154` | 状态复现＋回归评价 | 迭代器共享字典导致保存结果异常，检查对象别名和多次输出行为。 |
| M6：`sympy__sympy-20438` | B；C/D 场景候选 | 集合关系同时出现错误返回和跨模块异常栈，检查实体检索、结构联系与动态失败映射。 |
| S1：`sphinx-doc__sphinx-8595` | B＋完整流程 | 从 __all__、autodoc 等标识符检索源码，再通过实际生成的文档核对修复行为。 |
| S2：`sphinx-doc__sphinx-7462` | D＋路径映射 | 短异常栈和边界输入，适合先验证报错位置能否正确映射到代码索引。 |
| S3：`sphinx-doc__sphinx-9673` | C 场景候选 | 涉及 autodoc 与 Napoleon 的协作；检查扩展间的结构信息是否能补充词法候选。 |
| S4：`sphinx-doc__sphinx-8721` | 状态复现；C 场景候选 | 多格式连续构建涉及扩展和构建器，检查结构联系及后续产物验证。 |
| P1：`pytest-dev__pytest-7571` | 状态复现＋回归评价 | 错误跨越两个测试；检查 Agent 是否识别状态泄漏，以及复现和评价是否保留所需执行顺序。 |
| P2：`pytest-dev__pytest-7205` | D＋依赖边界识别 | 堆栈同时出现 pytest 和 pluggy；检查失败解析能否区分项目源码和外部依赖，再映射回项目索引。 |
| P3：`pytest-dev__pytest-7490` | 失败语义；C 场景候选 | 断言失败是刻意制造的，目标是正确处理 xfail；检查系统是否理解失败分类，以及标记、执行和报告阶段之间的联系。 |
| P4：`pytest-dev__pytest-10356` | B＋索引能力边界 | 类和标记识别可测试；当前 C 不解析 MRO，仅能检查可用的包含和导入信息，不预设继承相关增益。 |

### 8.2 对应关系的验证边界

**C 的边界：跨组件题意不等于结构增强已经有效。** 当前 C 使用一跳内部导入关系，没有完整调用图。角色 2 需要在固定初始源码上检查：词法候选附近是否确实存在可解析的导入邻居，结构排名是否产生有用候选，以及融合后的排名如何变化。不能仅因题目涉及多个组件就认定 C 会受益，也不能将结构联系直接当作真实修复位置。

**D 的边界：原题 traceback 与新产生的运行失败分开记录。** 原题中的堆栈已经进入全部条件的相同任务输入，B、C 也可能利用这些文字。原题带堆栈首先适合验证解析器；D 的动态重排需要运行中实际产生的可用失败证据。应记录触发情况、证据来源、更新前后候选排名，并保留没有触发可用失败的任务，不能只分析 D 成功触发的案例。

第一批四道题优先验证不同仓库上的完整流程；跨组件题用于检查 C 的结构假设；异常与状态敏感题用于开发 D 的失败处理。全部任务分别记录定位表现、修复结果和探索成本，避免把找到相关文件等同于修复成功。

上述对应关系适用于本开发候选池。正式评价集另行选择并预先冻结，不能根据开发题上哪种条件获胜来挑选正式任务。

## 9. 角色 1 与角色 5 的下一步

1. 小组确认本候选名单和环境统一规则，记录确认日期。
2. 角色 1/5 核对兼容的控制环境、Harness 版本、任务镜像与评估入口。
3. 对第一批四道题记录真实镜像 digest、Python/依赖、启动结果、复现结果、构建时间、磁盘需求和测试入口。
4. 环境故障与题目本身的预期失败分开记录；证据不足的状态保持待确认。
5. 候选被排除时填写具体原因和日志路径，不能静默删除；按事先约定的规则选择替补。
6. 确认任务/初始版本后，角色 2 索引该固定源码，角色 3/4/1 对接模块；角色 5 独立评估并保存证据。
7. 这些任务一旦用于调试和方法调整，就保留在开发集合；正式评价任务另外选择并在看结果之前冻结。

参考修复、隐藏评测信息与真实定位标签仅在评价侧使用，不进入 Agent 或定位排名。未知费用/耗时记为 null；未运行的官方评估记为 not_run。
