# 四题 source-only 提示策略实验：与原始 dev5/dev3 的逐题对比

> 精简提交版：报告结论与数值不变。完整轨迹、排名、D 事件和官方测试全文位于独立证据包；标为“归档文件”的链接提供包内路径与哈希。下载后复算方法见 [完整证据说明](../docs/FULL_EVIDENCE.md)。


> GitHub 整理版，2026-10-28。完整版整理时读取了 76 次执行记录，复算官方结果、逐次 usage、初始排名/候选与 D 投递；没有重新运行 Agent、模型或官方评测。正文中 2026-10-26/27 的源码核验、原压缩包完整性检查和轨迹解释保留为历史审计记录，不能理解为本次重新执行全部历史核验。
>
> 报告链接已改为相对路径。统一表位于 [results](../results/analysis.json)，所有执行身份与原始文件见 [证据索引](../evidence/INDEX.md)。旧文提到的 `analysis.json → exploration/events` 等路径对应 [历史标注](../evidence/annotations/README.md)，其文件结构与新工具输出不同。正文中的 S/E/R/H/N/O 等旧目录简称用于识别历史来源，当前可访问路径以证据索引为准。


分析日期：2026-10-27。实验：`prompt_policy_four_tasks_20261027`。本报告只分析已有记录，不运行 Agent、Docker、测试或模型 API，不修改项目实现，不生成 HTML。

## 1. 先回答：这次究竟有没有改进？

**有局部改进，但没有获得整体修复数量的净增长，也没有证明 D 重排名带来了额外成功。**

- 新实验 A/B 各成功 **1/4**，C/D 各成功 **2/4**。最初同四题的 A/B 各为 **2/4**，C/D 各为 **1/4**。
- 变化全部集中在 **SymPy-23262**：原来 A/B 成功、C/D 失败，这次恰好反过来。Sphinx-8595 仍全成功；17630 和 20438 仍全失败。
- 将 16 个“题目×条件”运行一起清点，新旧均 **6/16** 成功；这只是盘点，16 次不是 16 道独立题，不能作为独立样本统计。
- 提示策略确实成功部署：Agent 看到 20 个经过路径过滤的源码候选，以及另列的 3 个测试路径。**但这四题没有新增任何目标文件的候选覆盖**，完整排名也没有变化。
- 23262-C/D 这次最终修到了正确的序列化函数，并保留 list 分支；这是实质修复进展。可是 C 的原有 20 个源码候选甚至逐项未变，D 本题没有排名更新，因此无法把成功单独归因于 source-only 或 D 重排名。
- D 能捕捉并送达更多有效诊断，尤其 20438 的“退出码 0 + traceback”。但“异常送到了”还没有稳定转化成“Agent 处理全部需求并正确提交”。

这批最有价值的结论是：**展示层已修好，反馈投递也更完整；当前最明显的瓶颈是把公开问题转成完整验证、检查实际修改位置、以及处理原始缺陷与新引入缺陷之间的区别。** 其中也有定位系统自身的不足，不能统统推给 Agent。

## 2. 数据范围、审计与比较口径

### 2.1 严格按同题对齐

| 题目 | 历史基线 | 本次 |
| --- | --- | --- |
| Sphinx-8595 | 原始 dev5，四条件的 selected run | 新 A/B/C/D，各一次 |
| SymPy-17630 | 原始 dev5，四条件的 selected run | 新 A/B/C/D，各一次 |
| SymPy-23262 | 原始 dev5，四条件的 selected run | 新 A/B/C/D，各一次 |
| SymPy-20438 | 原始 dev3，四条件的 selected run | 新 A/B/C/D，各一次 |

历史四题是从两个已完成批次中抽取的同题组合，不是当时另行执行的一套“四题实验”。不把原五题成功率或原三题成功率直接与现在四题相减。新实验共有 16 次运行、16 份官方报告，无重试；历史只采用原报告已经选定的运行，不重新挑选更好的 attempt。

### 2.2 本次实际核验了什么

1. 包内 `SHA256SUMS` 的 **237 项全部匹配**；哈希一致只说明导出完整，不代表方法有效。
2. 外部 `agent_visible_rankings.txt` 与包内同名文件逐字节一致。
3. 16 个 `effective_task.txt` 均完整包含在实际轨迹首个 user 消息中；B/C 的 8 份候选导出与 `prompt_candidates.json` 相同。四题 C/D 的首个 user 消息均逐字相同。
4. 直接读取 16 份本次官方 `report.json`：16 份补丁均成功应用，无官方基础设施失败；最终补丁文本均出现在对应评测日志中。
5. 从 trajectory 的原始 response usage 重新累计调用、tokens、费用：**259 次调用，3,900,811 total tokens，$0.77604795**。费用是接口报告值，没有另查账单。格式错误响应也计入调用，不能只数 assistant 消息。
6. 直接回读历史 16 份官方报告，成功/失败以及 F2P/P2P 通过数与原分析文件一致。
7. D 共投递 6 条反馈，全部能以完整文本和 SHA-256 对应到真实轨迹消息。5 条被记为 `rank_update`，1 条 `diagnostic_only`；其中一条 `rank_update` 实际没有改变完整排名顺序，后文单列。

包内 `audit_correction.json` 说明先前审计误报来自文本读取时 CRLF 归一化；本次按原始 UTF-8 字节读取后，实际提示交付检查通过。该修正不是补跑实验。

定位评价沿用历史报告已经提取的目标**文件路径**，只作为离线定位代理。本次没有打开参考修复的实现，也没有读取 `evaluation/dataset.json` 的语义内容；对失效行为的判断来自 Agent 自己的补丁、轨迹和已有官方失败日志。参考文件相同不等于正确修复；改了不同文件也不自动等于错误，最终仍以行为及 Harness 为准。

### 2.3 本次改变了哪些变量

| 项目 | 最初 dev5/dev3 | 本次 |
| --- | --- | --- |
| 模型与接口 | `openai/gpt-5.4-mini`，OpenRouter | 同名模型、同接口 |
| 问题与代码版本 | 固定 Verified revision、各题 base commit | 同题固定输入；完整初始排名一致 |
| A 的首个 user 消息 | 原始任务 | 四题均与历史逐字相同 |
| 共用 system 消息 | 原始简短系统提示 | 加入 `closed_loop_v2` 调查、复现、分支验证和提交前检查指导 |
| B/C/D 初始候选 | 全文件排名的 Top-20 | 过滤后 20 个源码候选，另附 3 个测试路径 |
| D 机制 | 旧退出码/失败规则 | 247c125 的诊断、路由、去重和计时机制；`failure_weight=1` |
| 函数提示、额外短验证提示 | 本报告不混入其他试验 | 都未启用 |
| 预算 | 250 steps、$3/run、命令 60 秒 | 同量级固定配置；非总 token 预算 |

本次实际源码来源是 **247c125 底版 + 72e93e9 的提示策略集成**；不能只写“纯 247c125”。集成差异涉及 `context.py`、`swebench_runner.py` 与策略测试文件。相较紧邻的 247c125 批次，这是提示策略改动；**相较用户指定的最初 dev5/dev3，同时还包含共用提示和 D 修复改动**。

因此可以比较版本表现，不能从本次历史对比单独估计 source-only 的因果效应。四题都是已经看过结果的开发题，也不能包装成独立 held-out 验证。

## 3. 官方修复结果

表中均为“原始 → 本次”，✓ 表示官方 resolved。

| 题目 | A | B | C | D |
| --- | --- | --- | --- | --- |
| Sphinx-8595 | ✓ → ✓ | ✓ → ✓ | ✓ → ✓ | ✓ → ✓ |
| SymPy-17630 | ✗ → ✗ | ✗ → ✗ | ✗ → ✗ | ✗ → ✗ |
| SymPy-23262 | ✓ → ✗ | ✓ → ✗ | ✗ → ✓ | ✗ → ✓ |
| SymPy-20438 | ✗ → ✗ | ✗ → ✗ | ✗ → ✗ | ✗ → ✗ |

