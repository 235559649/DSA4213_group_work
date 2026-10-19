# Structural ranking (role 2) / 结构排名（2 号）

Condition C adds a structural file ranking S to the lexical ranking L. S is
built from one-hop import neighbors of the top lexical files, as specified in
proposal section 3.4. Code: `src/localization/structural.py`.

条件 C 在词法排名 L 的基础上加入结构排名 S。S 由词法排名靠前文件的一跳导入邻居得到，
完全按照 proposal 3.4 节的定义。代码：`src/localization/structural.py`。

## Method / 方法

1. Seeds Q: up to the first 10 files with positive scores in L.<br>
   种子 Q：L 中前 10 个分数为正的文件。
2. Neighbors N(q): files that seed q imports or that import q, excluding q
   (`index.neighbors`).<br>
   邻居 N(q)：种子 q 导入的文件和导入 q 的文件，不含 q 自身（`index.neighbors`）。
3. Each seed spreads 1 / r_L(q) equally over its neighbors; a file's score is
   the sum it receives:<br>
   每个种子把 1 / r_L(q) 平均分给它的邻居；文件的分数是它收到的总和：

   s_struct(f) = Σ_{q∈Q} 1[f ∈ N(q)] / (r_L(q) · max(1, |N(q)|))

4. S: **the seeds first, in lexical order** (see below), then the other files
   with positive score, highest first; ties by lexical rank (files not in L
   last), then path.<br>
   S：**先放种子本身，按词法顺序**（见下文），再放其余分数为正的文件，从高到低；
   同分时按词法排名（不在 L 中的排最后），再按路径。
5. No seed has a neighbor → S is just the seeds, and fusing it with L leaves
   L's order unchanged.<br>
   没有任何种子有邻居 → S 只有种子本身，和 L 融合后 L 的顺序不变。

## Design choice: seeds head S / 设计选择：种子放在 S 最前面

**Team decision, 2026-10-19, before the freeze. Differs from the proposal; report it.**

**组内决定（2026-10-19，冻结前）。与 proposal 不同，需要在报告中说明。**

