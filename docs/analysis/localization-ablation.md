# Localization ablation (development set) / 定位对照实验（开发集）

Offline evidence for whether the ranking methods produce different rankings
(layer 1, mechanism) and whether those rankings are closer to the reference
files (layer 2, localization effectiveness). No agent runs and no model
calls. Layers 3 (repair) and 4 (overhead) are covered by the agent runs, the
comparison table below and `docs/evaluation/timing.md`. Generated on
2026-10-26.

离线证据，回答两个问题：各排名方法是否真的产生了不同的排名（第 1 层：机制有效性），以及这些排名是否更接近
参考补丁修改的文件（第 2 层：定位有效性）。不运行 Agent，不调用模型。第 3 层（修复）和第 4 层（开销）由
Agent 运行、下面的对照表和 `docs/evaluation/timing.md` 覆盖。2026-10-26 生成。

```bash
python scripts/localization_ablation.py --tasks-from experiments/bm25_results.json -o ablation.md
```

Every ranking is recomputed from the task's index and problem statement.
Reference files come from `src/evaluation/gold.py`, evaluation side only: the
target set G is the Python source files the reference patch modifies,
excluding tests, documentation and files that did not exist at base_commit
(proposal 5.2). Reference paths are not printed here (`--show-paths`).

每个排名都从任务的索引和问题描述重新计算。参考文件来自 `src/evaluation/gold.py`，只在评估侧使用：目标集合 G
是参考补丁修改的 Python 源文件，排除测试、文档以及 base_commit 时不存在的文件（proposal 5.2）。这里不显示
参考文件路径（需要时加 `--show-paths`）。

## Variants / 变体

| Key | Ranking / 排名 |
|---|---|
| L | BM25 file ranking (Condition B) / BM25 文件排名（条件 B） |
| S0 | structural ranking alone, proposal definition: neighbors of the top-10 lexical files, no seeds / 只用结构排名，proposal 定义：词法前 10 名的邻居，不含种子 |
| C | RRF(L, S) with the seeds at the head of S, **as used in the experiments** (Condition C) / RRF(L, S)，S 以种子开头，**即实验中实际使用的条件 C** |
| C0 | RRF(L, S0), the proposal's original Condition C / RRF(L, S0)，proposal 原定的条件 C |

## Layer 1 — mechanism / 第 1 层：机制有效性

Does a variant change what a top-k prompt would show, compared with L?

与 L 相比，各变体是否改变了 top-k 提示中会出现的文件？

| Variant | Top-5 differs from L / 前 5 名与 L 不同 | Top-20 differs from L / 前 20 名与 L 不同 | Mean top-20 overlap with L / 前 20 名与 L 的平均重合 |
|---|---|---|---|
| S0 | 20/20 | 20/20 | 0.20 |
| C | **0/20** | 20/20 | 0.69 |
| C0 | 20/20 | 20/20 | 0.45 |

**C never changes the top 5 and always changes the top 20.** With the seeds
at the head of S, RRF keeps L's top 10 in place, so the structural ranking can
only add files at ranks 11–20. It reaches the agent only because the
experiments show the top 20 (`localization_top_k = 20`); with a prompt of 10
or fewer candidates, Conditions B and C would be identical.

**C 从不改变前 5 名，但总会改变前 20 名。** S 以种子开头时，RRF 会保持 L 的前 10 名不变，所以结构排名只能在第
11–20 名加入文件。它之所以能影响 Agent，是因为实验给 Agent 看前 20 名（`localization_top_k = 20`）；如果提示
只有 10 个或更少的候选，条件 B 和 C 将完全相同。

## Layer 2 — localization effectiveness / 第 2 层：定位有效性

Proposal 5.2 metrics; Hit@10 and Hit@20 are added because the prompt shows
the top 20. 20 tasks, all scored (each modifies at least one Python source
file; two tasks have 2 or 3 target files).

proposal 5.2 的指标；因为提示展示前 20 名，额外加了 Hit@10 和 Hit@20。共 20 个任务，全部参与评分（每个都至少修改
了一个 Python 源文件；有两个任务有 2 或 3 个目标文件）。

| Variant | Hit@1 | Hit@5 | Recall@5 | MRR | Hit@10 | Hit@20 |
|---|---|---|---|---|---|---|
| L: BM25 (B) | 0.40 | 0.60 | 0.567 | 0.500 | 0.65 | 0.75 |
| S0: structural only | 0.05 | 0.20 | 0.200 | 0.142 | 0.45 | 0.50 |
| **C: as run** | 0.40 | 0.60 | 0.567 | **0.504** | 0.65 | **0.85** |
| C0: proposal's C | 0.30 | 0.55 | 0.492 | 0.393 | 0.55 | 0.65 |

Rank of the first reference file (- = not in the ranking):

第一个参考文件的名次（- 表示不在排名中）：

