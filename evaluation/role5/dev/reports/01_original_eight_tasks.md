# 原始八题预实验：最初五题与新增三题的合并分析

> 精简提交版：报告结论与数值不变。完整轨迹、排名、D 事件和官方测试全文位于独立证据包；标为“归档文件”的链接提供包内路径与哈希。下载后复算方法见 [完整证据说明](../docs/FULL_EVIDENCE.md)。

本报告把最初五题和新增三题整理为一份开发阶段基线：8 道不同题、32 个入选的任务×条件组合，另有 12 次启动失败，合计 44 次执行。两批任务互不重叠，可以作八题描述性合并；它们仍分批执行，不能由此声称同一时间/完全相同核心源码的控制实验。

合并后 A/B/C/D 成功数为 **5/8、4/8、4/8、4/8**。B 在原五题的优势没有在新增三题延续；D 在两批中都与 C 的成功任务相同。因此结论应是“部分定位和可观测性改善尚未稳定转化为修复收益”，不能仅凭文件排名上升宣称整体更好。

## 本次可复算的八题总览

| 条件 | 官方成功/入选运行 | 调用数 | Total tokens | 费用 USD |
|---|---:|---:|---:|---:|
| A | 5/8 | 69 | 566,254 | 0.16136640 |
| B | 4/8 | 71 | 664,566 | 0.17789745 |
| C | 4/8 | 74 | 874,634 | 0.21077955 |
| D | 4/8 | 83 | 860,835 | 0.22628250 |

Token 已按每次响应重新求和，未沿用历史合并文件误取最后一次响应的值。每道题只有一次入选运行，没有独立重复来估计波动。以下保留两批的完整逐题分析，让读者看到同一机制何时有效、何时失效。

原始 D 缺少新版本的初始定位与反馈总耗时字段。旧局部 overhead 保留但不冒充新计时口径；也不把 C-D 总时间差直接称为 D 的模块开销。


> GitHub 整理版，2026-10-28。完整版整理时读取了 76 次执行记录，复算官方结果、逐次 usage、初始排名/候选与 D 投递；没有重新运行 Agent、模型或官方评测。正文中 2026-10-26/27 的源码核验、原压缩包完整性检查和轨迹解释保留为历史审计记录，不能理解为本次重新执行全部历史核验。
>
> 报告链接已改为相对路径。统一表位于 [results](../results/analysis.json)，所有执行身份与原始文件见 [证据索引](../evidence/INDEX.md)。旧文提到的 `analysis.json → exploration/events` 等路径对应 [历史标注](../evidence/annotations/README.md)，其文件结构与新工具输出不同。正文中的 S/E/R/H/N/O 等旧目录简称用于识别历史来源，当前可访问路径以证据索引为准。


---

## dev5_abcd_v1：评测结果与讨论 v1

2026-10-26｜DSA4213 Group 25｜Role 5 evaluation

本次补充：五题逐条件消耗、Hit@20 与“排名 → 查看 → 修复”指标；沿用本文件和原始实验记录，派生分析版本为 v1.1。

这批产物足以完成一版**开发实验评测报告**。20 个任务–方法组合均有可关联的官方 Harness 结果：A/B/C/D 分别修复 3/5、4/5、3/5、3/5。结构信息使部分目标文件排名上升，但没有带来一致的修复收益；D 在这五题中没有提高总体修复率，调用与 token 成本更高。以下结果用于检查流程、解释案例和调整后续实验，不能作为正式留出集结论。

### 数据来源、版本与计数口径

本报告按最新版 proposal 的 §5.1–5.5 排列，再补充 issue 定位提示分析及不足。依据是 Group25 proposal（历史引用，见文末材料范围说明） 与同目录 `main.tex`；旧的 `docs/proposal/DSA4213_proposal.pdf` 不作为本版要求。`evaluation_protocol.v0.1.md` 及中文版本用于解释协议，是否实际完成以产物为准。

为避免反复列出长路径，下面使用四个前缀：

| 前缀 | 实际位置 |
|---|---|
| S | `历史归档/server-dev5-download-20261025-01`，下载副本本身就是项目根目录 |
| E | `S/experiments/dev5_abcd_v1` |
| R | `E/runs/<run_id>`；全部 26 个 run_id 见 [运行汇总表](../results/run_summary.csv) |
| H | `S/logs/evaluation/<evaluation_run_id>/<run_id>/<task_id>`；每条对应关系见 [分析数据](../evidence/annotations/original_dev5.json) 的 `attempts` |

下载副本 HEAD 为 `1ba5fc82ce195a336ed69b58d3309cf9421beb04`，与原本地仓库的 `8503b2539b0dd0a7267b64b4422a1d413764f23e` 不同。本版只读取下载副本，输出全部在独立的 `role5-dev5-report-v1` 中；未合并、覆盖或修改原仓库及实验产物。

样本单位是 **5 个任务 × 4 个条件 = 20 个逻辑组合**。26 次执行中，6 次在 Docker 启动阶段超时，API 调用为 0；它们是 Django、Sphinx 的 A/B/C 首次尝试，其后的唯一完成尝试进入主分析。保留全部失败记录，不按修复结果挑选重试，也不把 26 次执行当作 26 个独立样本。20 条有效执行均为 `repeat_id=1`。

已完成的证据核对：20 组 `run_result`、Agent 最终补丁、`predictions`、原生 Harness 的 `patch.diff`、`report.json`、测试输出及运行日志均能关联；评测补丁与提交补丁逐字节一致，原生报告/日志与实验目录中的副本一致。pytest A 的 `-timing1` 补丁、报告与原评测相同，允许作为一次**单独的同补丁计时复跑**使用，但不能冒充原次评测耗时或 Agent 重复实验。

分析脚本记录了 444 份实际使用文件的 SHA-256，以及用于核对源码显示内容的固定 base-commit Git blob；写出统计前再次检查输入哈希。基准 parquet 自带校验值也一致。以上证明本报告依赖的证据可读且相互一致；没有服务器端全目录清单，仍不能证明整份下载与服务器完全镜像。

**本节依据：** `E/protocol.json`、`task_manifest.jsonl`、`run_plan.jsonl`、`execution_log.jsonl`；`R/run_result.json`、`prediction_metadata.json`、`predictions.jsonl`、`patch.diff`；`H/{patch.diff,report.json,test_output.txt,run_instance.log}`。派生结果：`analysis_v1.json → input_manifest / attempts`。

### 5.1 修复表现（Repair Performance）

“Agent 完成”表示提交了补丁；“修复成功”只取官方 `resolved`。本批 20 次 Agent 均完成、20 个补丁均成功应用、20 次官方评测均有结果，最终 13/20 修复成功，7/20 未修复；这 7 次不是缺评测。

下表中的测试数量来自数据集标签并与报告核对；它不是额外独立的任务数量。

| 任务 | A | B | C | D | FAIL_TO_PASS 数 | PASS_TO_PASS 数 |
|---|---|---|---|---|---:|---:|
| django__django-11133 | 成功 | 成功 | 成功 | 成功 | 1 | 64 |
| pytest-dev__pytest-7571 | 失败 | 成功 | 成功 | 成功 | 1 | 14 |
| sphinx-doc__sphinx-8595 | 成功 | 成功 | 成功 | 成功 | 1 | 0 |
| sympy__sympy-17630 | 失败 | 失败 | 失败 | 失败 | 2 | 19 |
| sympy__sympy-23262 | 成功 | 成功 | 失败 | 失败 | 1 | 61 |

| 指标 | A | B | C | D |
|---|---:|---:|---:|---:|
| 任务修复率 | 3/5，60% | 4/5，80% | 3/5，60% | 3/5，60% |
| 补丁应用率 | 5/5 | 5/5 | 5/5 | 5/5 |
| FAIL_TO_PASS 通过比例：合并测试计数 | 4/6 | 5/6 | 4/6 | 4/6 |
| FAIL_TO_PASS 通过比例：先逐题再平均 | 70% | 90% | 70% | 70% |
| PASS_TO_PASS 通过比例：合并测试计数 | 158/158 | 158/158 | 158/158 | 158/158 |

SymPy-17630 四组均只通过 1/2 个目标测试，因此即使部分测试通过，任务仍是失败。Sphinx-8595 的 PASS_TO_PASS 标签确实是空列表，逐题比例为 **N/A（0/0）**，不是 0%，也不是数据未下载；各条件 PASS_TO_PASS 的逐题平均只覆盖另外 4 题，均为 100%。这些测试没有观察到回归，不等于证明补丁在所有场景下正确。

proposal 的主要比较是 A–D：D 在 pytest-7571 获胜，在 SymPy-23262 落后，另外三题结果相同，净变化为 0/5。B 比 A 多修复一题，但五题单次结果不足以确立方法优劣。

**本节依据：** 每个 `H/report.json` 的 `resolved`、`patch_successfully_applied`、`tests_status`；`E/evaluation_dataset/swebench_verified_78f471bf_test.parquet` 的测试标签。派生结果：`condition_summary`、`paired_comparisons`，CSV 每行的 `f2p_* / p2p_*`。

### 5.2 定位表现（Localization Performance）

#### 评价目标及初始排名

proposal §5.2 已明确规定：用参考补丁修改的 Python 源文件作为离线定位评价目标，排除测试、文档和生成文件。这就是此前说的“定位真值”，更准确地说是**参考修复位置代理**；它不是 issue 自带的提示，也不是唯一正确修复位置。

所需 benchmark 已在下载副本中，无需重新下载。本版评价脚本只从参考 diff 的文件头派生路径并记录哈希，不导出修复 hunk，不读取 `test_patch` 或 `hints_text`，不向 Agent 或排名模块注入这些标签。五题各有 1 个符合规则的目标文件，排除任务数为 0。函数级分析未开展。

