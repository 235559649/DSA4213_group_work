# 三题 D 演进：原始版本、第一次修复与第二次修复的完整比较

> 精简提交版：报告结论与数值不变。完整轨迹、排名、D 事件和官方测试全文位于独立证据包；标为“归档文件”的链接提供包内路径与哈希。下载后复算方法见 [完整证据说明](../docs/FULL_EVIDENCE.md)。


> GitHub 整理版，2026-10-28。完整版整理时读取了 76 次执行记录，复算官方结果、逐次 usage、初始排名/候选与 D 投递；没有重新运行 Agent、模型或官方评测。正文中 2026-10-26/27 的源码核验、原压缩包完整性检查和轨迹解释保留为历史审计记录，不能理解为本次重新执行全部历史核验。
>
> 报告链接已改为相对路径。统一表位于 [results](../results/analysis.json)，所有执行身份与原始文件见 [证据索引](../evidence/INDEX.md)。旧文提到的 `analysis.json → exploration/events` 等路径对应 [历史标注](../evidence/annotations/README.md)，其文件结构与新工具输出不同。正文中的 S/E/R/H/N/O 等旧目录简称用于识别历史来源，当前可访问路径以证据索引为准。


分析日期：2026-10-27。新实验：`failure_feedback_247c125_abcd_20261027`，源码提交 `247c12563012a31413c8c330a1441ca6a3ef1880`。

## 1. 结论先行

**第二次修复让 D 更早识别并交付运行证据，但没有提高这三题的官方修复成功率。本轮 D 为 0/3，原始 D 与第一次修复 D 均为 1/3。** 本轮完整 A/B/C/D 分别为 **0/3、1/3、1/3、0/3**，B/C 的成功均来自 Django-12262。

这次最有价值的变化，是能够把“机制修复”和“修复质量”分开验证：

1. **已确认的工程改进：** 两道 SymPy 在第一次模型调用中就产生了返回码为 0 的完整 traceback，新 D 均识别并在第二次调用前送达反馈。第一次修复时，这类捕获后打印的异常没有触发。新 D 还真实交付了不重排的诊断消息，部分环境错误也被正确过滤。
2. **仍未解决的结果问题：** 21379 收到 `mod.py` 的明确诊断、随后也阅读了该文件，最终仍修改上层 `hyperbolic.py`，官方 `test_Mod` 失败；20438 明知 `Eq(...).simplify()` 仍报错，却缩小修复范围后提交；Django 找对文件后遗漏了必填参数的状态更新。
3. **新增的机制问题：** 21379 的原始异常把 `mod.py` 从 285 提到 24，Agent 新引入的 NameError 又把它降回 285，下一次原始异常才恢复到 24。排名会被当前新错误覆盖，且编辑错误占用了原始缺陷的重排额度。
4. **新增的成本证据：** D 总运行时间 458.243 秒，其中初始定位与反馈处理合计 270.745 秒，占 59.08%；逐事件处理时间中 67.87% 花在最终没有送达反馈的事件上。
5. **比较边界：** 这次不只是替换 D。所有 A/B/C/D 都新增了 `closed_loop_v2` 调查与验证提示，B/C/D 的导航提示也增加一句要求。因此本轮条件间比较比跨轮直接归因更可靠；不能将所有变化都称为“第二次修 D 的效果”。

可以支持的项目结论是：**运行反馈的可观测性与交付能力改善，但其最终效用受到反馈路由、证据保留、修复判断和验证执行共同限制；目前没有完整 D 优于 A 或 C 的结果证据。**

## 2. 比较对象与证据核查

### 2.1 三轮身份不能混合

| 轮次 | 数据来源 | 实际运行范围 | 用途 |
|---|---|---|---|
| R0 原始三题 | `dev3_extra_abcd_v1`；原三题报告及原轨迹 | 12 个正式 A/B/C/D，历史启动失败另计 | 历史基线 |
| R1 第一次修 D | `trials/d_feedback_rerun_20261027.tar.gz`；`11dd3fa` | 仅 3 个 D | 检查第一次反馈修复 |
| R2 第二次修 D，本轮 | 本次 ZIP；`247c125` | 12 个正式 A/B/C/D，另保留 1 次失败 A 尝试 | 本轮主比较与第二次机制审计 |

三轮仍是同三个开发任务：`django__django-12262`、`sympy__sympy-20438`、`sympy__sympy-21379`，不是三批独立题目。R1 没有新 A/B/C，不能把 R0 的 A/B/C 拼接成 R1 的同期对照。

### 2.2 本次实际核查

- 解压到独立的 `tmp/d_second_fix_review/`，保留 ZIP 和已有报告。
- 验证 `FILE_MANIFEST.json` 列出的 **225 个文件 SHA-256 全部匹配**。这确认包内一致性，不等于独立证明服务器上的所有运行操作。
- 对 12 个正式运行逐一读取官方 `report.json`：均成功应用补丁、进入官方测试，无报告中的基础设施失败。
- 12 份 `patch.diff` 均匹配 `selection.json` 的哈希，且补丁全文存在于相应官方 `run_instance.log`。
- 从轨迹各消息的原始 response 汇总 usage，包含格式错误响应：调用数和费用均与 `run_result.json` 相符，未只统计正常 assistant 消息。
- 6 次反馈交付均在轨迹中找到相同文本，交付文本哈希匹配；其中 **5 次重排、1 次纯诊断**。
- 直接核对三题 C/D 的初始 user 消息，全部逐字相同；12 个正式运行使用相同 system 消息。
- 读取提交的项目源码快照，核对提示变化、反馈路由、排名融合与计时位置。
- R0 数值沿用已审计的 `role5-dev3-report-v1/analysis.json`，并复查初始提示；R1 重新读取压缩包中的运行、轨迹及相关源码，官方历史结果与上午报告对照。未将这两轮包装为本次重新运行的结果。

本次没有运行 Agent、模型 API、复现测试或 Harness；没有修改项目实现，没有生成 HTML。未读取参考修复，也未打开本包 `evaluation/dataset.json` 的参考测试内容；官方既有日志仅用于解释已发生的结果。

### 2.3 重跑与缺失口径

SymPy-20438/A 的第一次尝试 `sympy__sympy-20438_A_771ea469` 因 `RepeatedFormatError` 结束。包中保留了用户授权单次重跑的记录，规则是无论结果如何使用第二次，不是挑成功的一次。

- 正式采用：`sympy__sympy-20438_A_f83ce396`，仍未修复成功。
- 失败尝试另计：14 次 API 调用，费用 $0.036555。
- 正式 12 次：149 次调用，$0.4778583。
- 含失败尝试：13 次实际运行，163 次调用，$0.5144133。

不把失败尝试当作第 4 道 A 题，也不把它从资源消耗中删除。本轮 A=0/3 的结果不因这次替换而得到成功率收益。费用为 provider response 的报告值，不是账单核对值。

## 3. 官方结果：先看本轮，再看跨轮

### 3.1 本轮完整 A/B/C/D

单元格为“是否 resolved；F2P 通过数；P2P 通过数”。F2P 为缺陷相关测试，P2P 为回归测试。

| 任务 | A | B | C | D |
|---|---|---|---|---|
| Django-12262 | 否；3/4；18/18 | **是；4/4；18/18** | **是；4/4；18/18** | 否；3/4；18/18 |
| SymPy-20438 | 否；0/2；93/93 | 否；0/2；90/93 | 否；0/2；90/93 | 否；0/2；93/93 |
| SymPy-21379 | 否；0/1；91/91 | 否；0/1；91/91 | 否；0/1；91/91 | 否；0/1；91/91 |
| 成功题数 | **0/3** | **1/3** | **1/3** | **0/3** |

本轮 A–D 主比较为 0 比 0，没有新增成功；C–D 为 1 比 0，D 在 Django 上少成功一题。B/C 在 20438 各新增三个回归失败，D 没有这些回归，属于补丁质量的局部差异，但该题 D 仍未解决原始需求。

### 3.2 三轮 D 纵向比较

| 任务 | R0 原 D | R1 第一次修 D | R2 第二次修 D |
|---|---|---|---|
| Django-12262 | 否；F2P 2/4；P2P 18/18 | 否；3/4；18/18 | 否；3/4；18/18 |
| SymPy-20438 | 否；0/2；93/93 | 否；0/2；92/93 | 否；0/2；93/93 |
| SymPy-21379 | **是；1/1；91/91** | **是；1/1；91/91** | 否；0/1；91/91 |
| 成功题数 | **1/3** | **1/3** | **0/3** |