### 3.1 主比较与增量比较

| 比较 | 原始同四题 | 本次同四题 | 应怎样解释 |
| --- | --- | --- | --- |
| A–D（项目主比较） | D 比 A 少成功 1 题 | D 比 A 多成功 1 题 | 相对位置翻转，全部发生在 23262；同时涉及 D 变好和 A 变差 |
| A–B | 同成功集合 | 同成功集合 | 本批 B 无官方净增益 |
| B–C | C 比 B 少成功 1 题 | C 比 B 多成功 1 题 | 23262 呈现结构候选方向与成功一致的个案，但历史方向相反 |
| C–D | 成功集合相同 | 成功集合仍相同 | 没有 D 相对 C 的额外修复成功 |

“D 相对 A 的差从 -1 变成 +1”不能表述为“D 新修好了两道题”：D 自身只多修好 23262 一题，另一个变化来自 A 在同题退化。C 也修好了该题，因此更不能将这两个差额都记到运行反馈头上。

### 3.2 目标测试与回归测试

F2P 是原本失败、期望修复后通过的测试；P2P 是原本通过、修复后应保持通过的测试。官方失败可能包括断言失败或执行错误。

| 题目 | 条件 | F2P 原始→本次 | P2P 原始→本次 | 本次 resolved |
| --- | --- | --- | --- | --- |
| Sphinx-8595 | A | 1/1 → 1/1 | N/A → N/A（0/0） | ✓ |
| Sphinx-8595 | B | 1/1 → 1/1 | N/A → N/A（0/0） | ✓ |
| Sphinx-8595 | C | 1/1 → 1/1 | N/A → N/A（0/0） | ✓ |
| Sphinx-8595 | D | 1/1 → 1/1 | N/A → N/A（0/0） | ✓ |
| SymPy-17630 | A | 1/2 → 1/2 | 19/19 → 19/19 | ✗ |
| SymPy-17630 | B | 1/2 → 1/2 | 19/19 → 19/19 | ✗ |
| SymPy-17630 | C | 1/2 → 1/2 | 19/19 → 19/19 | ✗ |
| SymPy-17630 | D | 1/2 → 1/2 | 19/19 → 19/19 | ✗ |
| SymPy-23262 | A | 1/1 → 0/1 | 61/61 → 52/61 | ✗ |
| SymPy-23262 | B | 1/1 → 0/1 | 61/61 → 61/61 | ✗ |
| SymPy-23262 | C | 0/1 → 1/1 | 61/61 → 61/61 | ✓ |
| SymPy-23262 | D | 0/1 → 1/1 | 61/61 → 61/61 | ✓ |
| SymPy-20438 | A | 0/2 → 0/2 | 92/93 → 93/93 | ✗ |
| SymPy-20438 | B | 0/2 → 0/2 | 93/93 → 93/93 | ✗ |
| SymPy-20438 | C | 0/2 → 0/2 | 93/93 → 92/93 | ✗ |
| SymPy-20438 | D | 0/2 → 0/2 | 93/93 → 93/93 | ✗ |

Sphinx 的 P2P 标签为空，0/0 是 N/A，不能写成“回归测试 100%”。17630 四条件都是只通过 1/2 个 F2P；20438 四条件仍为 0/2。新增明显回归是 23262-A 的 9 个 P2P 失败，以及 20438-C 的 1 个 P2P 失败。

## 4. 新提示策略到底做了什么，有没有把关键文件送进去？

### 4.1 实现是过滤展示，不是重算排名

`select_prompt_candidates` 先按 `(rank, file)` 排序，过滤测试路径及顶层 `doc/docs/example/examples`，再取 20 个。`select_related_tests` 则从同一完整排名中取前三个测试路径，另列为“Possibly relevant existing tests”。原始 rank 保留，因此列表有跳号。

这相当于把 20 个展示席位优先留给源码，另外给出测试线索。它没有改变 BM25、结构分数或 RRF，没有把测试与候选做调用关系配对，也没有保证前三个“测试路径”都是直接可运行的业务测试。

实际核对：四题 B/C/D 的 **12 份完整初始候选记录，包括路径、rank、score 等，均与原始批次相同**。变化发生在展示选择和附加提示。

### 4.2 目标路径的排名和展示位置

| 题目/路径代理 | B 原始 rank → 新展示位置 | C/D 原始 rank → 新展示位置 | 相对旧提示新增目标覆盖？ |
| --- | --- | --- | --- |
| Sphinx：`sphinx/ext/autodoc/__init__.py` | 12 → 第 5 个 | 11 → 第 4 个 | 否；原来已经展示 |
| 17630：`sympy/matrices/expressions/matexpr.py` | 52 → 未展示 | 18 → 第 18 个 | 否；C/D 原来已展示，B 仍未展示 |
| 23262：`sympy/utilities/lambdify.py` | 35 → 未展示 | 19 → 第 19 个 | 否；C/D 原来已展示，B 仍未展示 |
| 20438：`sympy/core/relational.py` | 1 → 第 1 个 | 1 → 第 1 个 | 否 |
| 20438：`sympy/sets/handlers/issubset.py` | 231 → 未展示 | 98 → 未展示 | 否 |
| 20438：`sympy/sets/handlers/comparison.py` | 887 → 未展示 | 120 → 未展示 | 否 |

“Sphinx 从第 12 变第 5”是**展示位置**变化，不是完整排名从 12 升到 5。也不要因为 C 列表新加入 `environment/adapters/indexentries.py`，就误认为本题目标文件首次进入列表；本题历史目标路径是 autodoc。

按这四题完整初始排名计算，B MRR 约 **0.2828**，C/D 约 **0.2998**，新旧不变。初始提示中“至少一个目标路径可见”的覆盖率，B 仍为 **2/4**，C/D 仍为 **4/4**。20438 只有 3 个目标代理中的 1 个可见，不能因 Hit@1=1 就声称多文件覆盖完整。

值得特别强调：**17630-B/C、23262-C 的 20 个候选记录与旧版逐项相同**，D 的初始提示与 C 相同。这几组的 source-only 过滤本身没有替换候选；主要新增内容是相关测试列表、共用验证指导及其他提示措辞。

### 4.3 相关测试提示的实际质量

| 题目 | B/C/D 实际附加的 3 条路径 | 本次观察 |
| --- | --- | --- |
| Sphinx-8595 | `tests/test_ext_autodoc.py`；`tests/test_environment_indexentries.py`；`tests/test_project.py` | 第一条与问题直接相关，确实被读/跑；后两条不能视为本题必要测试 |
| 17630 | `sympy/matrices/expressions/tests/test_blockmatrix.py`；`sympy/core/tests/test_singleton.py`；`bin/test_external_imports.py` | 第一条覆盖表面 blockmatrix 路径；未提示相邻 matadd 验证方向；实际 pytest 不可用 |
| 23262 | `sympy/testing/pytest.py`；`sympy/external/tests/test_codegen.py`；`sympy/utilities/tests/test_enumerative.py` | 首项是测试支持模块；没有直接给出 lambdify 的相应测试文件。C/D 最终靠自己的代码阅读和复现走到修复 |
| 20438 | `sympy/core/tests/test_arit.py`；`sympy/sets/tests/test_sets.py`；`sympy/testing/pytest.py` | sets 测试相关，但第一条和测试支持模块占用名额；B/D 跑 pytest 仍遇依赖缺失 |

因此，已经证实的是“测试线索按设计交付”；尚未证实的是“测试推荐更精准，或因此提升修复率”。路径规则还会将 `testing/` 下的框架支持文件当测试，也可能把某些库提供的测试工具源码排除在源码候选之外。不能将 `source_only` 理解为语义上完美的生产代码分类。