| 任务简写 | 参考文件代理 | B 初始名次 | C 初始名次 | D 初始名次 |
|---|---|---:|---:|---:|
| Django-11133 | `django/http/response.py` | 1 | 1 | 1 |
| pytest-7571 | `src/_pytest/logging.py` | 1 | 1 | 1 |
| Sphinx-8595 | `sphinx/ext/autodoc/__init__.py` | 12 | 11 | 11 |
| SymPy-17630 | `sympy/matrices/expressions/matexpr.py` | 52 | 18 | 18 |
| SymPy-23262 | `sympy/utilities/lambdify.py` | 35 | 19 | 19 |

| 指标，按 5 题平均 | A | B | C | D 初始 |
|---|---:|---:|---:|---:|
| File Hit@1 | N/A | 40% | 40% | 40% |
| File Hit@5 | N/A | 40% | 40% | 40% |
| File Recall@5 | N/A | 40% | 40% | 40% |
| MRR | N/A | 0.4262 | 0.4398 | 0.4398 |
| File Hit@20：实际注入的 Top-20 含目标文件 | N/A | 3/5，60% | 5/5，100% | 5/5，100% |

A 没有显式列表，定位排名指标不适用。这里的 MRR 来自完整保存的算法输出，不是仅对 Top-20 计算；Hit@5/Recall@5 相同是因为本批每题仅有一个目标文件。评分保留原始排名中的测试文件位置，不为提高名次而事后删除候选。

C 将两个 SymPy 目标从 Top-20 外移入上下文，因此 MRR 和 Top-20 覆盖改善，而 Hit@5 不变。但 SymPy-17630 仍全部失败，SymPy-23262 的 C/D 反而失败。**排名提高、源码被查看、修复正确是三个不同环节**，需要结合轨迹解释，不能用任何一个替代另一个。

#### 与 Top-20 注入深度一致的三环节指标

**Hit@20** 定义为：至少一个参考目标文件出现在实际注入的初始 Top-20 候选中。本版同时核对保存排名、`prompt_candidates.json`、`effective_task.txt` 和初始模型上下文。这里进入上下文的是**目标文件的路径与排名信息**，不代表源码正文已经被读取。D 使用初始列表评分，运行中更新仍在下节另行分析。

**进入上下文后是否查看**定义为：初始提示送达后，是否有同一个已注入目标文件的源码内容通过工具输出进入模型上下文。沿用 §5.3 的查看口径，搜索源码片段、文件正文、traceback 源码行或 diff 都可计入；仅列文件名不计入，原 issue 自带的源码片段也不算“注入后的查看”。没有注入目标文件的运行，其条件查看率不适用；存在无法判断的读取时保留未知。本批该指标没有未决记录。

| 环节 / 分母 | A | B | C | D |
|---|---:|---:|---:|---:|
| 初始排名 Hit@20 / 全部 5 题 | N/A | 3/5 | 5/5 | 5/5 |
| 已注入目标的任务中，实际查看该目标 / 命中 Top-20 的任务 | N/A | 3/3，100% | 4/5，80% | 4/5，80% |
| 已注入且已查看目标的任务中，官方修复成功 / 同时满足前两环节的任务 | N/A | 3/3，100% | 3/4，75% | 3/4，75% |
| 不论是否注入，实际查看目标 / 全部 5 题 | 5/5 | 5/5 | 4/5 | 4/5 |
| 官方修复成功 / 全部 5 题 | 3/5 | 4/5 | 3/5 | 3/5 |

另以更严格的“实际执行文件读取命令，且可见输出匹配该文件源码”核对：已注入目标后的**直接打开率**同样为 B 3/3、C 4/5、D 4/5。因此本批的查看率结果不依赖于把搜索片段计为打开；两种口径的逐次证据都保存在 JSON/CSV 中。

下表每格按“**Top-20 是否命中 → 后续是否查看目标源码 → 官方是否修复**”排列。第二环节对所有运行都展示，因此能够保留未命中却自行找到目标的情况；“未见”表示没有观察到目标源码被查看。

| 任务 | A | B | C | D |
|---|---|---|---|---|
| Django-11133 | N/A → 已看 → 成功 | 命中 → 已看 → 成功 | 命中 → 已看 → 成功 | 命中 → 已看 → 成功 |
| pytest-7571 | N/A → 已看 → 失败 | 命中 → 已看 → 成功 | 命中 → 已看 → 成功 | 命中 → 已看 → 成功 |
| Sphinx-8595 | N/A → 已看 → 成功 | 命中 → 已看 → 成功 | 命中 → 已看 → 成功 | 命中 → 已看 → 成功 |
| SymPy-17630 | N/A → 已看 → 失败 | 未中 → 已看 → 失败 | 命中 → 未见 → 失败 | 命中 → 未见 → 失败 |
| SymPy-23262 | N/A → 已看 → 成功 | 未中 → 已看 → 成功 | 命中 → 已看 → 失败 | 命中 → 已看 → 失败 |

这把两个不同问题区分开了：C/D 的 SymPy-17630 停在“候选已注入，但未观察到目标源码被查看”；SymPy-23262 则是“目标已经查看，仍未修复”。B 在两道未命中 Top-20 的题上都自行看到了目标，其中一道修复成功。条件比例的分母随环节变化，且只描述本批轨迹，不能据此推断排名或查看动作造成了修复成功。

#### D：首次可用失败前后

| D 任务 | 观察到的失败 / 实际更新次数 | 首次可用失败前后目标名次 | 下一次模型调用前已送达 | ΔRR |
|---|---:|---|---:|---:|
| Django-11133 | 1 / 1 | 1 → 1 | 第 3 次 | 0 |
| SymPy-17630 | 5 / 3 | 18 → 18 | 第 2 次 | 0 |
| 其他三题 | 各 0 / 0 | N/A，无可用事件 | N/A | N/A |

首次可用失败覆盖率为 **2/5**；在这两题中，Hit@1、Hit@5、Recall@5 和 RR 都未改善。Django 的 Top-20 顺序确实改变，但目标文件本来已第一；其失败是未配置 Django settings 引发的异常，不能把“反馈可解析”视为“已定位根因”。SymPy-17630 首次反馈连 Top-20 都未改变；后续虽有其他候选上升，目标文件仍为第 18。该题另外两次失败因更新上限而未再注入。

目前候选产物的 `symbol`、`symbol_type` 为空，没有可评分的函数排名；仅从文件名推测函数会改变指标定义。因此函数 Hit@5 为**未具备评价条件**，不能记 0。后续需先明确方法如何输出函数候选，再在评价侧做固定 base commit 的 AST 映射与覆盖率核验。

**本节依据：** 上述 parquet；`S/experiments/{bm25_results,structural_results,condition_c_results}.json`；`R/localization_candidates.json`、`prompt_candidates.json`、`effective_task.txt`、`trajectory.json`；D 的 `failure_feedback/{initial_rankings.json,failure_updates.jsonl,feedback_summary.json}`。派生结果：`gold_locations`、`attempts[].localization / context_funnel / d_feedback`，以及 `condition_summary.*.context_funnel`；CSV 增加 `hit20`、`target_viewed`、`injected_target_viewed` 和两项 `*_directly_opened` 字段。

### 5.3 探索效率（Exploration Efficiency）

#### 实际查看源码与首次触及位置

提取器依据**实际送给模型的工具输出**计数，不依据“打算读哪个文件”计数。文件正文、包含源码的搜索结果、traceback 源码行及 Agent diff 可计入；只列文件名、只在排名中出现、未执行的提交动作不计入。被截断后没有送给模型的 `raw_output` 不计入。测试/文档等使用与源文件口径一致的排除规则，路径去重。

源码搜索片段很短也可能计为一次“看到内容”，这不证明 Agent 已理解该文件。原 issue 已提供的 traceback 源码行记为步骤 0，并记录独立来源；SymPy-17630 的两个此类文件也计入内容暴露数。所有来源、可见片段和消息下标保留在 JSON 中，方便复核。

下表每格为“**不同源码文件数 / 首次看到参考文件之前的模型调用数**”。例如 `1 / 2` 表示第 3 次模型调用执行的命令首次返回目标源码，之前已有 2 次模型调用；`/ 0` 通常表示第 1 次调用就看到。格式错误但已发生的 API 调用也计入步骤。

| 任务 | A | B | C | D |
|---|---:|---:|---:|---:|
| Django-11133 | 15 / 0 | 6 / 0 | 12 / 0 | 15 / 0 |
| pytest-7571 | 1 / 2 | 1 / 0 | 1 / 0 | 1 / 0 |
| Sphinx-8595 | 2 / 0 | 2 / 0 | 1 / 0 | 2 / 0 |
| SymPy-17630 | 10 / 0 | 7 / 3 | 2 / 未观察到 | 2 / 未观察到 |
| SymPy-23262 | 15 / 4 | 17 / 5 | 12 / 0 | 23 / 0 |
| 平均源码文件数 | 8.6 | 6.6 | 5.6 | 8.6 |
| 观察到参考源码的任务数 | 5/5 | 5/5 | 4/5 | 4/5 |

C/D 在四个触及目标的任务中都于第 1 次调用看到目标，但另有一题未观察到；不能只比较成功触及者的均值就宣称全面更快。未触及任务没有填入虚构步骤数。当前已识别的直接读取候选没有未决条目，但提取器不是通用 shell 语义解释器，仍存在未覆盖形式；跨任务使用前需检查新形式。

#### 调用、token 与费用

以下均为每个条件的 5 条有效执行之和，缓存输入 token 是输入的子集，不能再次加进总 token。

| 条件 | API 调用 | 输入 token | 其中缓存输入 | 输出 token | 总 token | API 返回费用，美元 |
|---|---:|---:|---:|---:|---:|---:|
| A | 39 | 279,204 | 226,688 | 6,831 | 286,035 | 0.087128 |
| B | 47 | 423,488 | 362,112 | 8,648 | 432,136 | 0.112106 |
| C | 35 | 275,343 | 222,080 | 6,862 | 282,205 | 0.087482 |
| D | 55 | 627,155 | 555,136 | 12,283 | 639,438 | 0.150923 |