不能只看通过数：Django 的 R1 与 R2 都是 3/4，但本次失败已从“默认参数省略后被错误要求提供”，转为“必填关键字参数已经提供，却仍被认为缺失”。这是修复轨迹改变，不是同一个错误毫无变化。

20438 恢复了 R1 丢失的一个回归测试，但 F2P 仍为 0/2。21379 从成功变为失败，最终补丁落点也由之前包含 `mod.py` 变为仅修改 `hyperbolic.py`。这支持本轮产出退步，不能由单次轨迹证明新版 D 必然导致退步。

### 3.3 跨轮所有条件的任务成功数

| 轮次 | A | B | C | D |
|---|---:|---:|---:|---:|
| R0 | 2/3 | 0/3 | 1/3 | 1/3 |
| R1 | 未重跑 | 未重跑 | 未重跑 | 1/3 |
| R2 | 0/3 | 1/3 | 1/3 | 0/3 |

R0 的 C 成功来自 21379，R2 的 C 成功来自 Django。相同 1/3 掩盖了成功任务发生交换；不能说 C 的行为没有变化。

## 4. 是否是干净的 D 修复消融？

### 4.1 本轮内的控制较完整

模型均为 `openai/gpt-5.4-mini`，使用原生 OpenRouter 模型适配；step limit=250、每次 cost limit=$3、命令 timeout=60 秒；没有额外 wall-time limit。定位 Top-20，F 权重=1，RRF k=60；重排上限 3、编辑恢复上限 2、诊断上限 1。各 task/condition 独立运行，不共享 C/D 的动作前缀。

三题 C/D 初始 user 消息完全相同，system 也相同。这比用历史 C 与新 D 拼接比较更好。但即使初始输入相同，两次独立生成也会分叉，不能把 C 的成功路径当作 D 加反馈前必然会走的路径。

### 4.2 跨轮有明确混杂因素

R0、R1 的 system 只有通用 shell 助手描述。R2 新增统一 `closed_loop_v2`，要求：先调查实现、把 issue 预期转为断言、检查默认/替代分支、将验证命令与源码显示分开、保留失败状态、提交前复核异常等。

R2 的 `additional_short_verification_prompt=false` 只表示没有再次叠加上一批额外短提示，**不表示没有新增验证提示**。这次提示已经整合到所有组的 system 中。B/C/D 的 user 导航部分还新增一句要求阅读合理候选并说明偏离依据。

逐字比较结果：R0→R2 三题 A 的初始 user 均相同，但 system 均不同；B/C/D 的 system 与 user 均不同。R1→R2 三题 D 的初始 user 也不同。第一次修复和第二次修复快照中的 `keyword.py`、`structural.py`、OpenRouter 适配器和工具调用转换文件相同；`ranker.py` 增加权重接口，但本轮 F 权重仍为 1，不能把本轮当作“提高 F 权重”的实验。

因此，本轮更准确的名称是“**第二次反馈实现 + 统一调查验证提示的 A/B/C/D 开发实验**”。能确认的是具体工程行为和本轮结果；不能独立估计 D 代码、统一提示、随机生成分别贡献多少。

## 5. 逐题轨迹：为什么得到这些结果

以下 q 表示轨迹中有记录的 assistant 消息序号，m 表示 `messages` 的零基索引；事件 step 为运行器调用计数。格式错误会造成 q 与 API 调用数不同，不能混用。关键位置同时给出 m 以便核对。

### 5.1 Django-12262：B/C 真正修通，D 的参数状态维护仍有漏洞

**本轮改善：** B/C 的最终补丁都保留了“允许出现的关键字参数”和“仍然缺少的必填参数”的区别。B 单独维护 `required_kwonly` 并在收到参数时移除；C 保留原有必填跟踪，只修正允许列表和重复参数判定。这两份补丁官方均通过 4/4、18/18。

**A 的失败：** 将 `unhandled_kwargs` 直接改成全部 `kwonly`，导致带默认值的参数仍可能被当成必填。官方 `test_simple_tags` 失败，与此前常见的默认值问题一致。

**D 的过程：**

1. q1 已阅读 `library.py`；初始文件排名第 1。这里不存在“始终找不到文件”的证据。
2. q4 的测试分别遇到未配置 Django settings 和未安装 pytest。failure-1/2 正确跳过重排。
3. q5 又因测试模块导入路径错误，抛出 `InvalidTemplateLibrary`，内层为 `No module named 'template_tests'`。failure-3 却进入 `rank_update`，在 m15、q6 前送达。`library.py` 仍是第 1，`engine.py` 从 12 升到 2。这是测试配置问题被框架异常包装后穿过环境过滤的实例。
4. 多次自测对现有标签使用错误参数名 `greeting`；q14 才明确承认标签实际参数名是 `kwarg`。这些错误输出主要在验证脚本中制造噪声。
5. q14 编辑脚本发生 `<stdin>` 的三引号 SyntaxError；failure-7 走 `diagnostic_only`，m34、q15 前送达，不改变排名。q15 明确回应诊断并重新查看文件，这是诊断被采用的直接轨迹证据。但这是编辑脚本解析失败，不是已证明仓库源码不可解析，不能写成“编辑恢复通道验证成功”。
6. q17 最终删除了原先收到 keyword-only 参数时从未处理列表移除的分支；留下的 `missing_kwargs` 初始化后不再随已提供参数更新。
7. q19 的末次自测只覆盖默认参数省略、默认参数显式传入以及另一种重复参数情况，未验证“无默认值的必填关键字参数已显式提供”。q20–21 导出并提交。

官方错误为：`simple_keyword_only_param` 已提供 `kwarg` 却被报告未提供。**R1 修复漏的是默认参数分支，R2 修复漏的是必填参数状态更新；两者同为 3/4，却不应被归纳成同一根因。**

对 D 的判断：纯诊断通道有实际价值证据，但没有阻止最终逻辑遗漏；环境过滤只部分生效，且 file-level 命中无法区分同一 `library.py` 中的 `import_library` 配置故障与 `parse_bits` 目标行为。

### 5.2 SymPy-20438：反馈提前到达，Agent 仍主动缩小问题范围

**本轮相对改善：** D 的 P2P 93/93，恢复了第一次修复 D 的 92/93；也没有本轮 B/C 的三个回归失败。但所有组的 F2P 都是 0/2。

**D 的过程：**

- q1/m2 直接复现 subset 与 `Eq(...).simplify()`；捕获异常后打印完整 traceback，返回码 0。新入口识别 `Complement` 没有 `.equals` 的异常，failure-1 在 m6、第二次调用前送达，明确指向 `relational.py:314`。
- 该文件原本就是第 1；另外两个历史离线目标 `comparison.py`、`issubset.py` 仍是 120、98。反馈没有增加这些文件的 Top-20 覆盖。
- 后续主要沿 `ProductSet._eval_is_subset` 修改。最终使用公开 `other.contains(x)` 配合 `fuzzy_and`，避免了 B/C 直接调用内部 `_contains(e)` 遇到原生 tuple 的回归。
- q5/m19 编辑与复现放在同一条复合命令中；m20 输出清楚显示 subset=True/True，但 `Eq(...).simplify()` 仍抛 `EmptySet` 没有 `.equals`。该事件因为执行来源不能被保守判定，记录 `provenance_required`，没有再次送达 D 反馈。
- q6/m21 明确承认 equality simplification 仍失败，却表示不愿扩大修复范围；随后两次 pytest 都因缺依赖失败，最终提交 subset 补丁。

这里不能说“Agent 没看见异常”：普通命令输出已经包含它，最早的 D 消息也提供了相关源码位置。更准确的是 **Agent 没有把公开问题中的相等性行为作为必须满足的完成条件**。新增 system 提示存在，但没有形成可靠执行约束。

本轮 B/C 的 P2P 失败为 `test_Complement`、`test_product_basic`、`test_DisjointUnion`，官方日志显示内部 `_contains` 收到 Python tuple 后访问 `.is_Symbol` 报错。D 用公开 `contains` 的补丁避开了这类回归；A 第二次采用 dispatch 路径也为 93/93。该差异不能单独归因于 D 反馈。

官方 F2P 仍失败于 `test_Eq` 和 `test_issue_19378`。本轮再次证明“subset 的一个例子变 True”不足以说明集合关系和相等性需求被整体满足。

### 5.3 SymPy-21379：最明确的入口改善，也最明确地暴露反馈之后的失效

本轮 A/B/C/D 最终都只修改 `hyperbolic.py`，官方均失败于 `test_Mod`。R0、R1 的成功 D 最终包含 `mod.py` 修改，因此补丁落点差异与官方结果一致。

**本轮 D 的关键时间线：**

