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

4. S: files with positive score, highest first; ties by lexical rank (files not
   in L last), then path.<br>
   S：分数为正的文件，从高到低；同分时按词法排名（不在 L 中的排最后），再按路径。
5. No seed has a neighbor → S is empty and C keeps L unchanged.<br>
   没有任何种子有邻居 → S 为空，C 直接沿用 L。

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

Each `StructuralCandidate` has `file`, `rank`, `score` and `reason` (e.g.
`imported by lexical #1 sympy/matrices/expressions/blockmatrix.py`), the same
field names as `LocalizationCandidate` in `src/agent/contracts.py`.

每个 `StructuralCandidate` 有 `file`、`rank`、`score`、`reason`（例如
`imported by lexical #1 sympy/matrices/expressions/blockmatrix.py`），字段名与
`src/agent/contracts.py` 中的 `LocalizationCandidate` 相同。

Batch over tasks, reading the retrieval module's JSON output:

批量处理多个任务，读取检索模块输出的 JSON：

```bash
python scripts/run_structural.py --lexical bm25_results.json -o structural_results.json
```
