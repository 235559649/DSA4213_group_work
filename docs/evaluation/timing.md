# Timing definitions / 计时口径

Which time quantities the report uses, how each is computed from the recorded
fields, and which fields must not be added together. Supplements
`evaluation_protocol.v0.1.md` (section 2.2, `timings`). Status as of
2026-10-26, including PR #15 and PR #17.

报告中使用哪些时间量、每一项如何从已记录的字段计算，以及哪些字段不能相加。作为
`evaluation_protocol.v0.1.md`（2.2 节 `timings`）的补充。截至 2026-10-26，包含 PR #15 和 PR #17。

## 1. Reported quantities / 报告项

Report these five quantities and nothing else. None of them overlaps another.

只报告下面五项，它们之间没有重叠。

| Quantity / 报告项 | Scope / 范围 | Counts as method cost? / 是否计入方法成本 |
|---|---|---|
| **T_agent** — the agent's own run (`agent.run()`) | per run / 每次运行 | yes / 是 |
| **T_loc** — localization overhead | per run (B/C: per task, see 3.2) / 每次运行（B/C 见 3.2） | yes / 是 |
| **T_pre** — building the repository index | per task / 每个任务一次 | reported separately / 单独报告 |
| **T_env** — starting and stopping the task container | per run / 每次运行 | no / 否 |
| **T_eval** — official SWE-bench evaluation | per run / 每次运行 | no / 否 |

RQ2's "after accounting for localization overhead" is **T_agent + T_loc**.
T_pre is shown next to it, since it is paid once per task and shared by all
conditions and repeats.

RQ2 所说的"计入定位开销之后"即 **T_agent + T_loc**。T_pre 在旁边单独列出，因为它每个任务只付一次，
由所有条件和重复运行共享。

## 2. T_loc by condition / 各条件的定位开销

| Condition / 条件 | T_loc | Fields / 字段 |
|---|---|---|
| A | 0 | — |
| B | index load + BM25 | `bm25_results.json` → `timing.index_load_seconds + timing.bm25_init_seconds + timing.bm25_seconds` |
| C | B + structural ranking + RRF | B, plus `structural_results.json` → `timing.structural_seconds`, plus `condition_c_results.json` → `timing.rrf_seconds` |
| D | initial ranking + all failure updates | run record → `config.failure_feedback.initial_localization_seconds + config.failure_feedback.feedback_total_seconds` |

- **Index load is counted once.** `index_load_seconds` appears in both
  `bm25_results.json` and `structural_results.json`; both measure the same
  operation, which a real pipeline performs once. Take it from
  `bm25_results.json` only.<br>
  **读索引只算一次。** `bm25_results.json` 和 `structural_results.json` 中都有 `index_load_seconds`，
  测的是同一个操作，实际流程中只做一次。只从 `bm25_results.json` 取。
- **D includes index building.** D reads the container and builds its index
  inside the run, so `initial_localization_seconds` already contains what B
  and C report as T_pre. When comparing T_loc across conditions, say so; for
  a like-for-like comparison, compare D's T_loc with C's T_loc + T_pre.<br>
  **D 包含建索引。** D 在运行中读取容器并现场建索引，所以 `initial_localization_seconds` 已经包含了
  B、C 记作 T_pre 的部分。跨条件比较 T_loc 时要注明这一点；要同口径比较，就用 D 的 T_loc 对比
  C 的 T_loc + T_pre。
- Per-failure detail for D is in
  `runs/<run_id>/failure_feedback/failure_updates.jsonl`, field
  `feedback_processing_seconds` per event; they sum to `feedback_total_seconds`.<br>
  D 每次报错的明细在 `runs/<run_id>/failure_feedback/failure_updates.jsonl`，每个事件的
  `feedback_processing_seconds`，加总等于 `feedback_total_seconds`。

## 3. Rules / 规则

### 3.1 Do not add these together / 不能相加的字段

- **`runtime_seconds` + D's localization fields.** For D, `runtime_seconds`
  already includes the initial ranking and the failure updates (see section 4).
  Adding them counts D's overhead twice.<br>
  **`runtime_seconds` 与 D 的定位字段。** 对 D 来说，`runtime_seconds` 已经包含初始排名和报错更新（见
  第 4 节），再相加会把 D 的开销算两次。
- **`index_load_seconds` from both ranking files** (section 2).<br>
  **两个排名文件里的 `index_load_seconds`**（见第 2 节）。
- **`index_build_seconds` in more than one place.** The value in every
  ranking file is the same number, the index's `metadata.build_seconds`.<br>
  **多处的 `index_build_seconds`。** 每个排名文件里的值都是同一个数，即索引的 `metadata.build_seconds`。