| 位置 | 已发生的行为 | 意义 |
|---|---|---|
| q1，m2–4 | 原题复现捕获并打印完整 PolynomialError，returncode=0 | 新入口能捕获第一次原始异常 |
| failure-1，m5；第二次调用前 | 交付 `polytools.py`、`mod.py:169 / Mod.eval` 等位置；mod 排名 285→24 | 线索真实到达，仍未进融合 Top-20 |
| q2，m6–9 | Agent 解释 Mod 调用 gcd 的链路，实际读取 `mod.py`、`hyperbolic.py` 等 | 不再能解释为没有阅读目标 |
| q3，m10 | 主动判断应在上层 hyperbolic assumption 加保护 | 修复策略开始偏向绕开触发路径 |
| q4，failure-2，m16 | 新编辑遗漏 Piecewise 导入，NameError 走 rank_update；mod 24→285 | 编辑错误替换了原始缺陷的 F 信号 |
| q6，failure-3，m23 | PolynomialError 再出现；mod 285→24 | 重排额度达到 3 次 |
| 后续 7 个重排候选事件 | 分析完成后被 `route_update_limit` 跳过 | 仍产生较大处理成本 |
| q15，m41 | 编辑报 `old block not found`，后续复现成功使整条命令 rc=0 | 复合命令仍可掩盖前序失败 |
| q17–19 | 扩展检查仍失败；反复重写，曾破坏类定义导致无法导入 tanh | 编辑恢复能力没有覆盖这些实际错误 |
| q20–23 | 恢复源码后仅保留 sinh 的局部 Piecewise 保护，打印原例及一个普通例后提交 | 原例可运行，但最终补丁覆盖不足 |

**对照第一次修复：** R1 第一次重排在 step 4，mod 285→28；R2 在 step 1 就处理原始失败，mod 285→24，而且诊断中直接点名 `Mod.eval`。入口、及时性、诊断可见性都有改善。但 R2 仍未把 mod 提进融合 Top-20，且后续排名发生回退。

需同时保留两个判断：

- 定位系统确实提供了有用线索，Agent 也读到了相关实现，最终失败不能全部算作“找不到文件”。
- 系统仍有可改的问题：新的编辑错误会替换原始 F、消耗重排额度；不能把这些设计问题全部推给 Agent。

不要把 F 内部第 2 名与 L/S/F 融合后的第 24 名混淆。反馈文本中的观察位置、F 排名变化、融合排名变化是三个不同通道；mod 在融合 Top-20 外，但已经通过观察位置被展示。

## 6. 第二次 D 修复：哪些已验证，哪些仍有缺口

| 项目 | 本轮证据 | 判断 |
|---|---|---|
| rc=0 完整 traceback 检测 | 两道 SymPy 的 failure-1 均 rc=0、首次调用触发 | **真实改善**；不能推广为所有 rc=0 失败都能识别 |
| 反馈交付 | 5 个重排上下文、1 个诊断上下文均与轨迹、哈希匹配 | **真实交付**，不是只有 applied 日志 |
| 纯诊断与重排分开 | Django 编辑脚本 SyntaxError 为 diagnostic_only，排名保持 1 | **本轮验证到** |
| edit_recovery | 三题交付次数均为 0 | **未验证到实际恢复效果**；不能因功能已实现就称覆盖成功 |
| 环境错误过滤 | Django settings、缺 pytest 被跳过 | **部分有效** |
| 包装异常过滤 | 测试路径缺失被包装成 InvalidTemplateLibrary 后触发重排 | **仍有误路由** |
| 原始缺陷与编辑错误区分 | 21379 新引入的 NameError 进入 rank_update | **仍会污染排名并占额度** |
| 证据历史保留 | mod 285→24→285→24 | 当前 F 随事件替换，不是保留原始证据的累积定位 |
| 执行来源判定 | 20438 编辑+执行复合命令，及 21379 验证+diff 命令，触发 provenance_required | 防止误认输出有价值，但也会漏掉实际执行失败 |
| 更新上限 | 21379 重排最多交付 3 次 | 上限生效；不等于上限之后停止昂贵分析 |
| 提示要求落地 | 仍捕获异常不退出、用打印代替断言、复合命令掩盖失败、缺测试后直接提交 | 统一提示不足以保证验证行为 |

本轮共 **24 个证据事件、22 个 observed failures、16 个非零返回码动作**。它们是不同计数，不能都写成“失败次数”。24 个事件中，6 个交付、18 个跳过；跳过原因：额度用完 7、弱诊断 4、无源码环境提示 3、来源不明 2、环境配置 1、空输出 1。

## 7. 耗时、Token 与费用

### 7.1 本轮四组资源消耗

以下为三题正式运行之和，未含官方 Harness 时间。首次失败 A 的资源另外报告。

| 条件 | 成功题数 | API 调用 | 总 Token | 报告费用 USD | runtime 秒 |
|---|---:|---:|---:|---:|---:|
| A | 0/3 | 37 | 520,148 | 0.126075 | 132.993 |
| B | 1/3 | 31 | 353,414 | 0.095172 | 101.419 |
| C | 1/3 | 28 | 307,861 | 0.080115 | 86.324 |
| D | 0/3 | 53 | 844,875 | 0.176497 | 458.243 |

本轮 D 相对 C：调用约 1.89 倍、Token 2.74 倍、费用 2.20 倍、runtime 5.31 倍；相对 A：Token 1.62 倍、费用 1.40 倍、runtime 3.45 倍。它们是观察到的总成本差，不是纯反馈模块的因果开销，因为动作轨迹与调用数量不同。

### 7.2 D 的逐题耗时分解

| 任务 | runtime | 初始定位 | 在线反馈总计 | 其中逐事件处理 | 未交付事件处理 | 初始+反馈占 runtime |
|---|---:|---:|---:|---:|---:|---:|
| Django-12262 | 104.971 | 10.802 | 28.431 | 27.062 | 13.060 | 37.38% |
| SymPy-20438 | 114.214 | 49.339 | 39.276 | 39.052 | 29.364 | 77.59% |
| SymPy-21379 | 239.058 | 48.124 | 94.772 | 91.695 | 64.675 | 59.77% |
| 合计 | **458.243** | **108.265** | **162.480** | **157.809** | **107.100** | **59.08%** |

单位均为秒，逐项显示经过四舍五入，总计使用原始精度。

计时口径：

- `runtime_seconds` 为 runner 所记录的 Agent/环境阶段，包含 D 初始化、反馈、模型等待与命令执行；不是从全部预处理开始的端到端时间，也不含官方 Harness。
- `initial_localization_seconds` 包括源码读取、索引与初始定位，不能解释成纯排序算法耗时。
- 新版 `feedback_total_seconds` 除逐事件区段外，还累计普通动作的观察处理和交付前的新鲜度检查等区段。
- 因此本轮 **feedback_total=162.480 秒，并不等于事件之和 157.809 秒**；差额 4.671 秒有源码计时依据，不应判为统计错误。
- `localization_overhead_seconds` 继续是另一套旧口径，不能与上述时间再相加；这些处理时间已经包含在 runtime 中。
- 初始+反馈=270.745 秒，占 59.08%。剩余 187.498 秒包含模型等待、命令、环境与其他工作，不能命名为“纯模型推理”。

### 7.3 为什么没交付也花很多时间

逐事件总计 157.809 秒，其中交付重排 43.596 秒、交付诊断 7.113 秒、跳过事件 107.100 秒。**跳过占 67.87%。**

21379 的 7 个 `route_update_limit` 事件共 **64.673 秒**。源码仅在所有路由额度都耗尽后才早停；重排额度已用完时，恢复/诊断额度仍空余，所以还会读取源码、构造当前索引、分析失败，之后才被重排 gate 拒绝。这解释了“限制三次更新，却仍持续付费处理”的现象。

20438 的空输出事件约 9.744 秒，两个缺 pytest 提示约 19.620 秒。它们最终跳过，但在完整分析之前没有全部被廉价筛掉。优化应保留恢复/诊断机会，同时让可确认的空输出、环境错误和已耗尽路由更早退出，不能简单在第三次重排后关闭所有反馈。

### 7.4 三轮 D 的成本变化

| 轮次 | 成功题数 | API 调用 | 总 Token | USD | legacy/runtime 秒 |
|---|---:|---:|---:|---:|---:|
| R0 | 1/3 | 28 | 221,397 | 0.075360 | 219.165 |
| R1 | 1/3 | 44 | 586,365 | 0.135657 | 210.493 |
| R2 | 0/3 | 53 | 844,875 | 0.176497 | 458.243 |