下面展开为**每题、每个条件的一次有效执行**，与上表使用同一批 20 条记录。总 token = 输入 + 输出；费用保留 8 位小数，便于核对小额差异。

| 任务 | 条件 | API 调用 | 输入 token | 其中缓存输入 | 输出 token | 总 token | 费用，美元 |
|---|---|---:|---:|---:|---:|---:|---:|
| Django-11133 | A | 6 | 31,335 | 23,040 | 897 | 32,232 | 0.01198575 |
| Django-11133 | B | 11 | 91,107 | 79,360 | 1,822 | 92,929 | 0.02296125 |
| Django-11133 | C | 6 | 42,966 | 33,024 | 1,261 | 44,227 | 0.01560780 |
| Django-11133 | D | 7 | 54,926 | 43,648 | 1,595 | 56,521 | 0.01890960 |
| pytest-7571 | A | 7 | 25,550 | 18,560 | 928 | 26,478 | 0.01081050 |
| pytest-7571 | B | 7 | 49,376 | 39,552 | 1,238 | 50,614 | 0.01590540 |
| pytest-7571 | C | 7 | 51,371 | 41,216 | 1,125 | 52,496 | 0.01576995 |
| pytest-7571 | D | 7 | 47,611 | 37,760 | 1,131 | 48,742 | 0.01530975 |
| Sphinx-8595 | A | 6 | 20,344 | 14,976 | 1,002 | 21,346 | 0.00965820 |
| Sphinx-8595 | B | 6 | 32,450 | 24,704 | 1,082 | 33,532 | 0.01253130 |
| Sphinx-8595 | C | 5 | 24,424 | 17,408 | 827 | 25,251 | 0.01028910 |
| Sphinx-8595 | D | 8 | 56,505 | 46,976 | 1,240 | 57,745 | 0.01624995 |
| SymPy-17630 | A | 7 | 58,771 | 46,208 | 1,738 | 60,509 | 0.02070885 |
| SymPy-17630 | B | 10 | 89,942 | 76,032 | 1,847 | 91,789 | 0.02444640 |
| SymPy-17630 | C | 8 | 63,045 | 51,712 | 2,222 | 65,267 | 0.02237715 |
| SymPy-17630 | D | 13 | 143,311 | 125,440 | 4,481 | 147,792 | 0.04297575 |
| SymPy-23262 | A | 13 | 143,204 | 123,904 | 2,266 | 145,470 | 0.03396480 |
| SymPy-23262 | B | 13 | 160,613 | 142,464 | 2,659 | 163,272 | 0.03626205 |
| SymPy-23262 | C | 9 | 93,537 | 78,720 | 1,427 | 94,964 | 0.02343825 |
| SymPy-23262 | D | 20 | 324,802 | 301,312 | 3,836 | 328,638 | 0.05747790 |

共 176 次调用、1,639,814 tokens，费用合计约 $0.437640，均逐调用与 provider response 核对。这些是 API 返回的费用字段，未与最终账单核销。6 次启动失败未调用模型，API 成本为 0，但仍消耗约 721.82 秒启动等待，另列为基础设施损耗。有效执行的已执行 shell 命令数 A/B/C/D 为 45/51/39/67；被 runner 拦截而未执行的最终提交命令没有计入。

D 比 A 多用 353,403 tokens、约 $0.063795，修复数相同。D 比 C 也没有新增修复，但不能把全部费用差直接归给反馈消息：两组轨迹、命令数和查看文件都发生变化，需要独立重复或受控消融才能分离原因。

#### 时间及 B/C 预计算缺口

| 每题平均，秒 | A | B | C | D |
|---|---:|---:|---:|---:|
| 已记录 runner/Agent wall time | 33.244 | 21.378 | 16.295 | 61.622 |
| 已记录 Harness wall time | 22.774* | 22.604 | 22.660 | 22.674 |
| runner 内索引获取计时 | 0.403 | 0.399 | 0.395 | 0.410 |
| B/C 历史排名预计算耗时 | N/A | 未知 | 未知 | 不能由同类字段直接给出 |

\* A 中 pytest 使用已核验的同补丁 `-timing1` 复跑 21.94 秒，原次评测耗时未知。

逐题时间如下，单位均为秒。索引获取和 D 部分定位开销已经包含在 runner wall time 内，不能再加一次；A/B/C 不使用 D 反馈计数器，其该列为 N/A，不能据此说 B/C 排名开销为零。

| 任务 | 条件 | runner/Agent wall | Harness wall | runner 内索引获取 | D 部分定位开销 |
|---|---|---:|---:|---:|---:|
| Django-11133 | A | 13.490 | 24.340 | 0.393 | N/A |
| Django-11133 | B | 23.696 | 23.860 | 0.398 | N/A |
| Django-11133 | C | 14.287 | 23.980 | 0.394 | N/A |
| Django-11133 | D | 90.881 | 24.200 | 0.388 | 9.974 |
| pytest-7571 | A | 13.800 | 21.940* | 0.063 | N/A |
| pytest-7571 | B | 12.831 | 21.990 | 0.065 | N/A |
| pytest-7571 | C | 11.966 | 21.880 | 0.061 | N/A |
| pytest-7571 | D | 14.065 | 21.780 | 0.078 | 1.099 |
| Sphinx-8595 | A | 12.844 | 21.740 | 0.097 | N/A |
| Sphinx-8595 | B | 13.137 | 21.380 | 0.083 | N/A |
| Sphinx-8595 | C | 9.745 | 21.530 | 0.082 | N/A |
| Sphinx-8595 | D | 36.401 | 21.660 | 0.088 | 1.676 |
| SymPy-17630 | A | 21.897 | 22.160 | 0.677 | N/A |
| SymPy-17630 | B | 24.312 | 22.090 | 0.672 | N/A |
| SymPy-17630 | C | 25.626 | 21.950 | 0.669 | N/A |
| SymPy-17630 | D | 92.032 | 21.880 | 0.685 | 47.262 |
| SymPy-23262 | A | 104.189 | 23.690 | 0.786 | N/A |
| SymPy-23262 | B | 32.912 | 23.700 | 0.777 | N/A |
| SymPy-23262 | C | 19.854 | 23.960 | 0.766 | N/A |
| SymPy-23262 | D | 74.730 | 23.850 | 0.812 | 24.460 |

\* 同上，pytest A 为同补丁的单独 Harness 计时复跑。五题的 B、C 历史预计算耗时均未知；本表没有用零代填，也没有将这些时间拼成完整方法总耗时。

再次检查 `experiments/` 排名产物、`logs/` 中的文件、各 `timings.json` 以及三个批量排名脚本，**没有找到 B/C 预计算耗时**；20 条有效执行的 `ranking_seconds` 均为 null。批量生成 B/C 排名在 runner 计时范围外。`indexing_seconds` 只测 runner 内获取索引元数据的操作，不能当作最初建索引的总耗时。

runner wall time 包括其内部的加载、环境设置、Agent 执行和清理；D 的初始化及运行时反馈也在其中。D 自带 `localization_overhead_seconds` 只覆盖初始化和部分失败快照/映射，不含 `query()` 中所有融合与注入处理，因此也不是完整排名成本。索引/反馈计时与 wall time 重叠，不能直接相加。C 的已记录 wall time 较短，但**完整方法总耗时无法由当前记录公平比较**。

协议记录 Agent 批处理 `parallelism=1`；这不能证明此前 B/C 预计算是否并行。文件修改时间和下载时间不能补出历史运行时长。后续若找不到服务器原始计时，可在固定硬件、相同 base commit 上单独补做“不调用 LLM 的定位微基准”，分别测首次建索引、缓存复用、BM25、结构排名、RRF 和 D 反馈；标为后来补测，不能伪装成本次历史耗时。并行任务应报告实际端到端墙钟时间，并另外报告各步骤耗时；共享索引成本应同时列一次性成本和明确的摊销口径。

**本节依据：** `R/{trajectory.json,usage.jsonl,timings.json,run_result.json}`；`R/evaluation/harness_wall_seconds.txt`；`src/agent/{swebench_runner,failure_feedback}.py`；`scripts/{run_bm25_batch,run_structural,run_rrf,run_experiment_batch}.py`。派生结果：`attempts[].exploration`（含逐事件证据）、`condition_summary`、`overhead_audit`。

### 5.4 轨迹与失败分析（Agent-Trajectory Analysis）

分类遵循 proposal 的五类框架，使用固定规则加逐例证据复核，不训练分类模型。先判断基础设施/评测状态，再检查回归与源码触及，最后结合 Agent 补丁和可见验证输出解释。每条失败保留一个主类，可附次要因素；未知不能靠猜测填满。此版为 Codex 的首轮编码，尚未由第二位组员独立复核。

| 类别 | 本版操作定义 | 有效执行中的主类数量 | 对应案例 |
|---|---|---:|---|
| F1 未观察到参考文件源码 | 以参考文件代理和可见输出判断，不能断言未读任何相关代码 | 2 | SymPy-17630 C、D |
| F2 已查看相关代码，但诊断/修复路径不正确 | 需具体行为和补丁证据，不能仅因未修复就归此类 | 3 | pytest-7571 A；SymPy-23262 C、D |
| F3 补丁缺失、无效或不完整 | 本批均是可应用但目标测试仅部分通过 | 2 | SymPy-17630 A、B |
| F4 回归或验证不足 | 本批没有 P2P 回归；验证不足可作为次要因素 | 0 主类 | SymPy-23262 C/D 等需注意验证不足 |
| F5 环境/资源失败 | 与修复质量分开记账 | 0 主类；另有 6 次启动失败 | Django、Sphinx A/B/C 首次尝试 |