### 3.2 B and C rankings are computed once per task / B、C 的排名每个任务只算一次

B and C read precomputed rankings, so their T_loc is a per-task cost. All runs
of a task (including repeats) use the same ranking; attribute the same T_loc
to each of them rather than dividing it. D recomputes its ranking in every
run, so its T_loc is genuinely per run.

B、C 读取预先算好的排名，所以它们的 T_loc 是每个任务的成本。同一任务的所有运行（包括重复运行）
都使用同一份排名；每次运行都计入同样的 T_loc，而不是分摊。D 每次运行都重新计算排名，所以它的
T_loc 确实是每次运行的成本。

### 3.3 Measure on the machine that runs the agent / 在运行 Agent 的机器上测量

T_loc and T_agent must come from the same machine. Every ranking file
records `timing.measured_on`; regenerate the three ranking files on the
server before reporting:

T_loc 和 T_agent 必须来自同一台机器。每个排名文件都记录了 `timing.measured_on`；报告前在服务器上重新
生成三个排名文件：

```bash
PYTHONPATH=. python scripts/run_bm25_batch.py
python scripts/run_structural.py --lexical experiments/bm25_results.json -o experiments/structural_results.json
PYTHONPATH=. python scripts/run_rrf.py
```

Rankings do not change; only the timing does. No agent runs are needed.

排名不会改变，只有计时会变。不需要重跑 Agent。

### 3.4 Reporting / 报告方式

- Report per-task values and the median with range; with 1–3 runs per
  combination, means are dominated by single slow runs.<br>
  报告每个任务的值，以及中位数和范围；每个组合只有 1–3 次运行时，平均值会被个别慢的运行主导。
- Times below 0.01 s (structural ranking, RRF) are reported as "< 0.01 s",
  not rounded to 0, to show they were measured.<br>
  小于 0.01 秒的时间（结构排名、RRF）写作"< 0.01 秒"，不要四舍五入成 0，以表明确实测量过。
- Missing values are missing, not zero (protocol section 2.3).<br>
  缺失值就是缺失，不能当作 0（协议 2.3 节）。

### 3.5 Superseded field / 已被取代的字段

`config.failure_feedback.localization_overhead_seconds` (D) covers the
initial ranking and failure parsing but not the fusion and context injection
before the next model call. It is kept because the first development batch
(dev5) recorded only this field, but it is **not used for reporting**; use
`initial_localization_seconds + feedback_total_seconds`.

D 的 `config.failure_feedback.localization_overhead_seconds` 覆盖了初始排名和报错解析，但没有包含下一次
调用模型前的融合和提示注入。因为第一批开发实验（dev5）只记录了这个字段，所以保留它，但**不用于
报告**；请用 `initial_localization_seconds + feedback_total_seconds`。

## 4. Known gap: T_agent and T_env are not separated yet / 已知缺口：T_agent 和 T_env 尚未分开

The run record's `runtime_seconds` spans, in order:

运行记录中的 `runtime_seconds` 依次覆盖：

1. building the agent and **starting the Docker container**;<br>
   构建 Agent 并**启动 Docker 容器**；
2. for D only, the **initial ranking** (container snapshot, index, BM25,
   structural ranking, RRF);<br>
   仅 D：**初始排名**（读取容器快照、建索引、BM25、结构排名、RRF）；
3. `agent.run()`, which for D also contains the failure updates;<br>
   `agent.run()`，对 D 来说还包含报错更新；
4. closing the environment.<br>
   关闭环境。

So `runtime_seconds` is **not** T_agent, and is not comparable across
conditions as is: D's includes its localization overhead, B's and C's do not,
and every condition's includes container start-up, which varies (dev5 had six
start-up timeouts).

因此 `runtime_seconds` **不是** T_agent，也不能直接跨条件比较：D 的包含了它的定位开销，B、C 的不包含；
而且所有条件的都包含容器启动时间，这个时间波动很大（dev5 中有 6 次启动超时）。