| 任务 | R1 runtime / Token | R2 runtime / Token | 观察 |
|---|---|---|---|
| Django-12262 | 49.144 / 131,665 | 104.971 / 263,346 | 调查、配置与编辑迭代明显增加，仍 3/4 |
| SymPy-20438 | 73.355 / 256,509 | 114.214 / 110,261 | Token 减少，但初始定位和反馈耗时很高 |
| SymPy-21379 | 87.994 / 198,191 | 239.058 / 471,268 | 多次编辑失败与额度耗尽后的分析，最终从成功变失败 |

R1 初始定位 50.697 秒、在线反馈 38.698 秒；R2 分别为 108.265、162.480 秒。在线反馈计时覆盖范围已有变化，加之事件数从 8 增到 24、运行环境和模型延迟可能不同，不能把比值直接解释为算法退化倍数。能确认的是本轮的实际处理负担显著，而且跳过事件占用了大量时间。

## 8. 为什么 A 也变了？为什么 B/C 这次反而好了？

本轮 A 并不是完全不变的历史控制：虽然 issue/user 文本与 R0 相同，但 system 增加了统一验证要求。实际模型路径也不同。

- Django：R0 A 通过；R2 A 将全部 keyword-only 参数混入必填跟踪，失败于默认值行为。R2 B/C 生成了更完整的参数处理逻辑而通过。
- 21379：R0 A 最终包含 `mod.py` 修改而通过；R2 A 与 B/C/D 都集中在 `hyperbolic.py`，官方直接 Mod 行为仍失败。
- 20438：R0、R2 A 都未成功；R2 另有一次提交格式失败重跑，第二次使用 dispatch 方案，仍未满足 Eq 行为。

不能用“B/C 这次通过 Django”独立证明新提示或定位必然有效，也不能用“D 这次失败”证明反馈必然有害。三题每条件一次的样本，能够提供机制案例，尚不足以估计稳定成功率。值得保留的正面证据是：**相同开发题在本轮可以由 B/C 修通，说明至少 Django 的失败并非任务不可解；同一运行中，D 能给到线索，但补丁与验证仍可能失效。**

## 9. 对此前报告的更新，以及下一步优先级

### 9.1 需要更新的旧判断

| 上午判断 | 本轮后的更新 |
|---|---|
| 捕获并打印的 rc=0 异常可能完全不触发 | 对可信执行形式+完整 traceback 已修好，并有两题真实证据；弱文本、复合命令仍可能不触发 |
| 排名改善未必进入 Top-20 | 仍成立；mod 从 285→24，仍在外面，但诊断已展示且 Agent 实际阅读 |
| 没成功可能是反馈没送进去 | 对本轮 6 次交付不能再这样解释，文本与调用位置已验证 |
| 重复/跳过反馈也有成本 | 本轮进一步量化：未交付事件 107.100 秒；额度耗尽事件 64.673 秒 |
| 自测覆盖不足 | 仍成立；统一提示后依旧没有可靠闭环，而且 Django 换了一种遗漏 |
| Agent 自己制造的错误占用反馈 | 不仅占机会，还能把原始目标排名从 24 冲回 285 |

### 9.2 最值得先处理的事项（仅建议，本次未修改）

1. **P0：保证可用的普通测试入口与完成条件。** 缺 pytest、Django settings/import path 问题反复阻断验证。由运行集成侧提供固定环境检查和基于公开仓库的正常测试入口；把公开 issue 的行为分解为需要逐项验证的条件，特别是默认/必填参数、subset/Eq。不能把官方隐藏测试倒灌进 Agent。
2. **P0：区分原始缺陷定位与编辑后故障，保护已获得的证据。** 新引入的 NameError/ImportError 不应无条件覆盖原始 F 并消耗同一重排预算；但也不能把所有这类异常一律视为编辑错误。应结合发生时点、修改文件、此前有效状态与异常链。运行集成和失败分析侧共同处理。
3. **P1：改进环境包装异常和复合命令来源判定。** `InvalidTemplateLibrary ← ModuleNotFoundError(template_tests)` 是实际误重排案例；20438 的编辑+验证命令是实际漏反馈案例。优先让执行层提供可信的分段状态，减少靠整条 shell 文本猜测。
4. **P1：尽早过滤无效处理，降低源码快照成本。** 对空输出、明确环境故障及无增量证据增加廉价门控；额度管理需区分三条路由。通过事件耗时与快照次数验证，不仅看反馈条数。
5. **P2：再评估排名展示与 F 权重。** 本轮 mod 在 F 中第 2、融合第 24，存在展示覆盖差异；但诊断已让 Agent 阅读它，所以单纯提高 F 权重不能解释或解决所有失败。先解决路由和验证，不应直接把提高权重当作下一轮唯一改动。

角色 5 可以独立继续做：固定本轮结果口径、保留失败重跑成本、逐事件标注原始缺陷/编辑/环境来源、区分融合排名与诊断可见性、审计送达后的阅读与修改、统一各轮时间范围。路由、运行接口、提示执行约束和快照优化需要对应实现角色配合。

最小验证路线可先用本次已保存输出做离线接口回放：rc=0 完整 traceback 应识别；环境包装异常不应污染排序；编辑错误不应抹掉先前缺陷证据；路由额度耗尽后仍可恢复但不应反复支付完整无效重排分析。之后再固定提示、模型、预算，做小规模 C/D 配对重跑。离线回放通过只证明接口行为，不证明修复成功率提升。本次未运行这些验证。

## 10. 可以直接用于汇报的表述

> 第二次修复改善了失败反馈的识别和交付：两道任务在首次执行中产生的零退出码异常被及时识别，反馈明确指出相关源码位置；纯诊断消息也在不改变排名的情况下送达。然而，在同三题的完整 A/B/C/D 实验中，D 未增加官方修复成功，且耗时显著增加。轨迹显示，效果受限于编辑错误覆盖原始定位证据、环境与执行来源分类缺口，以及 Agent 在获得正确线索后仍生成不完整补丁、未完成公开需求验证。这些结果支持反馈链路的工程改进，但尚不支持端到端修复效果提升。

## 附录 A：正式运行身份

| 任务 | A | B | C | D |
|---|---|---|---|---|
| Django-12262 | `django__django-12262_A_fdb03f0c` | `django__django-12262_B_0cb25592` | `django__django-12262_C_f7bea977` | `django__django-12262_D_8e8f2e74` |
| SymPy-20438 | `sympy__sympy-20438_A_f83ce396`（attempt 2） | `sympy__sympy-20438_B_156e5618` | `sympy__sympy-20438_C_9370bc0e` | `sympy__sympy-20438_D_f3f4271b` |
| SymPy-21379 | `sympy__sympy-21379_A_7a93a156` | `sympy__sympy-21379_B_08d73eba` | `sympy__sympy-21379_C_fcc8739d` | `sympy__sympy-21379_D_d53c8237` |

## 附录 B：D 的 24 个证据事件

“拟议排名”在 skipped 事件中没有被应用。下表仅对实际应用事件填写排名变化；failure 编号在每个运行内独立。

| 任务 | 事件 | step / action | 结果 | 原因或通道 | 秒 | 实际目标排名变化 |
|---|---|---|---|---|---:|---|
| 12262 | 1 | 4 / 5 | 跳过 | environment_configuration_error | 6.472 | — |
| 12262 | 2 | 4 / 6 | 跳过 | environment_hint_without_source | 6.584 | — |
| 12262 | 3 | 5 / 8 | 交付 | rank_update；InvalidTemplateLibrary | 6.888 | library 1→1 |
| 12262 | 4 | 6 / 9 | 跳过 | weak_diagnostic_only | 0.001 | — |
| 12262 | 5 | 9 / 12 | 跳过 | weak_diagnostic_only | 0.001 | — |
| 12262 | 6 | 12 / 15 | 跳过 | weak_diagnostic_only | 0.001 | — |
| 12262 | 7 | 14 / 17 | 交付 | diagnostic_only；编辑脚本 SyntaxError | 7.113 | 保持 1 |
| 12262 | 8 | 19 / 22 | 跳过 | weak_diagnostic_only | 0.001 | — |
| 20438 | 1 | 1 / 3 | 交付 | rank_update；AttributeError，rc=0 | 9.688 | relational 1→1；其余目标不变 |
| 20438 | 2 | 2 / 6 | 跳过 | empty_output | 9.744 | — |
| 20438 | 3 | 5 / 13 | 跳过 | provenance_required | 0.001 | — |
| 20438 | 4 | 6 / 14 | 跳过 | environment_hint_without_source | 9.962 | — |
| 20438 | 5 | 6 / 15 | 跳过 | environment_hint_without_source | 9.658 | — |
| 21379 | 1 | 1 / 1 | 交付 | rank_update；PolynomialError，rc=0 | 9.556 | mod 285→24 |
| 21379 | 2 | 4 / 9 | 交付 | rank_update；新引入 NameError | 8.671 | mod 24→285 |
| 21379 | 3 | 6 / 13 | 交付 | rank_update；PolynomialError | 8.792 | mod 285→24 |
| 21379 | 4 | 8 / 15 | 跳过 | route_update_limit | 9.051 | — |
| 21379 | 5 | 9 / 16 | 跳过 | route_update_limit | 8.786 | — |
| 21379 | 6 | 11 / 18 | 跳过 | route_update_limit | 8.983 | — |
| 21379 | 7 | 12 / 19 | 跳过 | route_update_limit | 8.976 | — |
| 21379 | 8 | 13 / 20 | 跳过 | route_update_limit | 10.064 | — |
| 21379 | 9 | 17 / 24 | 跳过 | provenance_required | 0.002 | — |
| 21379 | 10 | 18 / 25 | 跳过 | route_update_limit | 9.439 | — |
| 21379 | 11 | 19 / 26 | 跳过 | route_update_limit；ImportError | 9.374 | — |