**案例一：目标文件读对了，仍可能修错。** pytest A 第 3 次模型调用已查看 `src/_pytest/logging.py`。最终补丁将 handler 的旧级别放入按 logger 名称索引的字典；已读源码的恢复逻辑遍历该字典并调用 `logging.getLogger`，不能据此证明 handler 自身被恢复。Agent 自建测试显示 `2 passed`，官方 F2P 为 0/1。故主类为 F2，验证针对性不足是伴随问题。证据：`pytest-dev__pytest-7571_A_b2fdd0bd/trajectory.json` 的 `messages[7,9,11,13]`、该 run 的补丁及官方报告。

**案例二：目标进入候选列表，仍可能没有进入实际源码上下文。** SymPy-17630 的目标 `matexpr.py` 从 B 的第 52 提升到 C/D 的第 18，确实在 Top-20 中；但 C/D 可见的源码集中于 `blockmatrix.py` 和 `strategies/core.py`，未观察到目标源码。D 三次更新也没有改善目标名次。四组官方 F2P 都是 1/2；A/B 虽看到参考文件，仍只完成部分行为修复。F1 在这里是位置代理下的描述，不能排除另一种正确修复本来就只需修改其他文件。证据：四组 `localization_candidates.json`、`trajectory.json`、D `failure_updates.jsonl` 与报告；逐条源码事件见 `exploration.events`。

**案例三：错误行为已经打印出来，却没有变成失败信号。** SymPy-23262 C/D 第 1 次调用已看到 `lambdify.py`，最终却只提交 `sympy/printing/pycode.py` 修改。C 的 `messages[14]`、D 的 `[15,23,37,43]` 都仍显示单元素输出 `return (1)`，而 issue 要求保留元组语义；这些命令返回码为 0。D 本题没有触发反馈更新，说明“能成功运行并打印输出”不能代表行为正确。F2 是对修复路径的解释，验证不足为次要因素。后续可让 Agent 把 issue 的预期转为可失败的断言，但必须在新开发版本验证，不能追改本批轨迹。

**成功对照：Top-5 未命中也能修好。** Sphinx C 的参考文件排第 11，首次模型调用的搜索已返回该文件源码，随后官方修复成功（`messages[3]` 为首次源码证据）。这说明 Top-5 只是有限深度定位指标，Agent 仍可使用 Top-20 或自行搜索；不应把 Hit@5=0 写成“定位完全失败”。

**本节依据：** 上述精确 run 的 `trajectory.json`、Agent `patch.diff`、D 反馈记录及 `H/report.json`；不使用参考补丁内容解释失败。派生结果：`attempts[].failure`、`classification`；分类规则在 `analyze.py → classify_failure`，消息下标均为 JSON 的零基下标。

### 5.5 变异性与实验协议（Variability and Experimental Protocol）

本批使用 SWE-bench Verified，数据 revision 为 `78f471bf655a3137b2e8a75af1501690ec009ec3`，原生 split 为 `test`，但小组实验分区明确为 **development**，`formal_heldout=false`。模型是经 OpenRouter 调用的 `openai/gpt-5.4-mini`，mini-SWE-agent 为 2.4.6；不能混入个人 MiMo 试跑。

已核对各题的 base commit、原始 issue、保存排名与实际注入上下文。A 使用原 issue，B 增加 BM25，C 增加 BM25+结构 RRF，D 从相同的 C 初始路径/次序/分数出发再接运行时反馈。Top-k=20、RRF k=60，D 最多更新 3 次。相同基础 system template 的哈希已记录；C/D 的解释文字分别含 `RRF` 和 `RRF(L,S)`，并非每个字节完全相同的附加提示。

实际预算是每次最多 250 steps、$3，单命令超时 60 秒；总 token 与 Agent 总 wall-time 上限没有强制执行。温度、top-p、随机种子未显式留档，不能仅凭“同模型”证明所有解码条件已冻结。下载环境含 `swebench-5.0.2.dist-info`，但这只能证明下载目录中存在该版本包，不能替代原评测环境的 commit、本地修改状态和镜像 digest 记录。

配对分析以同题比较，结果已保存；不对五题作显著性或稳定性声明。本批没有独立 Agent 重复实验，6 次启动重试及 pytest A 的 Harness 计时复跑均不构成重复实验。重复稳定性属于后续正式阶段，本轮不追加。

**本节依据：** `E/protocol.json`、`task_manifest.jsonl`、`R/{task_metadata.json,run_result.json,effective_task.txt,trajectory.json}`；下载目录中的 Harness 包元数据。派生结果：`protocol`、`attempts[].configuration`、`paired_comparisons`。

### 补充讨论：issue 本身的定位信息与额外排名有什么差别？

这五题的定位线索主要嵌在 `problem_statement` 文本里，没有单独的“标准答案路径”字段。`task_manifest.jsonl` 的 `has_localization_hint` 是小组的标签，不是定位答案。下面直接展示原始字段中的片段，并与实际 `prompt_candidates.json` / `effective_task.txt` 比较。

| 任务 | `problem_statement` 中实际出现的内容 | 提示强度及边界 | B/C/D 额外提供的导航信息 |
|---|---|---|---|
| Django-11133 | `from django.http import HttpResponse`；`memoryview` | API、模块、输入类型；没有 `response.py` 的明确路径或行号 | 三组均将 `django/http/response.py` 排第 1，并附分数和其余候选 |
| pytest-7571 | `caplog.set_level(42)`；`caplog.handler.level` | fixture、方法、状态属性；没有 `src/_pytest/logging.py` 路径 | 三组均将该实现文件排第 1 |
| Sphinx-8595 | `sphinx.ext.autodoc`；`__all__ = []` | 模块和触发条件；issue 的 `example.py` 是复现样例，不是 Sphinx 仓库实现文件 | 具体实现路径 `sphinx/ext/autodoc/__init__.py` 位于 B 第 12、C/D 第 11 |
| SymPy-17630 | traceback 的 `sympy/matrices/expressions/blockmatrix.py`、`sympy/strategies/core.py`；`line 80, in colblocksizes` | 具体文件、函数、历史行号与源码行；异常位置未必是修复位置 | C/D 的 Top-20 还包含第 18 的 `matexpr.py`，它未作为路径出现在上述 traceback 中；B 第 52 不会注入 |
| SymPy-23262 | `from sympy import lambdify`；`Python code printer`；预期 `return (1,)` | API、功能和预期行为；`_lambdifygenerated` 是动态函数，不能当作仓库路径 | `sympy/utilities/lambdify.py` 在 B 第 35，未注入；C/D 第 19，已注入 |

以 pytest C 为具体例子，原问题只有方法/属性线索，而实际附加消息包含：

```text
1. src/_pytest/logging.py | score: 0.0328 | reason: RRF
2. testing/logging/test_fixture.py | score: 0.0323 | reason: RRF
3. src/_pytest/fixtures.py | score: 0.0317 | reason: RRF
```

对应 `prompt_candidates.json` 的字段是 `file / rank / score / reason`，其 `symbol / symbol_type` 为 null。它提供的是基于当前仓库的候选路径和优先级，不是源码正文，也没有参考修复答案。A 同样保留完整原 issue，所以当前对照应解释为：**在 issue 已有线索之上，额外的自动排名是否有帮助。** 不能把 A 称为“无定位信息”。

后续选题建议保留公开 issue 原文，在查看结果前固定分层规则：H0 无明显定位线索；H1 只有 API/模块/行为线索；H2 有明确路径、函数定位或 traceback/行号。当前可暂标 H1 四题、H2 一题、H0 零题；这是本版分析标签，需要组员复核后冻结，不能当作 benchmark 官方标签。

正式评测同时报告全样本及各层内的同题 A–D 比较，避免因已知结果而删题。若资源不足，至少分别覆盖“有提示/无提示”，并保留提示类型和强度。去掉 issue 原有提示会改变任务，应另立消融实验；当前五题无法回答方法对“无提示任务”是否更有效。参考修复位置只用于事后评分，不参与提示分层或选题。

**本节依据：** `E/task_statements/<task_id>.txt`、`task_manifest.jsonl`；`R/task_metadata.json` 的 `problem_statement`，以及 `prompt_candidates.json`、`effective_task.txt`、实际 `trajectory.json` 初始用户消息；`S/docs/benchmark/candidate_pool_CN.v0.1.md`。派生结果：`issue_hints`、`attempts[].prompt_top20`。

### 6. 不足、解释边界与下一步

| 缺口 | 当前处理 | 后续最小方案 |
|---|---|---|
| B/C 排名、首次索引构建历史耗时 | 未知；不作完整方法速度优劣结论 | 先向组员索取原始命令/计时日志；没有则另做定位微基准，明确后来补测及冷/热缓存条件 |
| 函数级定位 | 不具备评分条件 | 先定义并保存函数候选；评价侧再做原始 AST 映射，报告可评分覆盖率，不必重跑当前 Harness |
| 失败分类和源码查看边界 | 已有可复现提取规则、事件证据和首轮分类 | 请第二位组员复核 7 次失败及关键首次查看事件；有分歧就保留或调整，不包装成自动确定的根因 |
| 运行环境完整复现 | 可核对已有结果，但缺实际 Harness 源码状态、完整启动命令、不可变镜像身份等 | 向组员补一段环境说明即可；这些主要影响复现可信度，不要求重跑来“凑材料” |
| 解码参数和完整预算 | 已记录值与未执行上限分别说明 | 正式阶段显式冻结模型参数及预算；本批保持历史事实 |
| 下载完整性 | 核心分析依赖已核对，缺服务器总清单 | 需要时请组员给文件清单/哈希；现阶段不影响上述已验证的 20 组结果分析 |
| 样本小、全都有某种 issue 提示 | 仅开发集描述，不作稳定性和泛化结论 | 后续固定提示分层、仓库覆盖与留出集；重复实验留在正式阶段 |