20 个源码候选加 3 个测试路径也不是与旧 20 个混合候选相同的上下文预算。若以后单独验证提示策略，应记录实际提示 token 长度，区分“内容分组”与“内容增量”。

## 5. Sphinx-8595：稳定成功，但新验证过程更绕，D 还提升了无关文件

问题核心是显式空的 `__all__=[]` 被真值判断当成“没有定义 __all__”，导致 autodoc 自动列出成员。

### 5.1 补丁与结果

新旧 A/B/C/D 均官方成功。本次四组都把核心判断从 `if not self.__all__` 改成 `if self.__all__ is None`；A/D 还调整 `sort_members` 的同类判断。B/C 最终补丁相同，A/D 最终补丁相同。

因此这是一个稳定的成功对照题，没有新的成功率空间；本次不能拿它证明“新策略多解决了一道问题”。源码目标展示提前是可确认的过程改善，但是否因此更快并未体现：四组本次 runtime 都高于历史值。

### 5.2 验证行为有进步，也有不可靠之处

- B 确实运行了相关 autodoc 子集；C 最终运行已有 `ignore_module_all` 用例通过。
- C 中途创建了一个不符合 fixture 实际含义的空成员测试，出现 `1 failed, 1 passed`，随后删除；这属于验证设计错误，不是定位算法发现新项目缺陷。
- D 的本地 Sphinx 项目第一次输出明确说明不能导入 `example`，此时“没有 foo/bar/baz”不能证明修复有效。Agent 随后调整路径再跑；第二次只保留“仍有 warning”的布尔值和空输出，没有完整 warning 文本，也没有同时验证“未定义 __all__ 时能正常列出成员”。所以该本地复现的证据强度有限。最终成功结论来自官方报告。

### 5.3 D 的一次更新并不支持根因定位增益

第 5 个决策执行较宽的 autodoc 测试，官方之外的本地测试失败输出包含大量 `PendingDeprecationWarning`。反馈把这个警告作为 exception summary，提升 `sphinx/environment/__init__.py`：**15 → 1**；实际目标 autodoc 则 **11 → 12**。反馈在下一次模型调用前确实送达。

轨迹中的 Agent 判断这是无关 warning 噪声，继续保留正确的 autodoc 修复。该题说明：**可解析、可映射的堆栈不一定与 issue 根因相关**；本次最终成功也不说明这一轮重排名帮了忙。更准确地说，Agent 没有被这次偏离根因的更新带走。

证据：[A 轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0186) / [A 补丁](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_A_da55590b/patch.diff)；[B 轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0189) / [B 补丁](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_B_62bf81ad/patch.diff)；[C 轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0192) / [C 补丁](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_C_9980e05c/patch.diff)；[D 轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0197) / [D 补丁](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_D_dbec8653/patch.diff)。

## 6. SymPy-17630：仍停留在 blockmatrix 局部补救，D 有小幅行为改善但未解决根本覆盖问题

### 6.1 新旧八条运行的共同局限

原始和本次四条件都只通过 **1/2 F2P、19/19 P2P**。本次全部补丁仍只修改 `blockmatrix.py`：在乘积块内把标量零重新包成带形状的 `ZeroMatrix`。

这些修改可以使公开示例中的 block multiplication/triple product 不再报错，但没有覆盖零矩阵在更基础运算中的语义。已有官方日志指出仍失败的是 `test_zero_matrix_add`；因此不是“所有测试都没改善”，而是**特定示例修好了，另一项必要行为始终没有修好**。

这一点不能简单要求 Agent 照参考文件修改。合理的工程诉求是从“为什么矩阵零会退化成标量零”继续检查相邻加法、乘法及形状语义，而不把包装层症状消失当成全部完成。

### 6.2 C/D 没有新增候选，B 的低覆盖依旧存在

`matexpr.py` 在 B 第 52，仍不展示；C/D 第 18，原来就展示。本次 D 在第 3 个决策通过 `grep` 实际看到了该文件的 ZeroMatrix/GenericZeroMatrix 相关代码片段，比原始 D 未观察到目标文件源码暴露有进展。但这只是搜索片段可见，不代表深入检查了相关运算，也没有转化为正确的完整补丁。

B 本次耗费 33 次 API 调用，大量时间用在构造器补丁、脚本引号/定位错误和恢复误删代码；最后仍回到 `_blockmul` 局部修复。C 也多次插入 helper 失败。这里的慢主要来自编辑与假设验证效率，不是“候选列表还不够长”。

### 6.3 D 的两轮 rank_update 分别处理不同性质的失败

1. 首次可用失败是实际 block multiplication 的 `ValueError`，在第 3 次模型调用前投递。F 排名集中于 `blockmatrix.py` 和 `strategies/core.py`；`matexpr.py` 的融合 rank **18 → 18**。
2. Agent 自己修改后尝试原地写入不可变矩阵，引发 `TypeError`。第二次投递在第 7 次模型调用前，Agent 随后加入 `.as_mutable()`，消除这个新引入错误。`matexpr.py` 则 **18 → 19**。
3. `python -m pytest ...test_blockmatrix.py` 报缺少 pytest，正确走环境原因 skip，没有再做根因排名，但这一条处理仍耗费约 **7.97 秒**。

D 在本题确实具有“及时展示失败位置、帮助注意到新引入错误”的机制证据；不过基础工具输出本身也已包含 TypeError，不能据单条轨迹断言是额外反馈导致修复。最重要的是，官方结果仍未改善。

历史 D 为 13 次调用/$0.04298，本次降至 9 次/$0.02554；这是局部成本进步。总 runtime 却从 91.35 秒升至 102.65 秒，不能称为端到端提速。

证据：[A 轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0200) / [A 补丁](../evidence/records/prompt_policy4/sympy__sympy-17630_A_f5105730/patch.diff)；[B 轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0203) / [B 补丁](../evidence/records/prompt_policy4/sympy__sympy-17630_B_ff6c411c/patch.diff)；[C 轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0206) / [C 补丁](../evidence/records/prompt_policy4/sympy__sympy-17630_C_e01fd7b2/patch.diff)；[D 轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0211) / [D 补丁](../evidence/records/prompt_policy4/sympy__sympy-17630_D_cc4b6bbb/patch.diff)。

## 7. SymPy-23262：真正的正例，同时也是最重要的反例

题目要求 Python 单元素 tuple 的代码生成保留逗号：返回 `(1,)`，而不是标量 `(1)`。关键区别在于：单独打印 SymPy Tuple 正确，并不代表 `lambdify` 的完整输入/递归序列化路径正确。

### 7.1 原始版本的分化

原始 A/B 最终都修改了 `lambdify.py` 中 `_recursive_to_string`，B 还保留了 printer 修改；两组官方成功。原始 C/D 虽然较早看到了 `lambdify.py`，最终只提交 `pycode.py` 的 printer 修改，官方失败。也就是说，旧失败并非单纯“完全找不到正确文件”。

### 7.2 本次 C：当前最干净的成功案例

C 在第 6 个决策明确定位到 `_recursive_to_string`：tuple 分支拼接括号时漏了单元素逗号。最终补丁在 tuple 分支处理单元素，同时让 list 分支保留自己的完整 return。

修复后真实输出不仅覆盖单元素 tuple、两个元素 tuple，还覆盖 `[1]` 与 `(1, [2])`。官方 **1/1 F2P、61/61 P2P**。调用仍为 9 次，与原 C 相同，修复质量却提升。

这一案例可以展示“沿 API 路径否定错误 printer 假设，再到真正序列化层，并检查相邻 list 分支”的完整过程。但必须同时说明：本题 C 的 20 个候选和旧版完全一样；附加测试列表也没有直接指向 lambdify 测试，因此还不能说是过滤测试文件造成成功。