## 附录 C：证据路径与复核文件

- [原始压缩包（原归档哈希）](../evidence/manifest.json)
- 本轮解压后的证据说明（历史引用，见文末材料范围说明）
- [本次独立计算与核查结果](../results/analysis.json)
- [离线审计脚本](../tools/offline_eval/README.md)：只读取已保存的结果、哈希、轨迹、补丁与日志，不执行被审计代码。
- [正式运行选择记录](../evidence/provenance/d_fix2_abcd/evaluation/selected/selection.json)
- [本轮结果索引](../results/run_summary.csv)
- [本轮反馈事件索引](../results/feedback_events.csv)
- [原三题与第一次 D 修复报告](../reports/02_three_task_d_evolution.md)
- 上午综合交叉对比（历史引用，见文末材料范围说明）
- [原三题历史审计](../reports/01_original_eight_tasks.md)

本轮 ZIP SHA-256：`4fad29676bd733d301b36cb4d34270adeeab1c611af946a9798f3eec8d761ccc`。

原始证据中的 `/root/projects/...` 是服务器运行路径；本地证据根为 `历史归档/tmp/d_second_fix_review/failure_feedback_247c125_abcd_20261027_offline_analysis/`。各运行位于其 `runs/attempt_*/runs/<run_id>/`，官方结果位于 `evaluation/selected/logs/evaluation/closedloop247-selected-<condition>/closedloop247_selected_<condition>/<task_id>/`。

本报告的目标文件集合沿用此前的离线评价代理，用于结果分析；它不是唯一合法修复位置，也没有作为本轮 Agent 的输入。


## 第一次修复的详细历史分析

以下为第一次修复时的完整诊断。它只代表当时已知情况；第二次修复后的判断以本报告前半部分为准。特别是两道 SymPy 的退出码 0 traceback，第一次仍未可靠交付，第二次才验证了改进。

## 原三题与 D 修复重跑合并分析

分析日期：2026-10-27。分析对象：原 `dev3_extra_abcd_v1` 的 12 个有效 A/B/C/D 运行，以及 `d_feedback_rerun_20261027.tar.gz` 中的 3 个新版 D 运行。本文保留旧实验的身份，不把旧 A/B/C 与新 D 拼成一次同时执行的实验。

### 1. 结论

**D 的反馈链路和记录能力有改善，但这次没有增加官方修复成功数。** 原 D 和新 D 都只通过 SymPy-21379，均为 1/3。Django-12262 从 2/4 个 FAIL_TO_PASS 测试通过增加到 3/4，属于局部改善；SymPy-20438 仍为 0/2，并新增一个 PASS_TO_PASS 回归。

新 D 三题均有反馈实际送到后续模型调用，共观察 8 个进入分析的失败事件，应用 4 次更新。原 D 只有 Django 一题发生更新。这个变化说明机制在本轮轨迹中更活跃，**不等于修复成功率提高，也不能仅凭更新次数把变化全归因于代码修复**：新旧运行生成了不同的命令和错误。

本轮 D 初始定位用时 50.697 秒，反馈处理用时 38.698 秒，合计 89.395 秒，占记录运行时间 210.493 秒的 42.47%。这些时间已包含在运行时间中，不能再次相加。约一半反馈处理时间花在最终没有注入的事件上。

### 2. 来源与审计范围

- 旧分析：[原三题报告](../reports/01_original_eight_tasks.md)及同目录 `analysis.json`。
- 新产物：[D 修复重跑压缩包（原归档哈希）](../evidence/manifest.json)。包内已有 `analysis_v2/REPORT_v2.md`；本文结合该历史说明，重新核对原始运行、usage、事件、轨迹、提交补丁和官方日志，并补充跨批次解释与耗时口径。
- 旧轨迹根目录：`server-dev8-download-20261026-01/extracted-dev8-handoff-01/experiments/dev3_extra_abcd_v1/runs/`。
- 新运行根目录（以下均为压缩包成员路径）：`d_feedback_rerun_20261027/runs/<run_id>/`。
- 新官方结果：`d_feedback_rerun_20261027/evaluation/logs/evaluation/personal-d-feedback-20261027/personal_d_11dd3fa_20261027/<task_id>/`。
- 新快照记录的源提交为 `11dd3faebaa70edefac2e23d027bad8f4c922f6a`。分析依据包内实际快照，不以当前工作目录的 HEAD 代替实验版本。

本次只做离线审计，没有重跑 Agent、调用付费模型、重跑 Harness 或修改项目实现。没有查看参考修复补丁的代码；定位目标文件沿用原报告的离线评价代理。官方日志用于解释已经发生的失败，不应再反向作为这些开发题的独立测试设计依据。

新 3 个运行的 `patch.diff` 与预测中的 `model_patch` 均一致，也均与官方评测实际使用的补丁一致。Token 按每次响应的 usage 累加；包括一次格式错误响应，不能只取最后一条 usage。缓存输入是输入 token 的子集，不能再加到总 token 上。

### 3. 官方修复结果：旧 A/B/C/D 和新 D

| 任务 | 旧 A：结果/F2P/P2P | 旧 B | 旧 C | 旧 D | 新 D |
| --- | --- | --- | --- | --- | --- |
| Django-12262 | 成功；4/4；18/18 | 失败；1/4；18/18 | 失败；2/4；18/18 | 失败；2/4；18/18 | 失败；3/4；18/18 |
| SymPy-20438 | 失败；0/2；92/93 | 失败；0/2；93/93 | 失败；0/2；93/93 | 失败；0/2；93/93 | 失败；0/2；92/93 |
| SymPy-21379 | 成功；1/1；91/91 | 失败；0/1；91/91 | 成功；1/1；91/91 | 成功；1/1；91/91 | 成功；1/1；91/91 |

F2P 表示 FAIL_TO_PASS，通过缺陷相关测试；P2P 表示 PASS_TO_PASS，原本应通过的回归测试。一个测试函数可能包含多个断言，3/4 不等于修好了 75% 的全部语义。`completed / Submitted` 只表示提交完成，不能替代 `resolved`。

原三题总体是 A=2/3、B=0/3、C=1/3、D=1/3。新包只重跑 D，不能写成“新版 A=2/3、B=0/3、C=1/3、D=1/3”；正确表达是“历史 A/B/C 作为背景，新 D 为 1/3”。

#### 3.1 Django-12262：找到了正确文件，缺少完整的参数语义

新运行：`django__django-12262_D_6fa50936`。

1. q1–q2 已阅读 `django/template/library.py`，初始目标文件排名第 1，定位不存在明显缺口。
2. q3 将 `unhandled_kwargs` 改为全部 keyword-only 参数。这让“有默认值的参数被显式传入”更容易通过，却混淆了“允许出现的参数”和“缺省时必须提供的参数”。
3. q4 的自测主要覆盖显式传参及打印重复参数异常，没有覆盖省略默认参数。
4. q6、q8 的编辑过程引入 SyntaxError / IndentationError。第一个失败触发反馈，第二个因为没有映射到源码而跳过。
5. q10 整理实现并进行编译和有限检查，随后提交。官方 F2P 3/4，P2P 18/18；`test_simple_tags` 仍因默认参数被错误视为必填而失败。

所以这题的剩余问题不是“D 没告诉它文件在哪”，而是**补丁没有保留默认值的正确行为，自测又没有把这个行为当作必须满足的条件**。