另有一个实现层面的记录问题：20 个保存补丁均经过 `.strip()`，末尾换行与 trajectory submission 不完全相同，但保存补丁、prediction 和实际 Harness 补丁一致，且均成功应用。未来可以改进补丁保存和应用检查，**本轮不修写任何历史补丁或组员实现**。

本版可用于汇报的结论是：开发实验的官方结果链条已能闭合，文件级定位、成本和轨迹分析已补齐；结构排名在部分任务中提高目标可见性，但收益未稳定转化为修复成功，D 的有效反馈覆盖及行为验证仍需改进。完整时间比较、函数指标与正式泛化结论仍待后续材料或实验支持。

**复核入口：** 本目录 [README](../tools/offline_eval/README.md) 解释全部 6 个文件及复算方法；机器结果集中在一份 JSON 和一份 CSV，不另建每题报告。全部缺失数值保持 null/空白或明确写“未知”；N/A 只用于不适用情形。

---

## 新增三题评测与讨论：dev3_extra_abcd_v1

2026-10-26｜DSA4213 Group 25｜Role 5｜独立离线分析 v1

### 先看结论

**已有证据支持：** 新三题 A/B/C/D 分别修复 **2/3、0/3、1/3、1/3**；12 份补丁全部应用成功。D 相比 A 少修复 Django-12262，与 C 在三题上的修复结果完全相同。D 只有 Django-12262 产生一次可用失败并完成更新；目标文件排名仍为第 1，更新后仍未修复。两个 SymPy 的 D 运行虽然输出过异常文字，但相应命令返回码为 0，反馈记录均为零次。

**仅限本轮三题的观察：** 结构排名提高了部分目标名次，但未提高 Top-20 任务覆盖率。SymPy-21379 的目标在 C/D 第 285 位，A/C/D 仍能自行找到并修复；D 的成功不能归因于未发生的反馈重排。SymPy-20438 中，D 没有查看已经注入的第 1 名目标源码，延续了旧五题“进入上下文不保证被查看”的现象。

**尚不能确定：** 不能由这三题断言定位提示导致失败、D 一般无效，或 C/D 时间差就是反馈模块成本。每组只有一次有效执行，选题偏向检验 D 的假设；新旧批次代码准备提交也不同，新增材料没有完整 src 源码。

组员的 8 题合并汇总存在 token 聚合错误：32 组都取了最后一次调用的 token。本报告已从原始 usage.jsonl 重新求和，并与 run_result 和新三题的逐次模型响应核对。费用、调用次数、修复结果、Agent 时间、Harness 时间分别核查，32 组这些汇总字段均一致，未随 token 错误一概否定。

### 来源、版本与计数口径

沿用旧报告对应的 Group25 proposal §5.1–5.5 与文件级评分口径。原始材料没有被修改，也没有执行交接包里的脚本。安全解压位置及前缀如下：

| 前缀 | 实际位置 |
|---|---|
| N | `历史归档/server-dev8-download-20261026-01/extracted-dev8-handoff-01` |
| E | `N/experiments/dev3_extra_abcd_v1` |
| R | `E/runs/<run_id>` |
| O | `历史归档/server-dev5-download-20261025-01` |
| H | `R/evaluation`；本包没有独立的原生 logs/evaluation 目录 |

压缩包 SHA256 为 `77655dfce2b88c329963de3342a21dc5fa57bac17277f1723698b5d0f2b64517`。18 条尝试中只有 12 个独立的任务×条件组合；另 6 条为 Docker 启动超时、API 调用为 0 的尝试。每个计划组合只有一个完成尝试，按尝试历史选取，不按修复结果择优。所有有效运行 repeat_id=1。

12 组 Agent patch、predictions、轨迹提交内容及 prediction_metadata 哈希一致；提交补丁全文能在对应 Harness 日志中找到，任务和 run_id 也相符。12 份官方报告的 FAIL_TO_PASS / PASS_TO_PASS 测试名称集合与本地 benchmark 标签一致。日志均包含早期 git apply 失败和随后补丁应用过程，不能仅凭前面的失败字样认定最终应用失败；最终应用状态取官方报告。**本包没有独立的原生评测 patch.diff，故本轮核验到日志里的补丁内容，不能称为再次核对了缺失文件的哈希。**

| 控制项 | 核验结果 |
|---|---|
| 模型 / 服务 / mini-SWE-agent | openai/gpt-5.4-mini / openrouter / 2.4.6 |
| 数据集 | SWE-bench Verified；revision `78f471bf655a3137b2e8a75af1501690ec009ec3`；原生 split=test |
| 小组实验分区 | development，不是 held-out |
| 新 / 旧准备提交 | `8686189ddd2a2e5560d097397f80a38c1a7a73d9` / `1ba5fc82ce195a336ed69b58d3309cf9421beb04` |
| 排名与更新 | Top-20；RRF k=60；结构种子 10；D 最多 3 次更新 |
| 预算 | 250 步、3 USD；命令超时 60 秒；总 token 和 Agent wall-time 上限未执行 |
| 解码 | 记录了 drop_params=true、parallel_tool_calls=true；未显式记录 temperature、top_p、seed 等，实际服务端默认值未知 |
| 代码可比性 | 包内与旧副本同名的 12 个 scripts 文件哈希一致；另有两个新脚本。完整 src 缺失，本地两个 Git 库也没有新提交对象，不能确认核心实现完全一致 |
| 系统提示 | 新12组与旧有效运行记录的 system_template SHA256 相同 |

**本节来源：** `E/{protocol.json,task_manifest.jsonl,run_plan.jsonl,execution_log.jsonl}`，`R/{run_result.json,trajectory.json,prediction_metadata.json,predictions.jsonl,patch.diff}`，`H/{report.json,run_instance.log}`，`N/scripts/`。全部运行 ID 及 18 行记录见 [run_summary.csv](../results/run_summary.csv)；核验清单见 [analysis.json](../evidence/annotations/original_dev3.json)。

### 5.1 修复表现

下表每格为“**是否修复；F2P 通过数/总数；P2P 通过数/总数**”。FAIL_TO_PASS（F2P）是本应被修复的测试，PASS_TO_PASS（P2P）是应保持通过的测试。每个 A/B/C/D 都有自己的一次官方评测，不把四组混在一起计算单组比例。

| 任务 | A | B | C | D |
|---|---|---|---|---|
| Django-12262 | 成功；4/4；18/18 | 失败；1/4；18/18 | 失败；2/4；18/18 | 失败；2/4；18/18 |
| SymPy-20438 | 失败；0/2；92/93 | 失败；0/2；93/93 | 失败；0/2；93/93 | 失败；0/2；93/93 |
| SymPy-21379 | 成功；1/1；91/91 | 失败；0/1；91/91 | 成功；1/1；91/91 | 成功；1/1；91/91 |

所有条件的补丁应用率都是 3/3。以下合并测试比例是在**各自条件内部**加总三题，供描述测试覆盖；任务修复率仍以 3 题为分母。

| 指标 | A | B | C | D |
|---|---:|---:|---:|---:|
| 修复率 | 2/3，66.7% | 0/3，0% | 1/3，33.3% | 1/3，33.3% |
| F2P 合并测试比例 | 5/7 | 1/7 | 3/7 | 3/7 |
| F2P 逐题比例平均 | 66.7% | 8.3% | 50.0% | 50.0% |
| P2P 合并测试比例 | 201/202 | 202/202 | 202/202 | 202/202 |

主要比较 A–D：D 没有新增修复，Django-12262 从 A 成功变为 D 失败，其余两题相同。拆分比较：A→B 少修复 Django-12262 和 SymPy-21379；B→C 多修复 SymPy-21379；C→D 三题修复结果均不变。这是配对结果描述，单次随机轨迹不能单独证明某模块造成了增益或损失。

**本节来源：** 各 `H/report.json` 的 resolved、patch_successfully_applied、tests_status；本地 benchmark 的 F2P/P2P 标签。JSON 中 `condition_summary`、`paired_comparisons` 可复核。

### 5.2 定位表现

#### 评价目标与初始排名

沿用 proposal 与旧版方法：在评价侧从参考修复 diff 文件头提取原有 Python 源文件，排除测试、文档、生成文件和新建文件。这里只输出路径及哈希，不展示修复内容、不读取 test_patch 或 hints_text，也不向 Agent 注入评价信息。使用已经下载的同 revision parquet，不下载新答案。三题均可评分，排除数为 0；函数级指标本轮不做。

| 任务 | 参考文件代理 | B | C 初始 | D 初始 |
|---|---|---:|---:|---:|
| Django-12262 | django/template/library.py | 1 | 1 | 1 |
| SymPy-20438 | sympy/core/relational.py | 1 | 1 | 1 |
| 同题 | sympy/sets/handlers/comparison.py | 887 | 120 | 120 |
| 同题 | sympy/sets/handlers/issubset.py | 231 | 98 | 98 |
| SymPy-21379 | sympy/core/mod.py | 551 | 285 | 285 |

三题 C/D 初始文件、名次和分数一致；reason 文本分别可为 RRF 与 RRF(L,S)，不能把说明文字差异误判为实际排名差异。完整保存列表与运行元数据的长度一致，并与 prompt 前缀和初始上下文核对；本包没有独立的上游排名结果文件，未声称重新生成验证了完整排名。

| 按任务平均的指标 | A | B | C | D 初始 |
|---|---:|---:|---:|---:|
| Hit@1 | N/A | 66.7% | 66.7% | 66.7% |
| Hit@5 | N/A | 66.7% | 66.7% | 66.7% |
| Recall@5 | N/A | 44.4% | 44.4% | 44.4% |
| MRR | N/A | 0.667272 | 0.667836 | 0.667836 |
| Hit@20 | N/A | 2/3 | 2/3 | 2/3 |

SymPy-20438 有三个目标，Top-5 只有一个，所以该题 Hit@5=1，Recall@5=1/3。三题 Recall@5 为 (1+1/3+0)/3。与旧五题每题一个目标不同，这次不能把 Hit 和 Recall 当成同一指标。