### 7.3 本次 D：最终成功，但不能归功于失败重排名

D 反复在 Return printer、LambdaPrinter、lambdastr 之间试错，直到第 30 个决策才将最终修复落实到 `_recursive_to_string`，第 31 个决策显示正确的原始复现与 tuple/list 输出。官方 **1/1、61/61**。

全程没有 `rank_update`。第 8 个决策的 `inspect.getsource` 失败被视为 source display 而跳过；第 27 个决策错误地从 `sympy.utilities.lambdify` 导入 `sympify`，只产生一条 `diagnostic_only`，在下一调用前投递。它不是原始 tuple 缺陷的定位信号。

因此可以记为 D 条件成功，不能记为“D 重排名成功救回”。本题 D 比 C 多 **24 次调用**，runtime **163.73 vs 30.38 秒**，费用 **$0.09279 vs $0.03660**，没有额外修复收益。

更深一层的问题仍然存在：多次输出错误的 `return (1)`，命令却正常退出；D 不会仅凭数字或字符串打印结果判断违反了业务预期。需要可失败的行为断言，这不是继续调 F 权重能解决的。

### 7.4 本次 A：找到正确函数，但漏了 list 分支，引入九项回归

A 最终同样改到了 `_recursive_to_string`。问题是它把 `items` 的赋值放进 tuple 分支，却让 list 分支也执行 `return left + items + right`。于是 list 输入触发 **UnboundLocalError**。

A 的最终复现确实包含断言，也全部通过；但是只覆盖 tuple、两个元素 tuple、嵌套 SymPy Tuple，没有覆盖 list。官方记录为 **0/1 F2P、52/61 P2P**，失败日志反复指向未赋值的 `items`。

这个反例非常关键：**定位到正确文件和函数、写了断言、公开最小示例通过，仍不等于修复完整。** 应强化与改动分支对应的验证覆盖，而不只是把“跑过测试”作为二值指标。

### 7.5 本次 B：原始症状仍在，却改用局部 printer 通过作为提交理由

B 最终只提交 `pycode.py` 的 `_print_Tuple` 修改。轨迹多次看到 `lambdify` 仍输出错误源代码，最后却用 `pycode(Tuple(...))` / `_exprrepr` 的局部正确输出作为完成依据。官方 **0/1 F2P、61/61 P2P**。

这一行为说明 `closed_loop_v2` 中“回到原始复现再验证”的自然语言要求没有稳定执行。错误不在没有任何验证，而在**更换了验证对象**：从用户的 lambdify 路径，退缩到更容易通过的 printer 单元。

本题应完整展示四组，不能只选 C/D 的成功。它既说明当前框架有能力找到并完成正确修复，也说明单次 Agent 结果和验证行为存在显著波动。

证据：[A 轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0228) / [A 补丁](../evidence/records/prompt_policy4/sympy__sympy-23262_A_493f0768/patch.diff)；[B 轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0231) / [B 补丁](../evidence/records/prompt_policy4/sympy__sympy-23262_B_fedf4112/patch.diff)；[C 轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0234) / [C 补丁](../evidence/records/prompt_policy4/sympy__sympy-23262_C_6a2d9a25/patch.diff)；[D 轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0239) / [D 补丁](../evidence/records/prompt_policy4/sympy__sympy-23262_D_ef4887ca/patch.diff)。

## 8. SymPy-20438：D 捕捉到问题了，但修复范围、编辑位置与集合语义仍出错

### 8.1 结果没有改善，失败原因比“Agent 不听提示”更具体

原始和本次四组全部官方失败，F2P 一直 0/2。本次 A 的 P2P 从 92/93 改善为 93/93；B/D 仍保持 93/93；C 则从 93/93 退到 92/93。

公开问题既涉及 ProductSet/FiniteSet 的子集关系，也展示 `Eq(...).simplify()` 的 AttributeError。两部分都出现在可见问题中，后者不应因为标题强调 subset 就自动被当作题外问题。

### 8.2 D：退出码为 0 的真实错误已被捕捉，但未阻止带着剩余错误提交

- 第 1 个决策复现中的异常被 try/except 捕获，退出码 0，但完整 traceback 显示 `Complement` 没有 `.equals`。新 D 成功识别并在第 2 次模型调用前投递，明确给出 `relational.py:314` 等位置。
- Agent 修改 ProductSet subset 逻辑后，第 7 个决策再次返回码 0，却打印 `EmptySet` 没有 `.equals`。D 在第 8 次调用前再次投递，包含工作区已变化的提示。
- 两次反馈都没有让相关错误消失。Agent 读取 relational 实现后，又认定这是独立 robustness 问题，最终只提交 subset 修改。
- 既有官方日志正是记录了这个仍存在的 `EmptySet.equals` 错误。因而这不是只能靠隐藏测试才能知道的失败：轨迹在提交前已经明确暴露。

这可以支持“第二次 D 修复后，零退出码错误漏报的问题在本轨迹上得到解决”，但不能支持“闭环已经保证完整修复”。当前缺少的是提交前对未关闭公开症状的持续追踪，或者更明确的需求核验机制。

### 8.3 D 补丁还存在一个静态可见的语义方向问题

新增 ProductSet 对 FiniteSet 的判断，实际遍历的是 `other` 的元素，确认这些元素属于 `self`，计算方向接近 **other ⊆ self**，却将它作为 **self ⊆ other** 的答案。

例如 self 为 `{1,2} × {1,2}`、other 只含 `{(1,1)}`：新增分支会因 other 唯一元素属于 self 而返回真，但 self 显然不全包含于 other。这是依据补丁逻辑的静态推导，**本次未运行该反例，也不把它冒充官方已覆盖的失败项**。

这个问题解释了为什么只测试“两个集合完全相等”的示例容易漏错：两个方向在相等情形下都是真。至少需要真子集/真超集/非包含方向的公开语义验证。

### 8.4 C：最终代码位置与 Agent 自述不一致

C 多次承认编辑到了错误的 `is_subset`，但最终补丁仍落在 `sets.py` 的 **Union** 类中；补丁旁的 `as_relational` 文档也明确写着 Union。它增加了无保护的迭代与 `_eval_Eq`，没有实现自述中的 ProductSet 修复。

官方 `test_issue_9637` 新增错误为 `TypeError: 'Interval' object is not iterable`，与对含 Interval 的 Union 直接迭代的改动一致。F2P 依旧 0/2。

这首先是编辑位置校验问题。当前无需扩展成函数级定位研究，单是在提交前检查“实际改动属于哪个类/函数、是否对应自己的修复计划”，就能更直接地拦住这种错误。

### 8.5 A/B 的差别

A 尝试同时处理 subset 与 relational 对 Set 的保护，还添加了局部回归测试，最终没有 P2P 回归，但 F2P 仍 0/2。它说明“愿意修复更多公开症状”有进步，却不代表集合相等语义已经实现正确。

B 在 `issubset.py` 添加 ProductSet/FiniteSet 分派，修复漏掉的 ProductSet import 后，公开 subset 示例变好，但主动留下 Eq 异常；没有解决全部需求。它对 ProductSet 直接枚举也缺少充分的可迭代性保护，应视为静态风险，而不是本次新增的官方失败数量。

### 8.6 定位系统自身仍有责任

初始 C/D 把 `relational.py` 排在第一，但另两个历史目标代理 `issubset.py` 与 `comparison.py` 仍在第 98/120，过滤后依旧不可见。两次 runtime 反馈又集中在报错栈的 relational/basic/simplify，未补充这两个路径。

因此本题同时包含“报错位置已指出但 Agent 放弃处理”与“多模块语义相关文件覆盖不完整”。不能将整个失败只归为 Agent 错误，也不能因命中一个文件就断言定位任务已经完全做好。