D 的第一次更新将目标排名从 1 降到 2。实际映射的是导入链中的 `django/template/__init__.py` 和 `engine.py`；发生语法问题的文件在当时不能正常解析，反馈并未形成更准确的目标函数证据。文件还在 Top-20，但排名变化本身没有改善这题的语义判断。

#### 3.2 SymPy-20438：不再抛异常不等于集合相等关系正确

新运行：`sympy__sympy-20438_D_9f878f69`。

1. q1 检查 subset 与集合相等，捕获异常后打印，返回码为 0，没有触发 D。
2. q4–q5 修改 ProductSet 的 subset/superset 行为，随后在 `Eq(...).simplify()` 遇到 `EmptySet` 没有 `.equals` 的异常，触发唯一一次更新；反馈在 q6 前送达。
3. q6 后继续读 `relational.py`，q9 添加 `hasattr(dif, "equals")` 防护。q10 的 subset 结果变成 True/True，但 Eq 仍保留为未求值表达式。
4. 后续推理把相等性当作更广的语义问题，最终仍提交；q15 发生一次格式错误，q16 完成提交。

官方 F2P 0/2，分别仍涉及 `test_Eq` 和 `test_issue_19378`。此外，新增的 `all(tuple(elem) in other for elem in self)` 在不能确定成员关系时强制要求布尔值，使 `test_Complement` 抛出 TypeError，P2P 从旧 D 的 93/93 降至 92/93。

D 已把运行期异常映射到 `relational.py`，但它原本就排第 1；另外两个离线参考文件 `comparison.py`、`issubset.py` 仍排 120、98，未进入 Top-20。反馈没有自动生成正确的集合语义，也没有要求 Agent 完成全部验证条件。

#### 3.3 SymPy-21379：最终修到 Mod，但不能证明是 D 带来的新增成功

新运行：`sympy__sympy-21379_D_4da3cd9f`。

1. q1 捕获原始 PolynomialError 并打印，进程返回 0，没有触发 D。
2. q2 已主动查看 `sympy/core/mod.py`，发生在第一次 D 更新之前。
3. q4 的复现仍失败，第一次反馈在 q5 前送达，`mod.py` 从第 285 到第 28。
4. q5 添加 Piecewise 判断但漏导入，产生 NameError；第二次反馈在 q6 前送达，排名从 28 到 27。
5. q6、q8、q11 的相似 NameError 被判定 `duplicate_context`，没有继续注入。
6. q12–q13 找到实际导入位置并修好，q14–q15 只导出 `mod.py` 补丁。官方在干净环境应用这个提交后通过 F2P 1/1、P2P 91/91。

这里需要区分三个证据：

- **排名证据**：285→28→27 确实变好，但仍未进入注入列表 Top-20。第一次更新的 ΔRR 约为 0.03221，不能写成“目标进入了提示列表”。
- **诊断证据**：反馈消息除了列表，还有异常与映射位置；第二次反馈能包含 `mod.py` 的具体位置。因此“没有进入 Top-20”也不意味着所有反馈通道都没有提到它。
- **因果证据**：Agent 在更新前已查看目标，旧 D 在没有更新时也修好了此题。只能确认“新版 D 运行最终成功”，不能据此断言“D 反馈造成成功”。

局部自测时工作区还曾修改 `hyperbolic.py`，但最终官方评测只应用导出的 `mod.py` 补丁。官方通过才消除了“是否依赖未提交修改”的疑问，不能只凭工作区复现成功下结论。

### 4. D 修复到底验证到了什么

| 检查点 | 本轮证据 | 结论边界 |
|---|---|---|
| 反馈真正送入模型 | 4 次 applied 均在后续响应前存在对应上下文 | 支持链路可用，不只是日志写了 applied |
| 失败诊断和排名一起提供 | 包内消息及源码 `format_feedback_evidence` 可核对 | 不代表每次诊断都命中真正待修复原因 |
| 重复上下文抑制 | 21379 的三个 NameError 后续事件被跳过 | 能避免重复注入，仍已支付分析开销 |
| 环境错误隔离 | 本轮没有足够环境负例；另两批提供了负例 | 不把没有覆盖的场景写成已验证 |
| rc=0 异常输出 | 新三题仍有捕获后打印、未触发的记录 | 检测入口尚未全面解决；支持可信 runtime 元数据不等于执行器已提供它 |
| 官方修复质量 | 1/3→1/3；Django 部分测试改善，20438 新增回归 | 尚无总体收益证据 |

`first usable failure` 不是外部 C 运行第一次失败。D 从自己的初始 C 式上下文开始，独立行动，处理自己轨迹里的失败。本轮没有保存 C/D 共用前缀的成对分叉实验，所以不能把旧 C 的轨迹当作新版 D 的前半段。

### 5. 新增 D 耗时分析

#### 5.1 四种时间不能混用

| 字段/指标 | 本报告含义 | 注意事项 |
|---|---|---|
| `runtime_seconds` | runner 中开始创建 Agent/环境至清理结束的记录时长 | 含 D 初始定位、在线反馈、模型等待和命令执行；不含官方 Harness；不是项目从预处理开始的全流程时间 |
| `initial_localization_seconds` | D 控制器初始化阶段的源码快照、索引/定位、初始排名等 | 包含远程读取与相关文件处理，不是单纯 RRF 算术耗时 |
| `feedback_processing_seconds` | 每个事件的分析、后续筛选/重排/注入与确认等已埋点区段的累计 | 不含导致失败的原命令运行时间，不含后续模型调用等待；也未覆盖检测及所有持久化区段 |
| `feedback_total_seconds` | 所有事件上一项之和，含 skipped | 是已测反馈处理成本，不是完整 D 增量成本 |

旧 `localization_overhead_seconds` 是另一套历史计时范围，主要累计初始化与 execute 侧分析，没有完整覆盖 query 侧后续处理。新旧字段不强行替换，也不把三个定位字段相加。

#### 5.2 每题分项

| 任务 | 失败事件 | 应用更新 | runtime 秒 | 初始定位秒 | 反馈处理秒 | 两项合计秒 | 已测定位占比 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Django-12262 | 2 | 1 | 49.144 | 6.172 | 7.810 | 13.982 | 28.45% |
| SymPy-20438 | 1 | 1 | 73.355 | 22.100 | 5.141 | 27.241 | 37.14% |
| SymPy-21379 | 5 | 2 | 87.994 | 22.425 | 25.747 | 48.172 | 54.74% |

“已测定位占比”=(初始定位+反馈处理)/runtime，只用于说明本次记录内部的时间分布。runtime 减去这两项还包括模型等待、普通命令、环境设置和其他未单列工作，不能命名为“纯模型推理时间”。

#### 5.3 每个失败事件也有成本

| 任务 | 事件 | 触发 step | 处理 | 理由 | 送达后的响应 | 处理秒 | 离线目标排名变化 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Django-12262 | failure-1 | 6 | 应用 | 可映射且通过门控 | q7 | 3.932 | library.py 1→2 |
| Django-12262 | failure-2 | 8 | 跳过 | no_mapped_source | — | 3.878 | 未记录/未生成 |
| SymPy-20438 | failure-1 | 5 | 应用 | 可映射且通过门控 | q6 | 5.141 | relational.py 1→1；comparison.py 120→120；issubset.py 98→98 |
| SymPy-21379 | failure-1 | 4 | 应用 | 可映射且通过门控 | q5 | 5.210 | mod.py 285→28 |
| SymPy-21379 | failure-2 | 5 | 应用 | 可映射且通过门控 | q6 | 5.147 | mod.py 28→27 |
| SymPy-21379 | failure-3 | 6 | 跳过 | duplicate_context | — | 5.069 | 未记录/未生成 |
| SymPy-21379 | failure-4 | 8 | 跳过 | duplicate_context | — | 5.132 | 未记录/未生成 |
| SymPy-21379 | failure-5 | 11 | 跳过 | duplicate_context | — | 5.189 | 未记录/未生成 |

8 个事件中应用 4 次、跳过 4 次。应用事件处理合计约 19.430 秒；跳过事件约 19.268 秒，占反馈处理的 49.79%。原因是分析与工作区读取已经发生，之后才做去重、可用性和注入决策。**“没更新”不代表“没花时间”。**

21379 的反馈处理 25.747 秒中约 15.390 秒花在三次重复上下文上。可见去重减少了提示内容重复，但本轮没有避免对应的前置分析工作；这是后续优化的候选点，不是本次已执行的修改。

#### 5.4 新旧成本对照