**Fix (PR #17):** each run record gets `config.timing`:

**修复（PR #17）：** 每条运行记录新增 `config.timing`：

| Field / 字段 | Covers / 覆盖范围 |
|---|---|
| `env_setup_seconds` | building the agent and starting the container; recorded even if start-up fails<br>构建 Agent 并启动容器；启动失败时也会记录 |
| `agent_seconds` | `agent.run()` only; for D it includes the failure updates<br>只含 `agent.run()`；D 的报错更新也在其中 |
| `env_teardown_seconds` | closing D's logs and cleaning up the environment<br>关闭 D 的日志并清理环境 |

With these fields / 使用这些字段时：

- **T_agent** = `agent_seconds` for A, B, C; `agent_seconds − failure_feedback.feedback_total_seconds` for D.<br>
  **T_agent**：A、B、C 为 `agent_seconds`；D 为 `agent_seconds − failure_feedback.feedback_total_seconds`。
- **T_env** = `env_setup_seconds + env_teardown_seconds`.<br>
  **T_env** = `env_setup_seconds + env_teardown_seconds`。
- `runtime_seconds` is unchanged and remains the total wall time.<br>
  `runtime_seconds` 不变，仍是总耗时。

**For runs recorded before PR #17** (e.g. dev5), which lack `config.timing`:
report `runtime_seconds` labelled as "run time including container
start-up", and for D subtract
`initial_localization_seconds + feedback_total_seconds` before comparing with
the other conditions. State this approximation in the report.

**PR #17 之前记录的运行**（例如 dev5）没有 `config.timing`：把 `runtime_seconds` 标注为"含容器启动的运行
时间"来报告；D 在与其他条件比较前，先减去 `initial_localization_seconds + feedback_total_seconds`。在报告
中说明这一近似处理。

T_eval is not recorded by the runner; the evaluation lead measures it around
the harness call.

T_eval 不由运行器记录，由评估负责人在调用官方评测前后测量。

## 5. Field reference / 字段对照

| Field / 字段 | Where / 位置 | Measures / 测量内容 | Used for / 用于 |
|---|---|---|---|
| `metadata.build_seconds` | index JSON / 索引 JSON | reading files and indexing, no clone or save / 读取文件并建索引，不含 clone 和保存 | T_pre |
| `timing.index_build_seconds` | all three ranking files / 三个排名文件 | copy of `build_seconds` / `build_seconds` 的副本 | T_pre (take once / 只取一次) |
| `timing.index_load_seconds` | `bm25_results.json` | loading the cached index / 读取缓存索引 | T_loc (B, C) |
| `timing.index_load_seconds` | `structural_results.json` | same operation / 同一操作 | not used / 不使用 |
| `timing.bm25_init_seconds` | `bm25_results.json` | building BM25 statistics / 构建 BM25 统计 | T_loc (B, C) |
| `timing.bm25_seconds` | `bm25_results.json` | BM25 retrieval / BM25 检索 | T_loc (B, C) |
| `timing.structural_seconds` | `structural_results.json` | structural ranking / 结构排名 | T_loc (C) |
| `timing.rrf_seconds` | `condition_c_results.json` | RRF fusion / RRF 融合 | T_loc (C) |
| `timing.measured_on` | all ranking files / 所有排名文件 | platform, Python version / 平台和 Python 版本 | check 3.3 / 核对 3.3 |
| `config.failure_feedback.initial_localization_seconds` | D run record / D 运行记录 | D's initial ranking, incl. index build / D 的初始排名，含建索引 | T_loc (D) |
| `config.failure_feedback.feedback_total_seconds` | D run record / D 运行记录 | all failure updates / 所有报错更新 | T_loc (D) |
| `feedback_processing_seconds` | `failure_updates.jsonl` | one failure update / 单次报错更新 | detail / 明细 |
| `config.failure_feedback.localization_overhead_seconds` | D run record / D 运行记录 | partial D overhead / D 的部分开销 | superseded (3.5) / 已取代 |
| `config.timing.env_setup_seconds` | run record (PR #17) / 运行记录 | agent build + container start / 构建 Agent + 启动容器 | T_env |
| `config.timing.agent_seconds` | run record (PR #17) / 运行记录 | `agent.run()` (D: incl. failure updates) / 含 D 的报错更新 | T_agent (section 4) |
| `config.timing.env_teardown_seconds` | run record (PR #17) / 运行记录 | cleanup / 清理 | T_env |
| `runtime_seconds` | run record / 运行记录 | container + (D) ranking + agent / 容器 + （D）排名 + Agent | total; see section 4 / 总耗时，见第 4 节 |

## 6. Measured magnitudes / 实测量级

Development set, 20 tasks, Windows laptop (re-measure on the server):

开发集 20 个任务，Windows 笔记本（需在服务器上重新测量）：

| Step / 步骤 | Time / 耗时 |
|---|---|
| index build (T_pre) / 建索引 | 0.4–13 s（sympy 10–13 s） |
| index load / 读索引 | 0.04–0.5 s |
| structural ranking / 结构排名 | 0.4–4 ms |
| RRF | 0.1–2 ms |

For comparison, one real C run of pytest-7571 took 15 s in total, so
localization overhead is not negligible for easy tasks, but the structural
ranking and RRF themselves are.

作为对比，pytest-7571 的一次真实 C 条件运行总共用时 15 秒，所以对简单任务来说定位开销不可忽略；但结构
排名和 RRF 本身的耗时可以忽略。