证据：[A 轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0214) / [A 补丁](../evidence/records/prompt_policy4/sympy__sympy-20438_A_239283e3/patch.diff)；[B 轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0217) / [B 补丁](../evidence/records/prompt_policy4/sympy__sympy-20438_B_8d10db20/patch.diff)；[C 轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0220) / [C 补丁](../evidence/records/prompt_policy4/sympy__sympy-20438_C_98fe91f2/patch.diff)；[D 轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0225) / [D 补丁](../evidence/records/prompt_policy4/sympy__sympy-20438_D_45bca537/patch.diff)。

## 9. D 机制的独立审计

### 9.1 计数必须区分事件、投递、路由与实际排名变化

| 题目 | 旧 D 失败/投递数 | 本次事件行数 | rank_update / recovery / diagnostic | 实际改变完整排名顺序的投递数 |
| --- | --- | --- | --- | --- |
| Sphinx-8595 | 0 / 0 | 1 | 1 / 0 / 0 | 1 |
| SymPy-17630 | 5 / 3 | 4 | 2 / 0 / 0 | 2 |
| SymPy-23262 | 0 / 0 | 2 | 0 / 0 / 1 | 0 |
| SymPy-20438 | 0 / 0 | 3 | 2 / 0 / 0 | 1 |
| 合计 | 5 / 3 | 10 | 5 / 0 / 1 | 4 |

新 `failure_updates.jsonl` 中包括因源码显示被跳过的观察，不能把 10 行直接称为“10 次真实运行失败”。旧版与新版观察口径不同，不能仅比较行数判定 D 更有效。

20438 第二次 rank_update 投递了新异常与工作区变化信息，但完整排名前后相同。源码中的 `ranking_updated` 是按路由是否 `rank_update` 赋值，不能直接等同于实际排序改变。角色 5 应从 before/proposed 两份 ranking 独立计算 order change、目标 delta-RR 和可见候选变化。

### 9.2 首次可用失败，不能挑后续更好的一次代替

| 题目 | 首次可用于 rank_update 的失败 | 在哪次模型调用前送达 | 目标 rank 前后 | 能说明什么 |
| --- | --- | --- | --- | --- |
| Sphinx-8595 | 宽泛 autodoc 测试失败中的 warning/堆栈信息 | 6 | autodoc 11 → 12 | 解析可用但相关性较差，目标反降 |
| SymPy-17630 | block multiplication ValueError | 3 | matexpr 18 → 18 | 症状文件被强化，目标代理未改善 |
| SymPy-23262 | 无可用源码重排名失败；只有后期诊断投递 | — | N/A | D 的最终成功不能转为重排名正例 |
| SymPy-20438 | 退出码 0 的 Complement.equals traceback | 2 | relational 1 → 1；另两条 98/120 不变 | 捕获与投递修复有效，目标覆盖无新增 |

按当前控制器的 rank-update 可用口径，覆盖为 3/4；其中 Sphinx 的错误与 issue 根因相关性有问题。按首次可用失败计，没有一题获得目标 RR 或覆盖提升。23262 的 delta 应记 N/A，而不是擅自记 0 或排除整道题；它仍保留在 A–D 官方成功率分母中。

### 9.3 路由的进展与不足

已见进展：源码显示中的异常字符串被跳过；缺 pytest 被识别为环境原因；错误 import 走 diagnostic_only；捕获异常不再单凭退出码 0 漏掉；反馈文本带 observed symbol、文件/行和工作区变化，6 条均真正进入轨迹。

仍有不足：warning 背景噪声可能进入根因排名；原始缺陷和补丁引入 TypeError 都计入 rank_update；“正常退出但输出错误”仍依赖 Agent 自己写断言；测试缺失的 skip 仍消耗数秒级分析开销。本批无 edit_recovery 投递，不能声称已在线验证该路由的效果。

## 10. D 耗时分析

### 10.1 口径与逐题拆分

下表使用 `run_result.runtime_seconds`。新版本源码从 agent/environment 建立前计时，到 feedback 关闭、environment cleanup 后结束，包含 D 初始化及运行反馈；不含后续官方 Harness。历史也取同名 runtime 字段，**没有混用原报告中更外层的 agent_wall_seconds**。

`initial_localization_seconds` 与 `feedback_total_seconds` 是 runtime 的内部组成，不得再次加到 runtime 上。event processing 是逐事件子集，不等于 feedback total；其间差值还有执行观察/freshness 等处理。缺少统一硬件、缓存和服务延迟控制，跨日耗时只能描述已有运行，不能解释为纯算法速度差。

| 题目 | 旧 D runtime | 新 C runtime | 新 D runtime | D 初始化 | D feedback total | D event processing | 初始化+反馈占比 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Sphinx-8595 | 36.31 | 42.30 | 38.83 | 2.64 | 2.11 | 1.67 | 12.2% |
| SymPy-17630 | 91.35 | 62.17 | 102.65 | 44.24 | 27.21 | 24.33 | 69.6% |
| SymPy-23262 | 73.92 | 30.38 | 163.73 | 49.00 | 9.84 | 9.66 | 35.9% |
| SymPy-20438 | 62.38 | 75.71 | 127.95 | 51.79 | 29.92 | 27.92 | 63.9% |

四题 D 合计：

- runtime **433.16 秒**；C 为 **210.56 秒**，D 多 **222.60 秒**，约为 C 的 **2.06 倍**。
- 初始化定位 **147.67 秒**，反馈总处理 **69.08 秒**；两项合计 **216.75 秒，占 D runtime 50.04%**。
- 逐事件处理合计 **63.58 秒**；比 feedback total 少 **5.50 秒**，不是漏记或可以另加的一项。
- skipped 事件也耗费 **16.81 秒，占逐事件处理约 26.44%**。最明显的是 17630 缺 pytest 的 7.97 秒和 20438 缺 pytest 的 8.85 秒。

本批没有出现此前那种耗尽三次 rank-update 配额后仍大量分析的长尾，所以“本次耗时更少”若与其他批次比较，不能直接归因于已优化上限检查；失败轨迹本身不同。

### 10.2 两种成本不能混淆

D 总 API 费用 **$0.18734**，略低于 C 的 **$0.20523**，但总 runtime 明显更长。D 的慢主要不能由 token 费用代替解释，尤其 SymPy 三题的初始定位分别约 44–52 秒。

最值得保留的局部进步是 17630-D：调用和费用下降；最明显的低效是 23262-D：成功与 C 相同，却重复试错 33 次调用。若展示 D 优势，必须同时列成功、API 费用、wall/runtime 和内部定位开销，不能只挑一个变好的指标。

## 11. 新旧资源投入对照

| 条件 | 成功数 原始→本次 | API calls | 费用 USD | runtime 合计/秒 |
| --- | --- | --- | --- | --- |
| A | 2/4 → 1/4 | 40 → 60 | $0.10581 → $0.17385 | 180.76 → 210.62 |
| B | 2/4 → 1/4 | 39 → 73 | $0.10092 → $0.20963 | 96.73 → 228.75 |
| C | 1/4 → 2/4 | 36 → 62 | $0.10093 → $0.20523 | 95.11 → 210.56 |
| D | 1/4 → 2/4 | 48 → 64 | $0.13659 → $0.18734 | 263.95 → 433.16 |

四条件合计由 **163 → 259 次 API 调用**，费用由 **$0.44424660 → $0.77604795**，runtime 由 **636.55 → 1083.10 秒**。修复盘点仍为 6/16。因此不能声称本次整体效率提高。更强的验证指导在部分轨迹中增加了检查，也在另一些轨迹中增加了无效试错与重复收尾。

逐运行明细：