| 任务 | 版本 | 完整 run_id | 调用 | 总 token | 记录 USD | legacy/runtime 秒 |
| --- | --- | --- | --- | --- | --- | --- |
| Django-12262 | 旧 D | django__django-12262_D_e10b202e | 10 | 80,451 | 0.030454 | 107.917 |
| Django-12262 | 新 D | django__django-12262_D_6fa50936 | 13 | 131,665 | 0.037583 | 49.144 |
| SymPy-20438 | 旧 D | sympy__sympy-20438_D_124384a9 | 7 | 59,181 | 0.019886 | 62.377 |
| SymPy-20438 | 新 D | sympy__sympy-20438_D_9f878f69 | 16 | 256,509 | 0.052770 | 73.355 |
| SymPy-21379 | 旧 D | sympy__sympy-21379_D_b9d3b913 | 11 | 81,765 | 0.025019 | 48.871 |
| SymPy-21379 | 新 D | sympy__sympy-21379_D_4da3cd9f | 15 | 198,191 | 0.045304 | 87.994 |

旧 D 总 token 为 221,397，新 D 为 586,365，约 2.65 倍；模型调用从 28 到 44，费用记录约从 0.075360 到 0.135657 美元。官方成功仍为 1/3。这个观察支持“本轮新增反馈活动没有转化为更多成功”，不能推出代码修复必然使所有任务更贵。

原报告主表使用更宽的 `agent_wall_seconds`；本表为便于对照使用旧 `legacy_runtime_seconds` 与新 `runtime_seconds`。旧初始化/在线反馈的独立分项没有完整记录，必须留未知，不能拿旧 `localization_overhead_seconds` 当旧在线反馈时间。跨日模型延迟、缓存、命令路径和机器状态也不同，不能将运行时间差直接解释成 D 修复提速或减速。

### 6. 与旧分析衔接后的判断

原报告的三条核心判断仍成立：定位排名与官方修复必须分开；20438 的多文件与语义问题没有被解决；运行时异常可见不代表反馈入口一定触发。新增证据把它们进一步具体化：

1. D 可以有真实送达而没有收益，问题已不能全部解释为“反馈没有传进去”。
2. Agent 自己制造的语法错误、漏导入也会占用反馈机会；这些是运行中的真实问题，但不等同于原始缺陷的有效定位信号。
3. 改善完整排名未必改善 Top-20；21379 就是明确例子。
4. D 有可观且可测的定位处理成本，尤其重复事件；旧报告无法单独量化这一点，现在可以。

下一步评价应继续以 A–D 为主要任务结果比较，以 C–D 解释反馈增量，同时单独报告触发率、实际送达、目标是否进入上下文及耗时。不能只选“D 触发了”的题作为主成功率分母，也不能把重跑的同三题当成新增独立样本。

### 7. 追溯索引

各运行目录重点文件：`run_result.json`、`trajectory.json`、`patch.diff`、`predictions.jsonl`、`localization_candidates.json`、`prompt_candidates.json`、`failure_feedback/feedback_summary.json`、`failure_feedback/failure_updates.jsonl`、`failure_feedback/observations.jsonl`。具体目录名以压缩包清单为准。

轨迹中 q 表示第几次有记录的模型响应，m 表示 `messages` 的零基索引。一次 q 可能包含多个命令；命令数、失败数、模型调用数不能互换。

包 SHA256：`951f8a5d048c20f18db1b130c5b387894228162e0ede4a2b2e0a301d3c5dbefa`。

后续批次见函数提示实验（历史引用，见文末材料范围说明）、验证提示实验（历史引用，见文末材料范围说明），整体判断见综合交叉对比（历史引用，见文末材料范围说明）。

## 随包证据索引