#### 排名 → 查看 → 修复

这里“查看”沿用旧版：模型可见的源码正文、搜索片段、traceback 源码行或 diff；仅看到路径不算查看。更严格的“直接打开”另存 JSON。多目标任务中，“查看任一目标”与“查看已注入的那个目标”分开。

| 任务 | B：Top-20 / 查看已注入目标 / 修复 | C | D |
|---|---|---|---|
| Django-12262 | 命中 / 已看 / 失败 | 命中 / 已看 / 失败 | 命中 / 已看 / 失败 |
| SymPy-20438 | 命中 / 已看 / 失败 | 命中 / 已看 / 失败 | 命中 / **未观察到** / 失败 |
| SymPy-21379 | 未中 / N/A / 失败 | 未中 / N/A / 成功 | 未中 / N/A / 成功 |

B/C/D 的“命中后查看率”分别为 2/2、2/2、1/2；三组在“命中且已查看”子集中修复数均为 0。SymPy-21379 的 A/C/D 成功属于初始 Top-20 没有目标但后来找到源码的情况，不能遗漏。

SymPy-20438 D 后来确实查看了另一目标 `handlers/issubset.py`，但没有观察到读取已注入的 `core/relational.py`；因此“查看过任一相关文件”不能掩盖“没有使用已注入目标”的区别。SymPy-21379 B 只通过 traceback 见到 `mod.py` 的源码行，没有观察到直接打开该文件，最后只改了 hyperbolic.py。

#### D 首次可用失败

| 任务 | 记录失败 / 可用 / 应用更新 | 首次更新目标名次 | 目标融合分数 | 送达 |
|---|---:|---|---|---|
| Django-12262 | 1 / 1 / 1 | 1 → 1，ΔRR=0 | 0.0327868852 → 0.0486599011 | 第3次模型调用前，messages[8] |
| SymPy-20438 | 0 / 0 / 0 | N/A | N/A | 无更新 |
| SymPy-21379 | 0 / 0 / 0 | N/A | N/A | 无更新 |

首次可用失败覆盖率为 **1/3**。Django 的失败原文哈希与解析记录一致，映射到 engine.py、base.py、library.py；重排前后链一致，Top-20 顺序有变化，注入文本确实出现在下一次模型调用之前。目标本就第 1，分数增加不代表概率提高，也没有目标名次收益。该批没有记录到重复更新或无效失败被应用，但只有一个事件，不能据此充分验证所有去重/门控分支。

两个 SymPy 的零事件并不意味着输出没有异常。21379 的首次复现用 try/except + traceback.print_exc()，进程退出码为 0；20438 用 try/except 打印 AttributeError，也返回 0。21379 后续还出现 Python 错误被最后的 sed 命令成功状态遮蔽的情况。**异常文本已供 Agent 普通推理使用，但未进入 D 的更新链。** 这与旧实现“只处理非零返回码”的行为一致；因缺少本批 src，机制归因仍应表述为轨迹支持的解释，不能声称逐行验证了实际运行实现。

**本节来源：** `R/{localization_candidates.json,prompt_candidates.json,effective_task.txt,trajectory.json,run_result.json}`，D 的整个 `failure_feedback/`；评价路径来自 `O/experiments/dev5_abcd_v1/evaluation_dataset/swebench_verified_78f471bf_test.parquet` 的 patch 文件头。首次事件、分数和送达索引见 `analysis.json → attempts[].d_feedback`。

### 5.3 探索效率与消耗

#### 源码查看

每格为“不同 Python 源文件数 / 首次查看任一参考目标前的模型步骤数”。0 表示第 1 次模型交互就产生可见目标源码，不表示 Agent 一开始已读取源码。搜索与 traceback 也可贡献文件数，因此文件越多不一定越好。

| 任务 | A | B | C | D |
|---|---:|---:|---:|---:|
| Django-12262 | 4 / 0 | 9 / 0 | 2 / 0 | 3 / 0 |
| SymPy-20438 | 10 / 0 | 7 / 0 | 10 / 0 | 6 / 0 |
| SymPy-21379 | 26 / 0 | 25 / 0 | 31 / 12 | 12 / 0 |

12 组都观察到至少一个目标的源码内容，无未决直接读取记录；但多目标覆盖不等于所有目标均被查看。按旧版提取器逐条保存命令、消息索引、源码证据与固定 base-commit blob。真实执行的 Shell 命令数：Django A/B/C/D 为 5/9/6/10，20438 为 15/13/18/10，21379 为 14/11/32/15；提交哨兵未实际执行的命令不计入。

#### 逐题调用、token 与费用

输入 token 已包含缓存命中的输入；**总 token=输入+输出**，不能再加缓存列。费用取服务响应记录的 estimated_cost 求和，是估算 API 成本，不代表额外账单核验。

| 任务 | 条件 | API调用 | 输入 | 输出 | 缓存输入 | 总token | USD |
|---|---|---:|---:|---:|---:|---:|---:|
| Django-12262 | A | 6 | 15,473 | 712 | 11,392 | 16,185 | 0.007119 |
| 同题 | B | 7 | 67,352 | 1,173 | 53,760 | 68,525 | 0.019505 |
| 同题 | C | 6 | 30,393 | 917 | 22,656 | 31,310 | 0.011628 |
| 同题 | D | 10 | 76,900 | 3,551 | 64,000 | 80,451 | 0.030455 |
| SymPy-20438 | A | 14 | 172,907 | 3,478 | 153,856 | 176,385 | 0.041478 |
| 同题 | B | 10 | 108,803 | 2,052 | 93,568 | 110,855 | 0.027678 |
| 同题 | C | 14 | 198,065 | 3,427 | 176,512 | 201,492 | 0.044825 |
| 同题 | D | 7 | 57,489 | 1,692 | 45,696 | 59,181 | 0.019886 |
| SymPy-21379 | A | 10 | 85,508 | 2,141 | 71,296 | 87,649 | 0.025641 |
| 同题 | B | 7 | 51,394 | 1,656 | 40,576 | 53,050 | 0.018609 |
| 同题 | C | 19 | 355,390 | 4,237 | 324,096 | 359,627 | 0.066844 |
| 同题 | D | 11 | 79,212 | 2,553 | 67,968 | 81,765 | 0.025019 |

| 三题合计 | A | B | C | D |
|---|---:|---:|---:|---:|
| 调用 | 30 | 24 | 39 | 28 |
| 总token | 280,219 | 232,430 | 592,429 | 221,397 |
| 估算费用 USD | 0.074238 | 0.065791 | 0.123297 | 0.075360 |

D 相比 A 少用 58,822 token，但少修复一题，费用略高；不能概括为“更省且同样有效”。D 相比 C 少用 371,032 token，修复结果相同；主要差异来自两个没有发生 D 更新的 SymPy 轨迹，不能把节约归因于反馈模块。B 的调用和时间较少，却三题全失败，也不能只凭短轨迹判定效率更优。

#### 逐题时间，单位秒

| 任务 | 条件 | Agent wall | 官方Harness | 索引访问（已含在wall内） | 旧D overhead（已含在wall内） |
|---|---|---:|---:|---:|---:|
| Django-12262 | A | 12.585 | 25.49 | 0.555 | N/A |
| 同题 | B | 18.573 | 24.80 | 0.432 | N/A |
| 同题 | C | 13.912 | 24.75 | 0.433 | N/A |
| 同题 | D | 108.308 | 24.88 | 0.390 | 10.176 |
| SymPy-20438 | A | 44.288 | 46.18 | 0.898 | N/A |
| 同题 | B | 28.782 | 46.21 | 0.852 | N/A |
| 同题 | C | 42.227 | 44.69 | 0.794 | N/A |
| 同题 | D | 63.207 | 47.13 | 0.829 | 27.518 |
| SymPy-21379 | A | 111.333 | 37.64 | 20.451 | N/A |
| 同题 | B | 17.544 | 39.29 | 0.725 | N/A |
| 同题 | C | 50.192 | 38.27 | 0.737 | N/A |
| 同题 | D | 49.607 | 38.62 | 0.735 | 22.917 |
| 三题合计 | A | 168.206 | 109.31 | — | — |
| 三题合计 | B | 64.899 | 110.30 | — | — |
| 三题合计 | C | 106.332 | 107.71 | — | — |
| 三题合计 | D | 221.122 | 110.63 | — | — |

timing_scope 声明 Agent wall 从 runner 入口到 Docker 清理，已包含索引访问、定位准备、环境设置、Agent 执行和运行时反馈；上表各列不能直接相加。Harness 是独立最终评测，单列。B/C 外部预计算时间未记录，当前 wall 不能称为完整方法总成本，也不因此阻塞本轮分析。

两个零更新的 D 仍有 22.917 / 27.518 秒旧 overhead，直接说明该字段不能解释成纯反馈处理时间。21379 A 的索引访问为 20.451 秒，其他条件约 0.7 秒，存在准备/缓存状态差异的迹象；无法据此精确分解所有墙钟差异。D−C 在三题分别为 +94.396、+20.980、−0.585 秒，均不能直接当作反馈模块耗时。

#### 合并汇总 token 错误的处理

`N/scripts/build_combined_analysis.py → extract_usage` 从后向前找到带 total_tokens 的行便覆盖汇总，而 usage.jsonl 是逐调用记录。32 组 token 字段都等于最后一行。例：旧 Django-11133 A 的总 token 被写成 7,778，逐次正确总和为 32,232。

本报告没有运行或修改该脚本。32 组成本、调用、resolved、Agent wall、Harness 时间分别与原始材料核对一致；修正 token 并不意味着这些字段也错。完整审计在 `analysis.json → combined_audit`。

**本节来源：** `R/{usage.jsonl,run_result.json,timings.json,trajectory.json}`、`H/harness_wall_seconds.txt`，旧批对应原始文件；源码查看还读取旧缓存中各新任务 base_commit 的原始 Git blob，不访问上游修复。