| 题目 | 条件 | API calls 原始→本次 | runtime 秒 原始→本次 | 费用 原始→本次 | 本次 total tokens |
| --- | --- | --- | --- | --- | --- |
| Sphinx-8595 | A | 6 → 10 | 12.75 → 37.06 | $0.00966 → $0.02596 | 67,792 |
| Sphinx-8595 | B | 6 → 7 | 13.05 → 24.82 | $0.01253 → $0.01947 | 58,831 |
| Sphinx-8595 | C | 5 → 13 | 9.66 → 42.30 | $0.01029 → $0.03864 | 169,924 |
| Sphinx-8595 | D | 8 → 10 | 36.31 → 38.83 | $0.01625 → $0.02766 | 114,011 |
| SymPy-17630 | A | 7 → 10 | 21.22 → 33.78 | $0.02071 → $0.02878 | 110,185 |
| SymPy-17630 | B | 10 → 33 | 23.63 → 102.85 | $0.02445 → $0.09380 | 541,812 |
| SymPy-17630 | C | 8 → 18 | 24.95 → 62.17 | $0.02238 → $0.06066 | 296,413 |
| SymPy-17630 | D | 13 → 9 | 91.35 → 102.65 | $0.04298 → $0.02554 | 102,681 |
| SymPy-23262 | A | 13 → 23 | 103.40 → 73.81 | $0.03396 → $0.06051 | 342,028 |
| SymPy-23262 | B | 13 → 19 | 32.13 → 54.58 | $0.03626 → $0.05475 | 322,683 |
| SymPy-23262 | C | 9 → 9 | 19.08 → 30.38 | $0.02344 → $0.03660 | 156,727 |
| SymPy-23262 | D | 20 → 33 | 73.92 → 163.73 | $0.05748 → $0.09279 | 621,417 |
| SymPy-20438 | A | 14 → 17 | 43.39 → 65.97 | $0.04148 → $0.05860 | 264,520 |
| SymPy-20438 | B | 10 → 14 | 27.92 → 46.50 | $0.02768 → $0.04162 | 198,907 |
| SymPy-20438 | C | 14 → 22 | 41.43 → 75.71 | $0.04482 → $0.06932 | 352,162 |
| SymPy-20438 | D | 7 → 12 | 62.38 → 127.95 | $0.01989 → $0.04135 | 180,718 |

表中 tokens 是本次各次响应 usage.total_tokens 的累积，包含重复上下文，不是最终上下文窗口长度。接口缓存会影响费用，因此 tokens 与费用不应按单一常数换算。

## 12. 为什么理论上都是 A，结果还是不同？

本次四题 A 的首个 user 消息确实与原始版本相同，模型名称也相同；但四题 system 消息都不同，新版加入了 `closed_loop_v2`。所以从原始版本到这次，**A 的完整输入并非完全相同**。

即使完整输入固定，生成式 Agent 的多步探索和编辑也不保证复现同一补丁。本批没有提供配对重复实验来分离提示效应、采样波动、提供方运行差异和环境时延，不能断言某一个因素贡献多少。

本次 A 真正改变 resolved 的是 23262：旧 A 在共享序列化逻辑中保留 list 正常路径，新 A 在 tuple 内定义局部变量后由 list 共用，从而引入回归。这是可以从补丁直接解释的失败机制，不需要猜测“官方评测随机判错”。两版都是补丁成功应用后，由实际测试给出不同结果。

20438-A 虽然仍失败，但回归数减少一项；Sphinx 和 17630 的 A 最终成功状态没变。应该逐题解释变化，不能把“某一批 A 成功率下降”当成定位方法突然增强的证据。

## 13. 对项目结论怎样写才准确、有价值

可以在报告或展示中使用：

> 在四个已使用过的开发实例上，新版源码候选/测试提示与修复指导组合，使 C/D 的官方成功数从 1/4 增至 2/4，但 A/B 各从 2/4 降至 1/4，变化集中于同一个实例。完整初始排名和目标覆盖均未改变，因此本实验支持展示策略已正确落地，并给出修复路径改善的个案证据，尚不能证明其独立因果收益。D 对退出码为零的异常反馈更完整，但本批没有超越 C 的额外修复成功，且引入明显 runtime 开销。

可以展示三种机制情形：

1. **容易找到、稳定成功**：Sphinx-8595。讨论源码展示与测试可用性，同时展示噪声反馈的风险。
2. **目标在上下文内，是否沿正确路径修复决定结果**：23262。并列 C 的正确修复、B 的验证对象偏移、A 的分支回归；不要隐藏退化组。
3. **表面症状改善，但语义/需求覆盖不足**：17630 与 20438。说明运行反馈可提供定位证据，但不替代完整修复推理与验证。

目前不应写：source-only 提升了完整排名 MRR；D 重排名让 23262 成功；所有失败都纯属 Agent；D 已显著优于 C；四题结果能够泛化到 Verified 全集。

## 14. 下一步优先处理与最低成本验证（建议，尚未执行）

这次结果不支持优先继续扩大候选数量或盲调 F 权重。先修直接可观测的提交与验证问题，并保留一个变量一次的实验边界。

| 优先级 | 要解决的具体问题 | 角色 5 可独立完成 | 需要配合的角色/范围 | 最小验证 |
| --- | --- | --- | --- | --- |
| P0 | 自测通过不代表公开需求全满足；B/D 可带着已见错误提交 | 离线标注“公开症状→验证命令→最终状态”，单列 unresolved-visible-failure | 角色 1 将提交前核验落到 Agent 执行/记录；角色 4 提供尚未关闭的有效失败证据 | 先回放 23262-B、20438-D 的已有轨迹，确认能识别剩余症状；再选一个开发题，仅验证此改动 |
| P0 | 改错类/函数，或删除必要分支 | 用补丁和可见源码做编辑位置/分支回归审计 | 角色 1 在编辑后验证实际类/函数与 diff；无需先改整个定位粒度 | 用 20438-C 错落 Union 和 23262-A list 未赋值作本地检查样例；先不花 API |
| P1 | related tests 只是路径启发式，支持模块占名额、测试不可执行 | 报告推荐命中、实际运行、依赖阻断分别计数 | 角色 2/3 改测试候选选择及关联；角色 1/环境准备提供可运行测试入口 | 固定 4 题现有完整排名，离线比较新旧测试列表；再在相同镜像做环境检查，不读隐藏评测用例 |
| P1 | D 将无关 warning 或新引入错误当原始根因排名 | 分开标注 issue-related、environment、edit-induced、unknown；自行算实际排序变化 | 角色 4 修改 failure classification/route；角色 1提供可靠执行与改动元数据 | 回放 Sphinx warning、17630 immutable TypeError、20438 rc=0 traceback，分别检查预期路由 |
| P1 | D 初始化和 skip 开销高 | 用现有 timing 分解；将 skipped 成本单列 | 角色 4/3 检查环境失败早退、索引复用及初始化热点，保留修改后索引新鲜度 | 先离线计时诊断样例；等输出/路由等价后再小量在线比较，不直接拿跨日 runtime 当优化收益 |
| P2 | source-only 的独立效果仍未证明 | 预先固定开发题、指标和比较计划 | 角色 1提供开关及一致提示；角色 2/3冻结排名 | 同底版、同 system、同模型与预算，只切换旧混合20 vs 新源码20+测试；若要拆分测试提示收益，再分后续独立实验 |

如果只允许一个很小的在线开发验证，优先选择 **23262** 检查“原始复现 + tuple/list 相邻分支覆盖 + 最终补丁一致”的落实，而不是凭现有一次成功宣布完成。若重点验证 D，则用 **20438** 检查“rc=0 失败投递后，公开剩余异常是否在提交前被处理”，成功标准应先包含行为链条，再看官方 resolved。