| 实验 | 任务 | 条件/尝试 | 入选 | 运行、轨迹、官方结果 |
|---|---|---|---|---|
| original_dev3 | sympy__sympy-21379 | A / 1 | 是 | [记录](../evidence/records/original_dev3/sympy__sympy-21379_A_713ba62f/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0096) · [补丁](../evidence/records/original_dev3/sympy__sympy-21379_A_713ba62f/patch.diff) · [官方](../evidence/records/original_dev3/sympy__sympy-21379_A_713ba62f/official/report.json) |
| original_dev3 | sympy__sympy-21379 | B / 1 | 是 | [记录](../evidence/records/original_dev3/sympy__sympy-21379_B_514ce584/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0099) · [补丁](../evidence/records/original_dev3/sympy__sympy-21379_B_514ce584/patch.diff) · [官方](../evidence/records/original_dev3/sympy__sympy-21379_B_514ce584/official/report.json) |
| original_dev3 | sympy__sympy-21379 | C / 1 | 是 | [记录](../evidence/records/original_dev3/sympy__sympy-21379_C_3476e59b/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0102) · [补丁](../evidence/records/original_dev3/sympy__sympy-21379_C_3476e59b/patch.diff) · [官方](../evidence/records/original_dev3/sympy__sympy-21379_C_3476e59b/official/report.json) |
| original_dev3 | sympy__sympy-21379 | D / 1 | 是 | [记录](../evidence/records/original_dev3/sympy__sympy-21379_D_b9d3b913/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0107) · [补丁](../evidence/records/original_dev3/sympy__sympy-21379_D_b9d3b913/patch.diff) · [官方](../evidence/records/original_dev3/sympy__sympy-21379_D_b9d3b913/official/report.json) |
| original_dev3 | django__django-12262 | A / 1 | 否 | [记录](../evidence/records/original_dev3/django__django-12262_A_a44e4d1e/run_result.json) · [补丁](../evidence/records/original_dev3/django__django-12262_A_a44e4d1e/patch.diff) |
| original_dev3 | django__django-12262 | B / 1 | 否 | [记录](../evidence/records/original_dev3/django__django-12262_B_682184bf/run_result.json) · [补丁](../evidence/records/original_dev3/django__django-12262_B_682184bf/patch.diff) |
| original_dev3 | django__django-12262 | C / 1 | 否 | [记录](../evidence/records/original_dev3/django__django-12262_C_f998ec07/run_result.json) · [补丁](../evidence/records/original_dev3/django__django-12262_C_f998ec07/patch.diff) |
| original_dev3 | django__django-12262 | D / 1 | 是 | [记录](../evidence/records/original_dev3/django__django-12262_D_e10b202e/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0076) · [补丁](../evidence/records/original_dev3/django__django-12262_D_e10b202e/patch.diff) · [官方](../evidence/records/original_dev3/django__django-12262_D_e10b202e/official/report.json) |
| original_dev3 | sympy__sympy-20438 | A / 1 | 否 | [记录](../evidence/records/original_dev3/sympy__sympy-20438_A_24b09c2b/run_result.json) · [补丁](../evidence/records/original_dev3/sympy__sympy-20438_A_24b09c2b/patch.diff) |
| original_dev3 | sympy__sympy-20438 | B / 1 | 否 | [记录](../evidence/records/original_dev3/sympy__sympy-20438_B_a4e8e3f0/run_result.json) · [补丁](../evidence/records/original_dev3/sympy__sympy-20438_B_a4e8e3f0/patch.diff) |
| original_dev3 | sympy__sympy-20438 | C / 1 | 否 | [记录](../evidence/records/original_dev3/sympy__sympy-20438_C_84d97108/run_result.json) · [补丁](../evidence/records/original_dev3/sympy__sympy-20438_C_84d97108/patch.diff) |
| original_dev3 | sympy__sympy-20438 | D / 1 | 是 | [记录](../evidence/records/original_dev3/sympy__sympy-20438_D_124384a9/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0093) · [补丁](../evidence/records/original_dev3/sympy__sympy-20438_D_124384a9/patch.diff) · [官方](../evidence/records/original_dev3/sympy__sympy-20438_D_124384a9/official/report.json) |
| original_dev3 | django__django-12262 | A / 2 | 是 | [记录](../evidence/records/original_dev3/django__django-12262_A_4aedcb24/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0062) · [补丁](../evidence/records/original_dev3/django__django-12262_A_4aedcb24/patch.diff) · [官方](../evidence/records/original_dev3/django__django-12262_A_4aedcb24/official/report.json) |
| original_dev3 | django__django-12262 | B / 2 | 是 | [记录](../evidence/records/original_dev3/django__django-12262_B_07bad546/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0066) · [补丁](../evidence/records/original_dev3/django__django-12262_B_07bad546/patch.diff) · [官方](../evidence/records/original_dev3/django__django-12262_B_07bad546/official/report.json) |
| original_dev3 | django__django-12262 | C / 2 | 是 | [记录](../evidence/records/original_dev3/django__django-12262_C_530a2f4d/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0070) · [补丁](../evidence/records/original_dev3/django__django-12262_C_530a2f4d/patch.diff) · [官方](../evidence/records/original_dev3/django__django-12262_C_530a2f4d/official/report.json) |
| original_dev3 | sympy__sympy-20438 | A / 2 | 是 | [记录](../evidence/records/original_dev3/sympy__sympy-20438_A_d53bdc45/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0080) · [补丁](../evidence/records/original_dev3/sympy__sympy-20438_A_d53bdc45/patch.diff) · [官方](../evidence/records/original_dev3/sympy__sympy-20438_A_d53bdc45/official/report.json) |
| original_dev3 | sympy__sympy-20438 | B / 2 | 是 | [记录](../evidence/records/original_dev3/sympy__sympy-20438_B_253ef3a1/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0083) · [补丁](../evidence/records/original_dev3/sympy__sympy-20438_B_253ef3a1/patch.diff) · [官方](../evidence/records/original_dev3/sympy__sympy-20438_B_253ef3a1/official/report.json) |
| original_dev3 | sympy__sympy-20438 | C / 2 | 是 | [记录](../evidence/records/original_dev3/sympy__sympy-20438_C_258b0715/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0087) · [补丁](../evidence/records/original_dev3/sympy__sympy-20438_C_258b0715/patch.diff) · [官方](../evidence/records/original_dev3/sympy__sympy-20438_C_258b0715/official/report.json) |
| d_fix1 | django__django-12262 | D / 1 | 是 | [记录](../evidence/records/d_fix1/django__django-12262_D_6fa50936/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0005) · [补丁](../evidence/records/d_fix1/django__django-12262_D_6fa50936/patch.diff) · [官方](../evidence/records/d_fix1/django__django-12262_D_6fa50936/official/report.json) |
| d_fix1 | sympy__sympy-20438 | D / 1 | 是 | [记录](../evidence/records/d_fix1/sympy__sympy-20438_D_9f878f69/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0010) · [补丁](../evidence/records/d_fix1/sympy__sympy-20438_D_9f878f69/patch.diff) · [官方](../evidence/records/d_fix1/sympy__sympy-20438_D_9f878f69/official/report.json) |
| d_fix1 | sympy__sympy-21379 | D / 1 | 是 | [记录](../evidence/records/d_fix1/sympy__sympy-21379_D_4da3cd9f/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0015) · [补丁](../evidence/records/d_fix1/sympy__sympy-21379_D_4da3cd9f/patch.diff) · [官方](../evidence/records/d_fix1/sympy__sympy-21379_D_4da3cd9f/official/report.json) |
| d_fix2_abcd | django__django-12262 | A / 1 | 是 | [记录](../evidence/records/d_fix2_abcd/django__django-12262_A_fdb03f0c/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0018) · [补丁](../evidence/records/d_fix2_abcd/django__django-12262_A_fdb03f0c/patch.diff) · [官方](../evidence/records/d_fix2_abcd/django__django-12262_A_fdb03f0c/official/report.json) |
| d_fix2_abcd | django__django-12262 | B / 1 | 是 | [记录](../evidence/records/d_fix2_abcd/django__django-12262_B_0cb25592/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0021) · [补丁](../evidence/records/d_fix2_abcd/django__django-12262_B_0cb25592/patch.diff) · [官方](../evidence/records/d_fix2_abcd/django__django-12262_B_0cb25592/official/report.json) |
| d_fix2_abcd | django__django-12262 | C / 1 | 是 | [记录](../evidence/records/d_fix2_abcd/django__django-12262_C_f7bea977/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0024) · [补丁](../evidence/records/d_fix2_abcd/django__django-12262_C_f7bea977/patch.diff) · [官方](../evidence/records/d_fix2_abcd/django__django-12262_C_f7bea977/official/report.json) |
| d_fix2_abcd | django__django-12262 | D / 1 | 是 | [记录](../evidence/records/d_fix2_abcd/django__django-12262_D_8e8f2e74/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0029) · [补丁](../evidence/records/d_fix2_abcd/django__django-12262_D_8e8f2e74/patch.diff) · [官方](../evidence/records/d_fix2_abcd/django__django-12262_D_8e8f2e74/official/report.json) |
| d_fix2_abcd | sympy__sympy-20438 | A / 1 | 否 | [记录](../evidence/records/d_fix2_abcd/sympy__sympy-20438_A_771ea469/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0031) · [补丁](../evidence/records/d_fix2_abcd/sympy__sympy-20438_A_771ea469/patch.diff) |
| d_fix2_abcd | sympy__sympy-20438 | B / 1 | 是 | [记录](../evidence/records/d_fix2_abcd/sympy__sympy-20438_B_156e5618/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0037) · [补丁](../evidence/records/d_fix2_abcd/sympy__sympy-20438_B_156e5618/patch.diff) · [官方](../evidence/records/d_fix2_abcd/sympy__sympy-20438_B_156e5618/official/report.json) |
| d_fix2_abcd | sympy__sympy-20438 | C / 1 | 是 | [记录](../evidence/records/d_fix2_abcd/sympy__sympy-20438_C_9370bc0e/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0040) · [补丁](../evidence/records/d_fix2_abcd/sympy__sympy-20438_C_9370bc0e/patch.diff) · [官方](../evidence/records/d_fix2_abcd/sympy__sympy-20438_C_9370bc0e/official/report.json) |
| d_fix2_abcd | sympy__sympy-20438 | D / 1 | 是 | [记录](../evidence/records/d_fix2_abcd/sympy__sympy-20438_D_f3f4271b/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0045) · [补丁](../evidence/records/d_fix2_abcd/sympy__sympy-20438_D_f3f4271b/patch.diff) · [官方](../evidence/records/d_fix2_abcd/sympy__sympy-20438_D_f3f4271b/official/report.json) |
| d_fix2_abcd | sympy__sympy-21379 | A / 1 | 是 | [记录](../evidence/records/d_fix2_abcd/sympy__sympy-21379_A_7a93a156/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0048) · [补丁](../evidence/records/d_fix2_abcd/sympy__sympy-21379_A_7a93a156/patch.diff) · [官方](../evidence/records/d_fix2_abcd/sympy__sympy-21379_A_7a93a156/official/report.json) |
| d_fix2_abcd | sympy__sympy-21379 | B / 1 | 是 | [记录](../evidence/records/d_fix2_abcd/sympy__sympy-21379_B_08d73eba/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0051) · [补丁](../evidence/records/d_fix2_abcd/sympy__sympy-21379_B_08d73eba/patch.diff) · [官方](../evidence/records/d_fix2_abcd/sympy__sympy-21379_B_08d73eba/official/report.json) |
| d_fix2_abcd | sympy__sympy-21379 | C / 1 | 是 | [记录](../evidence/records/d_fix2_abcd/sympy__sympy-21379_C_fcc8739d/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0054) · [补丁](../evidence/records/d_fix2_abcd/sympy__sympy-21379_C_fcc8739d/patch.diff) · [官方](../evidence/records/d_fix2_abcd/sympy__sympy-21379_C_fcc8739d/official/report.json) |
| d_fix2_abcd | sympy__sympy-21379 | D / 1 | 是 | [记录](../evidence/records/d_fix2_abcd/sympy__sympy-21379_D_d53c8237/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0059) · [补丁](../evidence/records/d_fix2_abcd/sympy__sympy-21379_D_d53c8237/patch.diff) · [官方](../evidence/records/d_fix2_abcd/sympy__sympy-21379_D_d53c8237/official/report.json) |
| d_fix2_abcd | sympy__sympy-20438 | A / 2 | 是 | [记录](../evidence/records/d_fix2_abcd/sympy__sympy-20438_A_f83ce396/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0034) · [补丁](../evidence/records/d_fix2_abcd/sympy__sympy-20438_A_f83ce396/patch.diff) · [官方](../evidence/records/d_fix2_abcd/sympy__sympy-20438_A_f83ce396/official/report.json) |

## 历史材料范围说明

本整理版保留原报告的分析日期、审计结论与解释边界。原 PDF proposal、早期一次性分析脚本、重复归档包和其他探索实验报告没有重复放入本目录；它们不是本次通用工具运行的依赖。原始压缩包身份及 SHA-256 见 evidence/manifest.json。当前报告的完整指标应按配套完整证据包中的清单复算；精简版保留预计算汇总和小体积证据。

历史源码浏览和失败原因是人工/先前审计标注，并未因换成统一工具而变成自动推导的因果结论。本包不包含参考修复 hunk 或整套基准文件。源文件名是评价代理，不代表只有修改该文件才能修好。