### 5.4 代表性轨迹、失败原因与新旧对照

以下消息索引均从 0 开始；q 表示模型调用序号。报告中的具体修复代码只来自 Agent 自己的补丁与轨迹，不来自参考修复内容。

#### Django-12262：目标已找到，仍在修复逻辑上分化

- **A 成功**：`django__django-12262_A_4aedcb24`，q1 搜索即命中 library.py，q2 读取 parse_bits，q3 将合法关键字判断从未处理列表改为 kwonly；随后编译与 diff 检查，官方 4/4 F2P。不能把这解释为 A 做了更全面的验证：它没有展示完整行为测试，官方结果才是成功依据。
- **B/C 失败**：`..._B_07bad546`、`..._C_530a2f4d`，都直接读取正确文件。B 将 unhandled_kwargs 改为全部 kwonly；C 再在末尾排除有默认值的项。结果分别 1/4、2/4。B 的自测还因模板加载环境问题中断（messages[10]），后续只做有限检查。
- **D 失败**：`..._D_e10b202e`，q2 的 TemplateSyntaxError 被正确保存、映射并在 q3 前注入；此时目标此前已经打开、排名也是第 1。后续多次修改，messages[14] 出现默认参数分支异常，messages[16] 又显示 `TypeError argument of type 'NoneType' is not iterable`。最终补丁仍含未保护 kwonly_defaults 的成员检查，并提交了更复杂的参数逻辑；官方只过 2/4。可据此认为验证和修复覆盖不足，但不能将全部失败归因于重排。

本题支持“定位已完成不等于修复已完成”，不支持“D 没找到文件”。D 的一次模型格式错误在 messages[19]，也不应混作运行时源码失败反馈。

#### SymPy-21379：异常信息可见，但反馈模块没有触发

- **D 成功且零更新**：`sympy__sympy-21379_D_b9d3b913`。q1 把异常捕获后打印 traceback（messages[2] 命令，messages[3] 返回码 0），q2 直接读取 mod.py，q5 修改 GCD 处理，最终用 PolynomialError 异常分支保留未求值行为；官方 1/1、91/91。q6 出现的 Python 错误也被后续 sed 成功状态遮蔽（messages[18–19]），反馈记录依然为空。成功来自这条实际探索轨迹，不能归功于 D 更新。
- **B 失败但自建复现通过**：`..._B_514ce584` 只修改 hyperbolic.py。messages[13] 的示例已输出表达式，但官方 F2P 为 0/1。它见过 mod.py 的 traceback 源码行，却未直接打开；“见到路径或一行源码”与深入检查实现不能等同。现有证据支持覆盖不完整，不足以断言唯一根因。
- **A/C 成功**：`..._A_713ba62f` 最终改动 mod.py 与 hyperbolic.py；`..._C_3476e59b` 最终改动 mod.py。C 经 19 次调用、359,627 token，直到第13次调用才观察到目标源码；D 为11次调用、81,765 token。两者初始排名相同且 D 无更新，差异不能当作反馈加速证据。

官方通过只表明通过了本次测试集合，不能证明 Agent 补丁中的所有额外修改都普遍正确。

#### SymPy-20438：多文件代理与未完成的行为修复

四组最终都只提交 sets.py 改动，官方 F2P 均为 0/2；参考文件代理有三个，但它们不是唯一允许修改的位置，不能仅因补丁路径不同就判错。

- **D** `sympy__sympy-20438_D_124384a9`：q1 输出 subset 为 None 并捕获 AttributeError（messages[5]），q4 后 subset 变为 True，但 `Eq(...).simplify()` 仍出现 EmptySet.equals 异常（messages[13]）。这两次命令均为 rc=0。Agent 后来做其他 subset 检查并提交，没有修复该可见异常；目标 relational.py 虽已注入，未观察到被查看。
- **C** `..._C_258b0715`：多轮增加 equals 和 subset 分支，messages[28] 的有限示例变为 True，官方仍 0/2。说明几个成功样例不能替代官方覆盖；不能仅根据有限输出确定所有未覆盖边界。
- **A** `..._A_d53bdc45`：还出现 1 个 P2P 回归（92/93），主要分类为 F4；其 q12 测试尝试因缺 pytest 而失败（messages[27]），是验证限制，不是该次 Agent 启动失败。B、C、D 未观察到 P2P 回归，但也没有修复目标测试。

#### 失败分类口径

8 个未修复的有效运行中，SymPy-20438 A 记为 **F4：官方观察到回归**；其余 7 个先记为 **F3：可应用补丁仍有目标测试失败**，再在上述案例中解释验证不足、目标使用不足等观察。不把“修改了非参考路径”直接编码为误诊，不把猜测写成唯一根因。6 次零调用启动超时另记 F5，不进入 12 个有效运行的失败分母。分类是证据辅助编码，未做独立人工复核。

#### 与旧五题发现对照

| 旧五题观察 | 新三题证据 | 本轮判断 |
|---|---|---|
| C 可提高目标排名，但不保证修复 | 20438 两个目标显著前移，四组仍失败；21379 前移但仍未入 Top-20 | 支持“排名与修复分开评价” |
| Top-20 已注入不保证查看 | 20438 D 没有查看已注入的 relational.py | 支持；多目标任务需检查是否查看同一个被注入目标 |
| D 总体未优于 A | 新三题 D 比 A 少修复一题，C/D 无任务级差异 | 本轮未提供 D 优势证据，不等于证明普遍无效 |
| D 触发覆盖偏低（旧2/5） | 新1/3，且两题异常输出被 rc=0 遮蔽 | 增加了具体触发边界解释 |
| 旧批 D token 总量高于 C | 新批 D token 明显低于 C，但两题没有发生 D 更新 | 成本方向不稳定，不能泛化为固定开销比例 |
| issue 的定位提示可能影响比较 | 新三题仍有 API/复现线索；20438 更有 traceback | 不能把新三题统称“无定位信息” |

Django issue 已点名 simple_tag、inclusion_tag 和两类错误；21379 给出 subs/Piecewise/clear_cache、real=True 的最小复现，但无目标文件 traceback；20438 原文直接给 relational.py traceback。三题 manifest 的 has_localization_hint 都为 yes。选题时应区分“没有文件路径”“没有 traceback”和“没有任何定位线索”，并保留原 issue，不删线索制造优势。

**本节来源：** 表中运行的 `trajectory.json#messages[index]`、Agent `patch.diff` 与官方 `evaluation/report.json`；旧观察来自 [旧五题报告](../reports/01_original_eight_tasks.md)。源材料路径及完整 run_id 可在本报告附表定位。

### 5.5 小样本、跨批次限制及后续判断

这是 development 中针对机制假设挑选的三题，不是独立抽样的正式测试集；没有重复实验，不评价稳定性、不计算显著性结论。原生 split=test 不改变这一点。两批的模型标识、预算和记录的系统提示一致，但提交号不同且新 src 缺失，跨批次只能作描述性对照。

目前最有信息量的后续方向是：先明确“可用失败”的运行接口是否要求非零返回码，以及 Agent 捕获异常或多命令串联时如何保留错误状态，再在后续预先固定的开发协议中检验触发覆盖。本轮不修改历史事件、不补跑，也不因为没记录单独排名时间而阻塞报告。若未来只调整错误检测规则，应保留去重、无关环境错误筛除与更新上限，不能把每个 Error 字样都算可用源码证据。

#### 八题合并：仅作补充

| 条件 | 旧五题修复 | 新三题修复 | 八题修复 | 八题正确总token | 八题估算USD |
|---|---:|---:|---:|---:|---:|
| A | 3/5 | 2/3 | 5/8，62.5% | 566,254 | 0.161366 |
| B | 4/5 | 0/3 | 4/8，50% | 664,566 | 0.177897 |
| C | 3/5 | 1/3 | 4/8，50% | 874,634 | 0.210780 |
| D | 3/5 | 1/3 | 4/8，50% | 860,835 | 0.226283 |

八题合计 D 的可用失败覆盖为 3/8。该表是两批已运行开发任务的描述性汇总，不是统一版本、同一抽样规则下的新基准结论，也不替代新三题的独立分析。

#### 如需加强核查，只需补这些，不用重下整个项目

1. 新提交 `8686189...` 对应的核心源文件或相对旧提交的差异：至少 failure_feedback、swebench_runner、context、failure_analysis、localization/ranker 及结构/索引相关文件；也可提供包含该提交的 Git bundle。用于确认实现一致性。
2. 如需独立原生补丁证据，提供这12组 `logs/evaluation/<evaluation_run_id>/<run_id>/<task_id>/patch.diff`；目前日志中的提交补丁已核对，缺少这些文件不阻塞本报告。
3. 实际启动命令、Harness 版本/镜像 digest、若有则提供解码参数与 B/C 预计算计时；未记录的保持未知，不要求重跑。

### 运行 ID 速查

以下均为完成尝试；启动失败的六个 run_id 及错误仍保留在 CSV/JSON。

| 任务 | A | B | C | D |
|---|---|---|---|---|
| Django-12262 | django__django-12262_A_4aedcb24 | django__django-12262_B_07bad546 | django__django-12262_C_530a2f4d | django__django-12262_D_e10b202e |
| SymPy-20438 | sympy__sympy-20438_A_d53bdc45 | sympy__sympy-20438_B_253ef3a1 | sympy__sympy-20438_C_258b0715 | sympy__sympy-20438_D_124384a9 |
| SymPy-21379 | sympy__sympy-21379_A_713ba62f | sympy__sympy-21379_B_514ce584 | sympy__sympy-21379_C_3476e59b | sympy__sympy-21379_D_b9d3b913 |

术语固定：resolved=官方修复成功；completed=Agent 完成；目标=评价侧参考文件代理；可用失败=反馈日志 analysis.usable=true；应用更新=update_applied=true 且有实际送达证据。把这些状态分开，才能避免把运行完成、排名变化和修复成功当成同一个结果。