小样本验证只能证明实现方向与机制是否工作。最终评价应冻结版本和选择标准，在独立题目上同时运行 A–D；若做重复，应预先固定次数和汇总规则，不选最好的一次。历史基线保留作发展过程，不能拿来替代最终同版本对照。

## 15. 可复核证据与运行索引

下表链接均为本地绝对路径。每个“新记录”目录含 trajectory、补丁、完整/展示候选与有效提示；“新官方报告”可直接核对 resolved、F2P、P2P；D 的反馈文件位于各运行目录的 `failure_feedback/`。

| 题目 | 条件 | 原始 run_id | 本次 run_id | 运行材料 | 本次评测 | 历史评测 |
| --- | --- | --- | --- | --- | --- | --- |
| Sphinx-8595 | A | sphinx-doc__sphinx-8595_A_d3f56a5a | sphinx-doc__sphinx-8595_A_da55590b | [新记录](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_A_da55590b) | [新官方报告](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_A_da55590b/official/report.json) | [旧官方报告](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_A_d3f56a5a/official/report.json) |
| Sphinx-8595 | B | sphinx-doc__sphinx-8595_B_bbe306a9 | sphinx-doc__sphinx-8595_B_62bf81ad | [新记录](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_B_62bf81ad) | [新官方报告](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_B_62bf81ad/official/report.json) | [旧官方报告](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_B_bbe306a9/official/report.json) |
| Sphinx-8595 | C | sphinx-doc__sphinx-8595_C_a1e59bcb | sphinx-doc__sphinx-8595_C_9980e05c | [新记录](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_C_9980e05c) | [新官方报告](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_C_9980e05c/official/report.json) | [旧官方报告](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_C_a1e59bcb/official/report.json) |
| Sphinx-8595 | D | sphinx-doc__sphinx-8595_D_e196eabf | sphinx-doc__sphinx-8595_D_dbec8653 | [新记录](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_D_dbec8653) | [新官方报告](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_D_dbec8653/official/report.json) | [旧官方报告](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_D_e196eabf/official/report.json) |
| SymPy-17630 | A | sympy__sympy-17630_A_8944a852 | sympy__sympy-17630_A_f5105730 | [新记录](../evidence/records/prompt_policy4/sympy__sympy-17630_A_f5105730) | [新官方报告](../evidence/records/prompt_policy4/sympy__sympy-17630_A_f5105730/official/report.json) | [旧官方报告](../evidence/records/original_dev5/sympy__sympy-17630_A_8944a852/official/report.json) |
| SymPy-17630 | B | sympy__sympy-17630_B_310345fe | sympy__sympy-17630_B_ff6c411c | [新记录](../evidence/records/prompt_policy4/sympy__sympy-17630_B_ff6c411c) | [新官方报告](../evidence/records/prompt_policy4/sympy__sympy-17630_B_ff6c411c/official/report.json) | [旧官方报告](../evidence/records/original_dev5/sympy__sympy-17630_B_310345fe/official/report.json) |
| SymPy-17630 | C | sympy__sympy-17630_C_7d7d5077 | sympy__sympy-17630_C_e01fd7b2 | [新记录](../evidence/records/prompt_policy4/sympy__sympy-17630_C_e01fd7b2) | [新官方报告](../evidence/records/prompt_policy4/sympy__sympy-17630_C_e01fd7b2/official/report.json) | [旧官方报告](../evidence/records/original_dev5/sympy__sympy-17630_C_7d7d5077/official/report.json) |
| SymPy-17630 | D | sympy__sympy-17630_D_b6378bb3 | sympy__sympy-17630_D_cc4b6bbb | [新记录](../evidence/records/prompt_policy4/sympy__sympy-17630_D_cc4b6bbb) | [新官方报告](../evidence/records/prompt_policy4/sympy__sympy-17630_D_cc4b6bbb/official/report.json) | [旧官方报告](../evidence/records/original_dev5/sympy__sympy-17630_D_b6378bb3/official/report.json) |
| SymPy-23262 | A | sympy__sympy-23262_A_cb3e111d | sympy__sympy-23262_A_493f0768 | [新记录](../evidence/records/prompt_policy4/sympy__sympy-23262_A_493f0768) | [新官方报告](../evidence/records/prompt_policy4/sympy__sympy-23262_A_493f0768/official/report.json) | [旧官方报告](../evidence/records/original_dev5/sympy__sympy-23262_A_cb3e111d/official/report.json) |
| SymPy-23262 | B | sympy__sympy-23262_B_58239bd3 | sympy__sympy-23262_B_fedf4112 | [新记录](../evidence/records/prompt_policy4/sympy__sympy-23262_B_fedf4112) | [新官方报告](../evidence/records/prompt_policy4/sympy__sympy-23262_B_fedf4112/official/report.json) | [旧官方报告](../evidence/records/original_dev5/sympy__sympy-23262_B_58239bd3/official/report.json) |
| SymPy-23262 | C | sympy__sympy-23262_C_a39c81b8 | sympy__sympy-23262_C_6a2d9a25 | [新记录](../evidence/records/prompt_policy4/sympy__sympy-23262_C_6a2d9a25) | [新官方报告](../evidence/records/prompt_policy4/sympy__sympy-23262_C_6a2d9a25/official/report.json) | [旧官方报告](../evidence/records/original_dev5/sympy__sympy-23262_C_a39c81b8/official/report.json) |
| SymPy-23262 | D | sympy__sympy-23262_D_3fd15bb3 | sympy__sympy-23262_D_ef4887ca | [新记录](../evidence/records/prompt_policy4/sympy__sympy-23262_D_ef4887ca) | [新官方报告](../evidence/records/prompt_policy4/sympy__sympy-23262_D_ef4887ca/official/report.json) | [旧官方报告](../evidence/records/original_dev5/sympy__sympy-23262_D_3fd15bb3/official/report.json) |
| SymPy-20438 | A | sympy__sympy-20438_A_d53bdc45 | sympy__sympy-20438_A_239283e3 | [新记录](../evidence/records/prompt_policy4/sympy__sympy-20438_A_239283e3) | [新官方报告](../evidence/records/prompt_policy4/sympy__sympy-20438_A_239283e3/official/report.json) | [旧官方报告](../evidence/records/original_dev3/sympy__sympy-20438_A_d53bdc45/official/report.json) |
| SymPy-20438 | B | sympy__sympy-20438_B_253ef3a1 | sympy__sympy-20438_B_8d10db20 | [新记录](../evidence/records/prompt_policy4/sympy__sympy-20438_B_8d10db20) | [新官方报告](../evidence/records/prompt_policy4/sympy__sympy-20438_B_8d10db20/official/report.json) | [旧官方报告](../evidence/records/original_dev3/sympy__sympy-20438_B_253ef3a1/official/report.json) |
| SymPy-20438 | C | sympy__sympy-20438_C_258b0715 | sympy__sympy-20438_C_98fe91f2 | [新记录](../evidence/records/prompt_policy4/sympy__sympy-20438_C_98fe91f2) | [新官方报告](../evidence/records/prompt_policy4/sympy__sympy-20438_C_98fe91f2/official/report.json) | [旧官方报告](../evidence/records/original_dev3/sympy__sympy-20438_C_258b0715/official/report.json) |
| SymPy-20438 | D | sympy__sympy-20438_D_124384a9 | sympy__sympy-20438_D_45bca537 | [新记录](../evidence/records/prompt_policy4/sympy__sympy-20438_D_45bca537) | [新官方报告](../evidence/records/prompt_policy4/sympy__sympy-20438_D_45bca537/official/report.json) | [旧官方报告](../evidence/records/original_dev3/sympy__sympy-20438_D_124384a9/official/report.json) |

主要入口：