In the proposal, S holds only the seeds' neighbors; a seed appears in S only
if it neighbors another seed. Fused with L by RRF, a correct file ranked #1 in
L but absent from S gets one RRF term, while files present in both lists get
two and overtake it (django-11133: #1 → #23). On the 20 development tasks
(L = role 3's full BM25 ranking, RRF k = 60):

proposal 中 S 只包含种子的邻居，种子只有在恰好是别的种子的邻居时才出现在 S 里。用 RRF 和 L
融合时，一个在 L 中排第 1 但不在 S 中的正确文件只能拿到一份分数，而同时出现在两份排名里的文件
能拿到两份并反超它（django-11133：第 1 → 第 23）。在 20 个开发任务上（L 为 3 号的完整 BM25
排名，RRF k = 60）：

| | Hit@1 | Hit@5 | MRR |
|---|---|---|---|
| L only (Condition B) / 只用 L（条件 B） | 8/20 | 12/20 | 0.500 |
| C, proposal's S / C，proposal 原定义的 S | 6/20 | 11/20 | 0.393 |
| **C, seeds head S (default)** / **C，种子放在 S 最前面（默认）** | **8/20** | **12/20** | **0.504** |

With seeds at the front, 6 tasks improved and 1 got worse relative to L.
Caveats: 20 tasks, several variants tried (lower S weight in RRF, truncating
S), so the choice may overfit the development set. `include_seeds=False`
(`--no-seeds`) reproduces the proposal's S for comparison.

种子放在最前面后，相比 L 有 6 个任务变好、1 个变差。注意：只有 20 个任务，而且试过好几种方案
（降低 S 在 RRF 中的权重、截断 S 等），这个选择可能对开发集过拟合。`include_seeds=False`
（`--no-seeds`）可以复现 proposal 原定义的 S，用于对比。

Fusing L and S with RRF (k = 60) belongs to the retrieval module (role 3).

用 RRF（k = 60）融合 L 和 S 由检索模块（3 号）负责。

## Design choice: test files as neighbors / 设计选择：测试文件作为邻居

By default (`exclude_test_neighbors=True`) test files can be **seeds** but are
not **neighbors**. A test file's imports point at the code it tests, which is
useful. But a widely imported source file has dozens of test files importing
it; counting them would spread the seed's weight thin and fill S with tests,
which are not localization targets. This choice goes beyond the proposal and
should be confirmed on the development set and frozen before held-out runs.

默认（`exclude_test_neighbors=True`）测试文件可以当**种子**，但不能当**邻居**。
测试文件导入的是它要测试的代码，这一点有用；但一个被广泛导入的源码文件往往有几十个测试文件导入它，
把它们算进来会把种子的权重摊得很薄，还会让 S 被测试文件占满，而测试文件并不是定位目标。
这一点超出了 proposal 的定义，需要在开发集上确认，并在保留测试集实验前冻结。

## Usage / 用法

```python
from src.localization.structural import structural_ranking
from src.repository.swebench import build_task_index

index = build_task_index("django__django-11133")
lexical = retriever.retrieve(problem_statement, top_k=None)  # L: [(path, score), ...], best first
for c in structural_ranking(index, lexical):
    print(c.rank, c.file, c.score, c.reason)
```

Pass the **full** positive lexical ranking, not only the top 10: lexical ranks
also break ties, and RRF needs the full L.

请传入**完整的**正分词法排名，而不只是前 10 名：词法排名也用于打破平分，而且 RRF 需要完整的 L。

## Output / 输出

**File-level.** S ranks files; `symbol` and `symbol_type` are always `None`.
Function hints inside a file come from the retrieval module's entity scores
and the index's containment (`index.records_in_file`, `parent`).

**文件级。** S 只给文件排名，`symbol` 和 `symbol_type` 总是 `None`。文件内的函数提示来自
检索模块的实体级分数和索引里的包含关系（`index.records_in_file`、`parent`）。

Each `StructuralCandidate` has the `LocalizationCandidate` fields of
`src/agent/contracts.py` plus structured evidence:

每个 `StructuralCandidate` 包含 `src/agent/contracts.py` 中 `LocalizationCandidate` 的字段，
外加结构化的证据：

| Field / 字段 | Meaning / 含义 |
|---|---|
| `file`, `rank` | The file and its rank in S.<br>文件及其在 S 中的名次。 |
| `score` | s_struct(file), the sum of the neighbor relation weights; 0 for a seed that neighbors no other seed.<br>s_struct(file)，即各邻居关系权重之和；不是其他种子邻居的种子为 0。 |
| `symbol`, `symbol_type` | `None` (file-level).<br>`None`（文件级）。 |
| `reason` | Up to three strongest relations as text, e.g. `imported by lexical #1 sympy/matrices/expressions/blockmatrix.py`.<br>最强的最多三条关系的文字说明。 |
| `relations` | A `seed` relation first if the file is itself a seed (`weight` 0; it only fixes the position), then every contributing seed: `seed`, `seed_rank`, `relation` (`imported_by`: the candidate is imported by the seed; `imports`: the candidate imports the seed), `weight` = 1 / (seed_rank · \|N(seed)\|), strongest first.<br>如果文件本身是种子，第一条是 `seed` 关系（`weight` 为 0，只决定位置）；之后是每个贡献分数的种子：`seed`、`seed_rank`、`relation`（`imported_by`：候选文件被种子导入；`imports`：候选文件导入了种子）、`weight` = 1 / (seed_rank · \|N(seed)\|)，按权重从大到小。 |

## Batch JSON / 批量 JSON

```bash
python scripts/run_structural.py --lexical bm25_results.json -o structural_results.json
```

Input: the retrieval module's JSON, `[{"instance_id", "ranked_files": [{"rank", "path" or "file", "bm25_score" or "score"}]}]`.
Output, one entry per task:

输入：检索模块的 JSON，`[{"instance_id", "ranked_files": [{"rank", "path" 或 "file", "bm25_score" 或 "score"}]}]`。
输出，每个任务一项：

```json
{
  "instance_id": "sympy__sympy-17630",
  "index_sha256": "d3baa2f9...",
  "num_seeds": 10,
  "include_seeds": true,
  "exclude_test_neighbors": true,
  "num_lexical_files": 10,
  "ranked_files": [
    {
      "file": "sympy/core/compatibility.py",
      "rank": 1,
      "score": 0.110688,
      "symbol": null,
      "symbol_type": null,
      "reason": "imported by lexical #1 sympy/matrices/expressions/blockmatrix.py; ...",
      "relations": [
        {"seed": "sympy/matrices/expressions/blockmatrix.py", "seed_rank": 1, "relation": "imported_by", "weight": 0.043478}
      ]
    }
  ]
}
```

Dropping `relations` from an entry gives the keyword arguments of `LocalizationCandidate`.

去掉 `relations` 后，每一项正好是 `LocalizationCandidate` 的构造参数。