| Task | Targets | L | S0 | C | C0 |
|---|---|---|---|---|---|
| django__django-11133 | 1 | 1 | - | 1 | 23 |
| django__django-12262 | 1 | 1 | 3 | 1 | 1 |
| django__django-13158 | 1 | 2 | - | 2 | 27 |
| django__django-13417 | 1 | 2 | - | 2 | 30 |
| django__django-14017 | 1 | 1 | 23 | 1 | 3 |
| django__django-14539 | 1 | 9 | 4 | 9 | 1 |
| sympy__sympy-23262 | 1 | 35 | 34 | 19 | 17 |
| sympy__sympy-17630 | 1 | 52 | 7 | 18 | 13 |
| sympy__sympy-21379 | 1 | 551 | 211 | 285 | 285 |
| sympy__sympy-19346 | 1 | 215 | - | 340 | 340 |
| sympy__sympy-20154 | 1 | 1 | 1 | 1 | 1 |
| sympy__sympy-20438 | 3 | 1 | 8 | 1 | 1 |
| sphinx-doc__sphinx-8595 | 1 | 12 | 6 | 11 | 2 |
| sphinx-doc__sphinx-7462 | 2 | 14 | 7 | 13 | 3 |
| sphinx-doc__sphinx-9673 | 1 | 57 | 62 | 51 | 47 |
| sphinx-doc__sphinx-8721 | 1 | 1 | 49 | 1 | 5 |
| pytest-dev__pytest-7571 | 1 | 1 | 3 | 1 | 1 |
| pytest-dev__pytest-7205 | 1 | 1 | - | 1 | 44 |
| pytest-dev__pytest-7490 | 1 | 3 | 6 | 3 | 1 |
| pytest-dev__pytest-10356 | 1 | 3 | 18 | 3 | 5 |

### Reading / 解读

- **BM25 is a strong baseline when the issue names the code.** 8 of 20
  reference files rank first in L. These tasks leave little room for any
  other signal.<br>
  **当 issue 直接提到代码时，BM25 就是很强的基线。** 20 个参考文件中有 8 个在 L 中排第 1，其他信号在这些任务上
  几乎没有提升空间。
- **Structure alone is a weak localizer but a complementary one.** S0 scores
  far below L (MRR 0.142), yet it ranks some targets that BM25 buries much
  higher: sympy-17630 52 → 7, sympy-21379 551 → 211, sphinx-7462 14 → 7,
  sphinx-8595 12 → 6, django-14539 9 → 4.<br>
  **单独的结构信息是弱定位器，但能起互补作用。** S0 远低于 L（MRR 0.142），但它把一些被 BM25 埋在后面的目标排得
  高得多：sympy-17630 52 → 7，sympy-21379 551 → 211，sphinx-7462 14 → 7，sphinx-8595 12 → 6，django-14539 9 → 4。
- **The fusion decides who wins.** C0 lets those structural gains reach the
  top (django-14539 9 → 1, sphinx-8595 12 → 2, sphinx-7462 14 → 3) but pushes
  correct first-ranked BM25 files down (django-11133 1 → 23, pytest-7205
  1 → 44): MRR 0.500 → 0.393. C protects L's top 10 and adds structural files
  at 11–20: same Hit@1/5/10 as L, Hit@20 0.75 → 0.85 (sympy-23262 35 → 19,
  sympy-17630 52 → 18).<br>
  **融合方式决定了谁占上风。** C0 让结构信息的提升到达前排（django-14539 9 → 1，sphinx-8595 12 → 2，sphinx-7462
  14 → 3），但把 BM25 原本排第 1 的正确文件挤了下去（django-11133 1 → 23，pytest-7205 1 → 44）：MRR 0.500 →
  0.393。C 保护 L 的前 10 名，只在第 11–20 名加入结构信息找到的文件：Hit@1/5/10 与 L 相同，Hit@20 从 0.75 升到
  0.85（sympy-23262 35 → 19，sympy-17630 52 → 18）。
- **Neither method finds the hardest targets.** sympy-21379, sympy-19346 and
  sphinx-9673 stay outside the top 20 under every variant.<br>
  **最难的目标所有方法都找不到。** sympy-21379、sympy-19346、sphinx-9673 在所有变体下都不在前 20 名内。

### Limits / 局限

- **These 20 tasks were used to choose C.** "Seeds first" was decided on this
  development set (`docs/architecture/structural-ranking.md`), so C's numbers
  here are optimistic. An unbiased layer-2 estimate needs tasks that played
  no part in that choice; because the ablation needs no agent and no model,
  it can be run on the remaining SWE-bench Verified tasks at little cost.<br>
  **C 就是在这 20 个任务上选出来的。** "种子放在最前"是在这个开发集上决定的（`docs/architecture/structural-ranking.md`），
  所以 C 在这里的数字偏乐观。要得到无偏的第 2 层结论，需要用没有参与这个决定的任务；由于对照实验不需要 Agent
  也不调用模型，可以低成本地在 SWE-bench Verified 的其余任务上运行。
- 20 tasks, 23 target files: differences of one or two tasks are within noise.<br>
  只有 20 个任务、23 个目标文件：一两个任务的差别在波动范围内。
- File level only. Function Hit@5 (proposal 5.2) needs function candidates,
  which no condition produces yet.<br>
  只评文件级。函数级 Hit@5（proposal 5.2）需要函数候选，目前没有条件会产生。

## Linking to repair: the comparison table / 与修复结果对应：对照表

`scripts/run_comparison.py` joins the agent runs with the same reference
files, one row per run: where the first reference file was in the ranking
delivered to the run, whether it was among the candidates shown to the agent,
for D how the first usable runtime failure changed that rank (proposal 5.2),
and whether the official evaluation resolved the task. Missing run files are
reported as missing, never as misses.

`scripts/run_comparison.py` 把 Agent 运行和同一套参考文件对应起来，每次运行一行：第一个参考文件在交给该次运行的
排名中排第几、是否在展示给 Agent 的候选中、D 的第一次可用失败如何改变这个名次（proposal 5.2），以及官方评测是否
判定修复。运行目录中缺失的文件会显示为缺失，而不是未命中。

```bash
python scripts/run_comparison.py --runs-dir runs -o comparison.md
```

Run it on the server, where the run directories are. Whether the agent
actually opened the reference file comes from the trajectory labels in the
evaluation report.

在保存运行目录的服务器上运行。Agent 是否真的打开了参考文件，取自评估报告中的轨迹标注。