- [原始 dev5 报告](../reports/01_original_eight_tasks.md)
- [原始 dev3 报告](../reports/01_original_eight_tasks.md)
- [本次 manifest](../evidence/provenance/prompt_policy4/manifest.json)
- [提示策略集成差异](../evidence/provenance/prompt_policy4/provenance/prompt_policy_integration.diff)
- [实际候选列表](../evidence/provenance/prompt_policy4/agent_visible_rankings.txt)
- [共用系统提示](../evidence/provenance/prompt_policy4/prepared/system_prompt.txt)
- [包内结果汇总](../results/run_summary.csv)
- [独立审计 JSON](../results/analysis.json)
- [独立审计脚本](../tools/offline_eval/README.md)

独立审计脚本只使用本地标准库读取已有文件、生成审计 JSON 和便于阅读的轨迹文本；不执行压缩包附带的 `analyze.py`、不执行模型生成的 shell 命令、不启动评测。报告中的额外反例和改进方案均是分析或建议，未伪装为已经运行的实验。

## 随包证据索引

| 实验 | 任务 | 条件/尝试 | 入选 | 运行、轨迹、官方结果 |
|---|---|---|---|---|
| prompt_policy4 | sphinx-doc__sphinx-8595 | A / 1 | 是 | [记录](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_A_da55590b/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0186) · [补丁](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_A_da55590b/patch.diff) · [官方](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_A_da55590b/official/report.json) |
| prompt_policy4 | sphinx-doc__sphinx-8595 | B / 1 | 是 | [记录](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_B_62bf81ad/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0189) · [补丁](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_B_62bf81ad/patch.diff) · [官方](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_B_62bf81ad/official/report.json) |
| prompt_policy4 | sphinx-doc__sphinx-8595 | C / 1 | 是 | [记录](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_C_9980e05c/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0192) · [补丁](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_C_9980e05c/patch.diff) · [官方](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_C_9980e05c/official/report.json) |
| prompt_policy4 | sphinx-doc__sphinx-8595 | D / 1 | 是 | [记录](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_D_dbec8653/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0197) · [补丁](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_D_dbec8653/patch.diff) · [官方](../evidence/records/prompt_policy4/sphinx-doc__sphinx-8595_D_dbec8653/official/report.json) |
| prompt_policy4 | sympy__sympy-17630 | A / 1 | 是 | [记录](../evidence/records/prompt_policy4/sympy__sympy-17630_A_f5105730/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0200) · [补丁](../evidence/records/prompt_policy4/sympy__sympy-17630_A_f5105730/patch.diff) · [官方](../evidence/records/prompt_policy4/sympy__sympy-17630_A_f5105730/official/report.json) |
| prompt_policy4 | sympy__sympy-17630 | B / 1 | 是 | [记录](../evidence/records/prompt_policy4/sympy__sympy-17630_B_ff6c411c/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0203) · [补丁](../evidence/records/prompt_policy4/sympy__sympy-17630_B_ff6c411c/patch.diff) · [官方](../evidence/records/prompt_policy4/sympy__sympy-17630_B_ff6c411c/official/report.json) |
| prompt_policy4 | sympy__sympy-17630 | C / 1 | 是 | [记录](../evidence/records/prompt_policy4/sympy__sympy-17630_C_e01fd7b2/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0206) · [补丁](../evidence/records/prompt_policy4/sympy__sympy-17630_C_e01fd7b2/patch.diff) · [官方](../evidence/records/prompt_policy4/sympy__sympy-17630_C_e01fd7b2/official/report.json) |
| prompt_policy4 | sympy__sympy-17630 | D / 1 | 是 | [记录](../evidence/records/prompt_policy4/sympy__sympy-17630_D_cc4b6bbb/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0211) · [补丁](../evidence/records/prompt_policy4/sympy__sympy-17630_D_cc4b6bbb/patch.diff) · [官方](../evidence/records/prompt_policy4/sympy__sympy-17630_D_cc4b6bbb/official/report.json) |
| prompt_policy4 | sympy__sympy-23262 | A / 1 | 是 | [记录](../evidence/records/prompt_policy4/sympy__sympy-23262_A_493f0768/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0228) · [补丁](../evidence/records/prompt_policy4/sympy__sympy-23262_A_493f0768/patch.diff) · [官方](../evidence/records/prompt_policy4/sympy__sympy-23262_A_493f0768/official/report.json) |
| prompt_policy4 | sympy__sympy-23262 | B / 1 | 是 | [记录](../evidence/records/prompt_policy4/sympy__sympy-23262_B_fedf4112/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0231) · [补丁](../evidence/records/prompt_policy4/sympy__sympy-23262_B_fedf4112/patch.diff) · [官方](../evidence/records/prompt_policy4/sympy__sympy-23262_B_fedf4112/official/report.json) |
| prompt_policy4 | sympy__sympy-23262 | C / 1 | 是 | [记录](../evidence/records/prompt_policy4/sympy__sympy-23262_C_6a2d9a25/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0234) · [补丁](../evidence/records/prompt_policy4/sympy__sympy-23262_C_6a2d9a25/patch.diff) · [官方](../evidence/records/prompt_policy4/sympy__sympy-23262_C_6a2d9a25/official/report.json) |
| prompt_policy4 | sympy__sympy-23262 | D / 1 | 是 | [记录](../evidence/records/prompt_policy4/sympy__sympy-23262_D_ef4887ca/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0239) · [补丁](../evidence/records/prompt_policy4/sympy__sympy-23262_D_ef4887ca/patch.diff) · [官方](../evidence/records/prompt_policy4/sympy__sympy-23262_D_ef4887ca/official/report.json) |
| prompt_policy4 | sympy__sympy-20438 | A / 1 | 是 | [记录](../evidence/records/prompt_policy4/sympy__sympy-20438_A_239283e3/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0214) · [补丁](../evidence/records/prompt_policy4/sympy__sympy-20438_A_239283e3/patch.diff) · [官方](../evidence/records/prompt_policy4/sympy__sympy-20438_A_239283e3/official/report.json) |
| prompt_policy4 | sympy__sympy-20438 | B / 1 | 是 | [记录](../evidence/records/prompt_policy4/sympy__sympy-20438_B_8d10db20/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0217) · [补丁](../evidence/records/prompt_policy4/sympy__sympy-20438_B_8d10db20/patch.diff) · [官方](../evidence/records/prompt_policy4/sympy__sympy-20438_B_8d10db20/official/report.json) |
| prompt_policy4 | sympy__sympy-20438 | C / 1 | 是 | [记录](../evidence/records/prompt_policy4/sympy__sympy-20438_C_98fe91f2/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0220) · [补丁](../evidence/records/prompt_policy4/sympy__sympy-20438_C_98fe91f2/patch.diff) · [官方](../evidence/records/prompt_policy4/sympy__sympy-20438_C_98fe91f2/official/report.json) |
| prompt_policy4 | sympy__sympy-20438 | D / 1 | 是 | [记录](../evidence/records/prompt_policy4/sympy__sympy-20438_D_45bca537/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0225) · [补丁](../evidence/records/prompt_policy4/sympy__sympy-20438_D_45bca537/patch.diff) · [官方](../evidence/records/prompt_policy4/sympy__sympy-20438_D_45bca537/official/report.json) |

## 历史材料范围说明

本整理版保留原报告的分析日期、审计结论与解释边界。原 PDF proposal、早期一次性分析脚本、重复归档包和其他探索实验报告没有重复放入本目录；它们不是本次通用工具运行的依赖。原始压缩包身份及 SHA-256 见 evidence/manifest.json。当前报告的完整指标应按配套完整证据包中的清单复算；精简版保留预计算汇总和小体积证据。

历史源码浏览和失败原因是人工/先前审计标注，并未因换成统一工具而变成自动推导的因果结论。本包不包含参考修复 hunk 或整套基准文件。源文件名是评价代理，不代表只有修改该文件才能修好。