## 随包证据索引

| 实验 | 任务 | 条件/尝试 | 入选 | 运行、轨迹、官方结果 |
|---|---|---|---|---|
| original_dev5 | django__django-11133 | A / 1 | 否 | [记录](../evidence/records/original_dev5/django__django-11133_A_847146cd/run_result.json) · [补丁](../evidence/records/original_dev5/django__django-11133_A_847146cd/patch.diff) |
| original_dev5 | django__django-11133 | A / 2 | 是 | [记录](../evidence/records/original_dev5/django__django-11133_A_8e19ca5c/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0111) · [补丁](../evidence/records/original_dev5/django__django-11133_A_8e19ca5c/patch.diff) · [官方](../evidence/records/original_dev5/django__django-11133_A_8e19ca5c/official/report.json) |
| original_dev5 | django__django-11133 | B / 1 | 否 | [记录](../evidence/records/original_dev5/django__django-11133_B_e267b44c/run_result.json) · [补丁](../evidence/records/original_dev5/django__django-11133_B_e267b44c/patch.diff) |
| original_dev5 | django__django-11133 | B / 2 | 是 | [记录](../evidence/records/original_dev5/django__django-11133_B_6077748b/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0114) · [补丁](../evidence/records/original_dev5/django__django-11133_B_6077748b/patch.diff) · [官方](../evidence/records/original_dev5/django__django-11133_B_6077748b/official/report.json) |
| original_dev5 | django__django-11133 | C / 1 | 否 | [记录](../evidence/records/original_dev5/django__django-11133_C_b97e534e/run_result.json) · [补丁](../evidence/records/original_dev5/django__django-11133_C_b97e534e/patch.diff) |
| original_dev5 | django__django-11133 | C / 2 | 是 | [记录](../evidence/records/original_dev5/django__django-11133_C_a9d9d5ea/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0118) · [补丁](../evidence/records/original_dev5/django__django-11133_C_a9d9d5ea/patch.diff) · [官方](../evidence/records/original_dev5/django__django-11133_C_a9d9d5ea/official/report.json) |
| original_dev5 | django__django-11133 | D / 1 | 是 | [记录](../evidence/records/original_dev5/django__django-11133_D_8a58c59e/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0124) · [补丁](../evidence/records/original_dev5/django__django-11133_D_8a58c59e/patch.diff) · [官方](../evidence/records/original_dev5/django__django-11133_D_8a58c59e/official/report.json) |
| original_dev5 | pytest-dev__pytest-7571 | A / 1 | 是 | [记录](../evidence/records/original_dev5/pytest-dev__pytest-7571_A_b2fdd0bd/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0127) · [补丁](../evidence/records/original_dev5/pytest-dev__pytest-7571_A_b2fdd0bd/patch.diff) · [官方](../evidence/records/original_dev5/pytest-dev__pytest-7571_A_b2fdd0bd/official/report.json) |
| original_dev5 | pytest-dev__pytest-7571 | B / 1 | 是 | [记录](../evidence/records/original_dev5/pytest-dev__pytest-7571_B_4e76d17e/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0130) · [补丁](../evidence/records/original_dev5/pytest-dev__pytest-7571_B_4e76d17e/patch.diff) · [官方](../evidence/records/original_dev5/pytest-dev__pytest-7571_B_4e76d17e/official/report.json) |
| original_dev5 | pytest-dev__pytest-7571 | C / 1 | 是 | [记录](../evidence/records/original_dev5/pytest-dev__pytest-7571_C_5f2f3506/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0133) · [补丁](../evidence/records/original_dev5/pytest-dev__pytest-7571_C_5f2f3506/patch.diff) · [官方](../evidence/records/original_dev5/pytest-dev__pytest-7571_C_5f2f3506/official/report.json) |
| original_dev5 | pytest-dev__pytest-7571 | D / 1 | 是 | [记录](../evidence/records/original_dev5/pytest-dev__pytest-7571_D_a0b7c3b7/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0138) · [补丁](../evidence/records/original_dev5/pytest-dev__pytest-7571_D_a0b7c3b7/patch.diff) · [官方](../evidence/records/original_dev5/pytest-dev__pytest-7571_D_a0b7c3b7/official/report.json) |
| original_dev5 | sphinx-doc__sphinx-8595 | A / 1 | 否 | [记录](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_A_5511cc61/run_result.json) · [补丁](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_A_5511cc61/patch.diff) |
| original_dev5 | sphinx-doc__sphinx-8595 | A / 2 | 是 | [记录](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_A_d3f56a5a/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0142) · [补丁](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_A_d3f56a5a/patch.diff) · [官方](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_A_d3f56a5a/official/report.json) |
| original_dev5 | sphinx-doc__sphinx-8595 | B / 1 | 否 | [记录](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_B_c6db48c1/run_result.json) · [补丁](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_B_c6db48c1/patch.diff) |
| original_dev5 | sphinx-doc__sphinx-8595 | B / 2 | 是 | [记录](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_B_bbe306a9/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0145) · [补丁](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_B_bbe306a9/patch.diff) · [官方](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_B_bbe306a9/official/report.json) |
| original_dev5 | sphinx-doc__sphinx-8595 | C / 1 | 否 | [记录](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_C_b90d1a12/run_result.json) · [补丁](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_C_b90d1a12/patch.diff) |
| original_dev5 | sphinx-doc__sphinx-8595 | C / 2 | 是 | [记录](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_C_a1e59bcb/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0149) · [补丁](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_C_a1e59bcb/patch.diff) · [官方](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_C_a1e59bcb/official/report.json) |
| original_dev5 | sphinx-doc__sphinx-8595 | D / 1 | 是 | [记录](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_D_e196eabf/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0155) · [补丁](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_D_e196eabf/patch.diff) · [官方](../evidence/records/original_dev5/sphinx-doc__sphinx-8595_D_e196eabf/official/report.json) |
| original_dev5 | sympy__sympy-17630 | A / 1 | 是 | [记录](../evidence/records/original_dev5/sympy__sympy-17630_A_8944a852/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0158) · [补丁](../evidence/records/original_dev5/sympy__sympy-17630_A_8944a852/patch.diff) · [官方](../evidence/records/original_dev5/sympy__sympy-17630_A_8944a852/official/report.json) |
| original_dev5 | sympy__sympy-17630 | B / 1 | 是 | [记录](../evidence/records/original_dev5/sympy__sympy-17630_B_310345fe/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0161) · [补丁](../evidence/records/original_dev5/sympy__sympy-17630_B_310345fe/patch.diff) · [官方](../evidence/records/original_dev5/sympy__sympy-17630_B_310345fe/official/report.json) |
| original_dev5 | sympy__sympy-17630 | C / 1 | 是 | [记录](../evidence/records/original_dev5/sympy__sympy-17630_C_7d7d5077/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0164) · [补丁](../evidence/records/original_dev5/sympy__sympy-17630_C_7d7d5077/patch.diff) · [官方](../evidence/records/original_dev5/sympy__sympy-17630_C_7d7d5077/official/report.json) |
| original_dev5 | sympy__sympy-17630 | D / 1 | 是 | [记录](../evidence/records/original_dev5/sympy__sympy-17630_D_b6378bb3/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0169) · [补丁](../evidence/records/original_dev5/sympy__sympy-17630_D_b6378bb3/patch.diff) · [官方](../evidence/records/original_dev5/sympy__sympy-17630_D_b6378bb3/official/report.json) |
| original_dev5 | sympy__sympy-23262 | A / 1 | 是 | [记录](../evidence/records/original_dev5/sympy__sympy-23262_A_cb3e111d/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0172) · [补丁](../evidence/records/original_dev5/sympy__sympy-23262_A_cb3e111d/patch.diff) · [官方](../evidence/records/original_dev5/sympy__sympy-23262_A_cb3e111d/official/report.json) |
| original_dev5 | sympy__sympy-23262 | B / 1 | 是 | [记录](../evidence/records/original_dev5/sympy__sympy-23262_B_58239bd3/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0175) · [补丁](../evidence/records/original_dev5/sympy__sympy-23262_B_58239bd3/patch.diff) · [官方](../evidence/records/original_dev5/sympy__sympy-23262_B_58239bd3/official/report.json) |
| original_dev5 | sympy__sympy-23262 | C / 1 | 是 | [记录](../evidence/records/original_dev5/sympy__sympy-23262_C_a39c81b8/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0178) · [补丁](../evidence/records/original_dev5/sympy__sympy-23262_C_a39c81b8/patch.diff) · [官方](../evidence/records/original_dev5/sympy__sympy-23262_C_a39c81b8/official/report.json) |
| original_dev5 | sympy__sympy-23262 | D / 1 | 是 | [记录](../evidence/records/original_dev5/sympy__sympy-23262_D_3fd15bb3/run_result.json) · [轨迹（归档文件）](../evidence/ARCHIVE_INDEX.md#file-0183) · [补丁](../evidence/records/original_dev5/sympy__sympy-23262_D_3fd15bb3/patch.diff) · [官方](../evidence/records/original_dev5/sympy__sympy-23262_D_3fd15bb3/official/report.json) |
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

## 历史材料范围说明

本整理版保留原报告的分析日期、审计结论与解释边界。原 PDF proposal、早期一次性分析脚本、重复归档包和其他探索实验报告没有重复放入本目录；它们不是本次通用工具运行的依赖。原始压缩包身份及 SHA-256 见 evidence/manifest.json。当前报告的完整指标应按配套完整证据包中的清单复算；精简版保留预计算汇总和小体积证据。

历史源码浏览和失败原因是人工/先前审计标注，并未因换成统一工具而变成自动推导的因果结论。本包不包含参考修复 hunk 或整套基准文件。源文件名是评价代理，不代表只有修改该文件才能修好。
