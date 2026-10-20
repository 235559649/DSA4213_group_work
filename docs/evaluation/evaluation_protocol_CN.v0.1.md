# Evaluation Protocol_CN.v0.1

中文版详细说明。精简正式英文稿见[Evaluation Protocol.v0.1](<Evaluation Protocol.v0.1.md>)。

版本：讨论稿 v0.1，2026-10-12。

用途：给全组明确“谁提供什么材料，材料包含什么字段，角色5怎样评价”。本文规定建议的数据格式与执行顺序，不代表收集器、统计脚本或正式A–D实验已经完成。需全组确认的规则在文末列出。

依据：当前 proposal 第5.1–5.5节；已约定的“保留原始Issue，提前标注有无定位提示”；本次人工辅助pilot的材料经验。

## 0. 先理解整个过程

你需要的不是一堆互不相关的文件，而是一条可以追溯的证据链：

**同一个任务 → 分别运行A/B/C/D → 保存过程、排名和补丁 → 官方评测 → 角色5计算指标和解释差异。**

| 你要回答的问题 | 主要看什么 |
|---|---|
| 最后修好了没有？ | 最终补丁、官方逐任务报告、测试日志 |
| 定位模块推荐得准不准？ | 候选排名 + 评价侧参考文件集合 |
| 是否减少了探索代价？ | 轨迹事件、API用量、计时记录 |
| 为什么成功或失败？ | 事件时间线、具体动作和观察、补丁、官方结果 |
| 同一任务多跑几次，结果稳不稳定？ | 预先安排的独立重复运行及其统一摘要 |

**文件是原材料或加工结果，字段是文件中的具体信息，指标是根据字段算出的数值。**

例如：`rankings.jsonl`是文件；其中`candidates[].path`和`candidates[].rank`是字段；与参考文件对照后得到的`Hit@5`是指标。

## 1. 完整文件提纲

### 1.1 先约定材料标记

- **必留**：原始证据或可追溯的信息必须保留，允许保留原生文件名并在索引中引用。
- **条件必留**：适用条件下必须有。例如B–D必须留排名，A不适用。
- **派生**：角色5在运行后从原材料提取或计算；不要求组员人工重复填写。
- **建议**：便于审计与复核，但不单独形成成绩指标。

下面是逻辑上完整的材料结构。字段可以合并进已有文件；不要求把原生文件改名、复制成一套完全相同的目录。最终材料保存在实验归档端，不把整个归档目录挂载给Agent。

### 1.2 实验归档目录

```text
experiments/<experiment_id>/
  README.md                         # 建议：材料索引、来源与访问说明
  protocol.json                     # 必留：全组冻结的比较与评分规则
  task_manifest.jsonl               # 必留：每行一个任务及其标注
  task_statements/<task_id>.txt      # 必留信息：原始Issue，也可引用固定快照
  run_plan.jsonl                    # 必留：计划运行哪些任务/条件/独立重复

  runs/<run_id>/
    manifest.json                   # 必留：运行身份、版本、状态、材料路径
    effective_config.json           # 必留信息：实际生效设置，可引用轨迹
    trajectory.json                 # 必留：原始输入、动作、观察与错误
    usage.jsonl                     # 必留信息：逐调用用量，可从完整轨迹提取
    timings.json                    # 必留信息：运行计时及模块开销
    events.jsonl                    # 派生/补采集：标准化行为与证据位置
    rankings.jsonl                  # 条件必留：B–D候选排名快照
    failure_updates.jsonl           # 条件必留：D失败是否可用、重排关联
    patch.diff                      # 有补丁必留；无补丁在manifest中说明
    predictions.jsonl               # 建议归档：实际送给Harness的输入
    intervention_log.jsonl          # 条件必留：发生的人工干预、协议偏离
    evaluation/
      report.json                   # 必留：该运行的官方逐任务结果
      test_output.txt               # 必留：官方测试原始输出
      run_instance.log              # 必留：应用补丁、执行与错误日志
      aggregate_report.json         # 有则归档：原生批次汇总，可引用公共文件
    summary.json                    # 派生：一次运行的统一结果与指标
    hashes.json                     # 建议：原始证据的校验值

  analysis/
    run_summary.csv                 # 派生：每次运行一行，全部条件统一汇总
    paired_comparisons.csv          # 派生：同任务同重复的条件差异
    localization_scores.csv         # 派生：初始排名与D前后排名的定位分数
    trajectory_labels.jsonl         # 派生/人工：轨迹原因分类与证据
    variability.csv                 # 派生：重复运行结果、均值与波动
    cases.md                        # 派生/人工：代表案例，可并入最终报告
    final_report.md                 # 派生：五个模块结论、覆盖与限制
```

评价侧还需要以下材料，**保存在Agent与在线定位模块无法访问的位置**：

```text
<隔离的评价侧存储>/<experiment_id>/
  reference_manifest.jsonl          # 参考补丁来源、数据集revision、提取规则版本
  reference_patches/<task_id>.diff  # 参考补丁，或能精确定位原件的受控引用
  gold_locations.jsonl             # 从参考补丁提取的文件/函数评价目标
```

“隔离”靠访问控制或不挂载来实现，不能仅靠给文件夹起一个private名字。

### 1.3 原始材料与最后提交的报告有什么关系？

原始轨迹、排名、补丁、官方报告等是需要留存的证据；`analysis/`中是角色5生成的比较结果。最终项目报告不必贴出全部原始日志，但每个结论应能通过`run_id`和证据索引找到原件。

当前这轮提交本说明及空白字段约定，用pilot举例即可；完整A–D排名、比较表与波动结果需要后续正式运行才能产生。

## 2. 按“来源 → 文件 → 分支字段”理解材料

### 2.1 一张来源总览

| 来源 | 文件/分支 | 必要信息 | 提供时间与负责人 |
|---|---|---|---|
| 全组实验约定 | protocol、run_plan | 条件定义、任务与重复安排、预算、异常与评分规则 | 正式运行前；全组确认，角色5维护 |
| 数据集与任务选择 | task_manifest、原始题目 | 任务身份、原始Issue、代码版本、有无定位提示 | 运行前；任务/环境负责人和角色5 |
| Agent运行器 | manifest、配置、trajectory、usage、timings、patch | 实际设置、动作观察、资源、停止原因、最终提交 | 启动/运行/结束；角色1与运行者 |
| 结构与检索模块 | rankings及索引记录 | 候选顺序、文件/函数身份、索引版本、送入Agent的内容 | 首次给出推荐时；角色2/3 |
| 失败反馈模块 | failure_updates、更新后的rankings | 失败来源、可用性、触发状态、前后快照 | 发生失败和更新时；角色4 |
| 官方Harness | evaluation目录 | 补丁应用、resolved、测试分组与异常 | 评测结束；评测执行者 |
| 隔离评价侧 | reference_manifest、gold_locations | 用作定位评分的参考集合与提取依据 | 事后评分前；角色5/评价脚本 |
| 角色5分析 | events、summary、比较表、labels、报告 | 派生指标、分类证据、配对差异、解释 | 材料验收后；角色5 |

### 2.2 所有材料怎样对上同一次运行？

| 字段 | 含义 | 使用位置 |
|---|---|---|
| `experiment_id` | 一次冻结实验的编号 | 协议、任务/运行计划、报告 |
| `task_id` | 数据集任务ID | 任务、运行、排名、参考集合、评价结果 |
| `condition` | A/B/C/D；开发人工辅助另用`human_assisted_pilot` | 运行及汇总 |
| `repeat_id` | 预先安排的独立重复编号 | 运行计划、配对、波动分析 |
| `attempt_id` | 同一计划运行因允许的技术故障重试的尝试编号 | 运行与审计 |
| `run_id` | 一次实际运行的唯一编号 | 关联该运行的全部材料 |
| `protocol_version` | 本次按哪版规则执行 | 运行、评分与报告 |
| `evidence_ref` | 原始文件与消息/事件位置 | 事件、分类、摘要中的重要结论 |

逻辑主键为`task_id × condition × repeat_id × attempt_id`。一轮中模型调用很多次，不等于做了很多次独立实验。技术故障重试也不等于增加了一次独立重复。

以下字段是建议的标准化命名，不保证原生工具使用同名字段。适配时保留原生名称和来源映射，例如Harness输入的`instance_id`对应本组的`task_id`。

### 2.3 来源一：共同规则与任务信息

#### A. `protocol.json`：规则按分支组织

| 字段分支 | 必要子字段/信息 | 为什么需要 |
|---|---|---|
| 身份 | `experiment_id`、`protocol_version`、`frozen_at` | 确认规则何时冻结 |
| 条件 | `conditions`：A原始、B词法、C结构融合、D失败重排 | 确认方法差异 |
| 控制变量 | `model_config_ref`、`base_prompt_ref`、`environment_ref`、`network_policy` | 确认条件间共同设置 |
| 预算 | `budgets.step_limit`、`total_token_limit`、`cost_limit`、`agent_wall_limit`、`command_timeout`、`harness_timeout` | 各类时限含义不同；明确数值或明确关闭 |
| 执行状态 | `budget_enforcement` | 哪些限制已由程序实施，哪些只是计划 |
| 运行安排 | `main_repeat_id`、`repeat_plan`、`retry_policy`、`attempt_selection_rule` | 主实验与重复、技术重试不混淆 |
| 评分 | `repair_rule`、`infra_policy`、`localization_scope`、`path_mapping_rule`、`inspection_rule` | 明确分母、异常处理、文件映射及“查看”的口径 |
| D更新 | `usable_failure_rule`、`update_rule` | 在线可见证据决定更新，不使用参考答案 |
| 分组 | `hint_annotation_rule`、`subgroups` | 全部任务、有提示、无提示；可补仓库分组 |

预算字段不能只填写一个`max_tokens`：单次输出上限、全程累计Token、单条命令时限、整次Agent时限、官方评测时限分别记录。

#### B. `task_manifest.jsonl`：每行一个任务

| 字段分支 | 必要字段 | 解释 |
|---|---|---|
| 身份与版本 | `task_id`、`dataset_id`、`dataset_revision`、`split`、`repo`、`base_commit` | 不同仓库版本不能当成同一任务比较 |
| 原始输入 | `problem_statement_ref`、`problem_statement_hash` | 指向完整原始Issue或固定快照，不能只留task ID |
| 提示标注 | `has_localization_hint`：yes/no；`annotation_basis`；`annotated_at` | 运行前标注；依据是Issue原文短摘录；无提示说明核查范围 |
| 实验用途 | `experiment_partition`：development/heldout；`in_repeat_subset` | benchmark的split与本组开发/正式划分不是同一字段 |
| 任务范围 | `repair_eligible`、`eligibility_reason` | 按预先规则确定是否纳入修复评价 |

原始Issue中的公开建议保留；参考补丁、测试标签、真实定位信息不能混进这个给Agent使用的任务输入快照。这里使用此前确认的“有/无提示”，不用旧的H0–H3等级替代。

#### C. `run_plan.jsonl`：每行一次计划运行

必要字段：`task_id`、`condition`、`repeat_id`、`planned_run_key`、`role`（main/repeat）。实际运行通过manifest关联计划项；没有启动的计划项也保留，避免只统计成功生成文件的运行。

### 2.4 来源二：Agent运行器

#### A. `manifest.json`与`effective_config.json`

| 分支 | 必要字段/信息 |
|---|---|
| 运行身份 | 上述公共ID、`planned_run_key`、`started_at`、`ended_at` |
| 实际版本 | `agent_version`、`agent_code_revision`、`model_provider`、`model_id`、`image_identity`、关键依赖版本 |
| 实际设置 | 生效prompt或其可访问引用、采样/思考配置、工具、预算、网络策略；移除密钥 |
| 停止 | `termination_reason`、`budget_exhausted`、`run_completed` |
| 补丁 | `patch_present`、`patch_ref`、`patch_hash`、`patch_missing_reason` |
| 人工与偏离 | `human_assisted`、`intervention_count`、`protocol_deviation`、`formal_eligible`、理由 |
| 材料完整性 | `artifact_refs`、`trace_complete`、`usage_complete`、`collection_errors` |

完整有效配置已在轨迹里时，可以直接引用；只留一个无法取回原文的hash不够。预算中途调整不能覆盖成一个看起来始终一致的最终配置，必须保留变更记录。

#### B. `trajectory.json`：保留原生结构

不强制改写原件；至少能够追溯：消息顺序、角色、内容、模型响应、请求或调用ID、工具命令、工具观察、退出/超时状态、错误与最终提交。时间和usage若原生缺失，要由运行器另行采集。

失败或被截断的模型响应也保留。有些错误响应不在常规assistant消息下，统计时不能只按消息角色筛选。提出了命令、执行了命令、命令执行成功，是三个不同状态。

#### C. `usage.jsonl`：每行一次API调用

| 分支 | 必要字段 | 解释 |
|---|---|---|
| 关联 | `run_id`、`call_id`、`query_step`、`component`、`evidence_ref` | component区分Agent与额外定位模型调用；不重复计同一次调用 |
| 用量 | `input_tokens`、`output_tokens`、`cached_input_tokens`、`usage_status` | 缓存输入是输入子集；缺失usage不能填0 |
| 状态 | `finish_reason`、`error_type`、`retry_of_call_id` | 错误调用可能仍有用量；SDK重试需单独捕获 |
| 费用 | `estimated_cost`、`currency`、`pricing_basis`；账单已核对才填`billed_cost` | 估算和实付分开，标明价格依据 |

总Token按输入+输出累计，已包含在输出中的推理Token不再另加。索引/重排若另外调用模型，同样记入对应运行成本。

#### D. `timings.json`：计时及方法开销

必要字段：`run_id`、`agent_wall_seconds`、`human_wait_seconds`、`setup_seconds`、`indexing_seconds`、`ranking_seconds`、`harness_seconds`、`timing_scope`、`measurement_status`。

`agent_wall_seconds`应从本次任务方法开始工作（包含任务相关索引与初始排序）到修复停止；Harness耗时分列。预构建共享索引需要报告建设成本与是否计入/分摊的规则。分阶段耗时可能重叠，不应再次相加到已经覆盖这些阶段的总墙钟时间上。

#### E. `events.jsonl`：把原始过程整理成统一事件

| 分支 | 必要字段 | 示例含义 |
|---|---|---|
| 身份与顺序 | `event_id`、`run_id`、`query_step`、`action_id`、`timestamp` | 一次模型响应可能提出多个动作，action_id区分它们 |
| 行为 | `event_type` | path_discovered、source_content_seen、edit、test、rerank、submit、stop |
| 对象与内容 | `paths`、`content_kind`、`content_ref`、`workspace_state_ref` | 实际看到哪个版本的哪些内容 |
| 执行结果 | `execution_status`、`exit_code`、`timed_out`、`test_result_status` | 未执行、成功、失败、超时分别记录；测试结果不能只看管道最后一项 |
| 取证 | `evidence_ref`、`extraction_method`、`confidence`、`parser_version` | 从哪条消息提取；不确定内容待核查 |

建议的“查看源码”口径：Agent实际收到可归属某个文件的源码内容才算；仅列出文件路径不算。打开文件、带源码行的搜索结果、定位模块送入上下文的源码片段分别标记。无输出、仅traceback路径或模块后台读取但没有给Agent看的内容，不当作Agent已经查看。

这项细则需开发阶段确认后冻结。初始定位上下文若含源码，在首个模型查询前记`query_step=0`；查询从1计数。只给文件名则不算查看。事件必须证明内容已进入Agent可见上下文，不能根据模块读取了文件就推定。

#### F. 补丁、送评与干预

- `patch.diff`保存Agent最终补丁；修改文件列表可从diff自动提取。它用于描述修复，不作定位评分的正确答案。
- `predictions.jsonl`保留实际送评记录中的任务ID、模型标识、补丁，并关联到`run_id`和补丁hash。空补丁按状态处理，不造假文件。
- `intervention_log.jsonl`每条记录`intervention_id`、`run_id`、`timestamp/query_step`、`type`、`content`、`reason`、`evidence_ref`；例如拒绝命令、给出技术提示、续预算、修改配置。确认没有干预可在manifest记0；未监测不能直接声称0次。

### 2.5 来源三：定位与失败反馈模块

#### A. `rankings.jsonl`：每行一份排名快照

| 分支 | 必要字段 | 用途 |
|---|---|---|
| 快照身份 | `snapshot_id`、`run_id`、`stage`、`created_at`、`query_step` | stage为initial/pre_update/post_update；初始快照在首条Agent命令之前 |
| 方法来源 | `method_version`、`index_ref`、`base_commit`、`parameters_ref` | 复核是哪个索引与算法输出 |
| 候选列表 | `candidates[].path`、`rank`；算法有分数时留`score` | 文件路径相对仓库根；顺序明确，文件去重规则固定 |
| 范围 | `ranking_complete`、`candidate_count`、`saved_depth`、`candidate_universe_ref` | 判断是否只保存了前几名，避免算错MRR |
| Agent可见内容 | `agent_context_ref`、`shown_depth`、`delivered_event_id` | 保存实际给Agent的列表/源码片段；完整内部排名与送入上下文的内容分开 |
| 重排关联 | `update_id`、`trigger_event_id` | D快照与触发失败对应；初始排名可为空 |

Function Hit@5需要额外保存真实的函数候选列表：函数稳定ID、仓库路径、原版本行号范围、函数排名及索引来源。只有文件列表时，不能凭文件顺序编造函数排名。

为复核建议保留算法产出的完整文件排名。若只保存top-5，仍可算Hit@5和Recall@5；但第5名后是否命中未知，不能把它当成完整MRR的未命中0。若方法本来只输出有限列表，应提前定义为截断指标并标注范围。

#### B. `failure_updates.jsonl`：D失败与更新记录

必要字段分支：

- 来源：`run_id`、`failure_id`、`trigger_event_id`、`query_step`、`failure_evidence_ref`、`workspace_state_ref`。
- 判断：`usable`、`eligibility_reason`、`mapping_status`、`rule_version`。
- 更新：`update_id`、`update_status`、`before_snapshot_id`、`after_snapshot_id`、`no_update_reason`。

须能从记录顺序识别**第一次可用失败**。该失败后若更新失败，也要保留状态，不能跳过它、挑选后面第一次有改善的更新作为主分析。没有失败、失败不可用、更新失败、运行先结束分别统计。

排名“无变化”也要留下快照或明确复用同一快照的记录；它是一次有效结果，不是缺失。

### 2.6 来源四：官方Harness

保留原生`report.json`、`test_output.txt`、`run_instance.log`；在summary中适配成统一字段，不直接改写官方报告。

| 分支 | 统一提取字段 | 判断什么 |
|---|---|---|
| 关联 | `eval_run_id`、`task_id`、`run_id`、`evaluated_patch_hash`、`harness_version` | 评测的是不是该次提交的补丁 |
| 执行状态 | `evaluation_status`：not_run/completed/error；`error_reason` | 没跑、已完成与执行失败分别记录 |
| 应用结果 | `patch_applied` | 是否成功应用；未知为null |
| 修复结果 | `official_resolved` | 保留官方原始结论；无可用结果为null |
| 测试组 | `f2p_pass`、`f2p_total`、`p2p_pass`、`p2p_total`、各组原始测试列表引用 | 修复与回归分别怎样 |
| 证据 | `report_ref`、`test_output_ref`、`run_log_ref` | 可回到原始报告复核 |

`analysis_success`是角色5按冻结协议判定的分析结果，和`official_resolved`分列。例如预算耗尽按当前proposal计未解决，即使没有官方结果，也可按规则令analysis_success=0；不能因此把official_resolved伪填为false。

### 2.7 来源五：隔离评价侧的定位标准

`gold_locations.jsonl`每行一个任务，建议分支如下：

| 分支 | 必要字段 | 含义 |
|---|---|---|
| 来源 | `task_id`、`base_commit`、`dataset_revision`、`reference_patch_ref/hash`、`extractor_version` | 标准来自哪份参考补丁 |
| 文件 | `included_paths`、`excluded_paths_with_reasons`、`path_mapping` | 纳入Python源码，排除测试、文档、生成文件；路径映射可追溯 |
| 适用性 | `file_loc_status`、`ineligible_reason` | eligible/not_applicable/pending_rule等明确状态 |
| 函数 | `function_targets`、`function_mapping_status`、`ast_index_ref` | 仅无歧义地映射到初始版本AST时评价 |

文件标准可由评价脚本自动提取。新增文件、删除文件、重命名文件和无法对应原始AST的修改，应按运行前确定的映射/适用规则处理，保留原始变化类型；不得为了提高分数临时删除难评分目标。

参考集合不是Agent最终修改文件集合。替代正确修法可能不修改参考文件，因此定位成绩和官方修复结果要同时解释。

### 2.8 来源六：角色5的汇总和分类

`summary.json`及`run_summary.csv`应至少按以下分支组织，具体取值由后面五个模块生成：

| 分支 | 字段内容 |
|---|---|
| 身份 | 公共ID、任务分组、正式实验资格、所用规则版本 |
| 覆盖与异常 | 各材料是否完整、各指标状态、缺失/不适用原因 |
| 修复 | official_resolved、analysis_success、patch_applied、F2P/P2P计数 |
| 定位 | 初始Hit@1/5、Recall@5、RR；D更新前后指标、触发状态 |
| 效率 | 源码查看数、首次命中、Token、时间、实际命令数、费用 |
| 轨迹 | 主因分类、次要标签、分类证据引用 |
| 证据 | 原始文件和派生记录路径、分析程序版本 |

数值字段用null配合状态区分`missing`、`not_applicable`、`not_run`、`incomplete`；真实0保留为0。CSV里建议同样有`metric_status`/理由列，避免空白单元格含义不明。

## 3. 分模块怎样执行评价

### 3.1 修复成功：A/B/C/D都评价

**材料路径：** run_plan + manifest + patch + evaluation报告/日志 → summary → 条件比较表。

**关键字段：** task_id、condition、repeat_id、attempt_id、termination_reason、budget_exhausted、patch_present、patch_applied、evaluation_status、official_resolved、F2P/P2P计数。

执行步骤：

1. 对照run_plan，确认计划中的运行都有记录，包括未启动、失败、超时、未提交。
2. 按预先重试政策选定同一计划运行的有效attempt，其他尝试保留；不挑最好成绩。
3. 核对提交补丁和送评补丁的hash，确认官方报告属于该任务和本次提交。
4. 原样提取official_resolved，再按协议生成analysis_success。当前proposal规定无补丁、不可应用或预算耗尽计未解决。
5. 基础设施错误先标error/pending；按预定规则重试或核定。尚未核定时报告已确认成功数/N和待定数量，不把临时比例称为最终完成实验的解决率。
6. 核定后按相同任务集合汇总A–D。排除任务须预先有规则并披露，不能仅删除失败条件的记录。

指标：

- 任务解决率 = 按协议成功的计划运行数 / 对应条件纳入的计划运行数。
- 补丁应用率 = 应用成功数 / 相同约定分母；未送评、应用未知数量另外列明。
- 单任务F2P通过比例 = f2p_pass / f2p_total；P2P同理。分母0时该描述性比例不适用，不改写官方resolved。
- 先算每任务比例再平均是任务宏平均；把所有测试数相加再除是测试微平均，两者不能混用。

输出：`run_summary.csv`修复列、A–D总体表，以及A成功/D失败、A失败/D成功、都成功、都失败四格表。B–A、C–B、D–C用于分析组件增量。

### 3.2 定位表现：B/C/D评分，A的显式排名不适用

**材料路径：** rankings + failure_updates + 隔离侧gold_locations → localization_scores → 条件比较表。

**关键字段：** task_id、base_commit、stage、snapshot_id、candidates.path/rank、ranking_complete、saved_depth、included_paths、file_loc_status、before/after_snapshot_id、usable、update_status。

执行步骤：

1. 验证候选与参考集合属于同一任务和base commit，统一相对路径格式并按冻结规则去重。
2. 取Agent首个命令之前的initial快照。B/C/D初始排名分别评分；不能用最终排名替代初始排名。
3. 读取评价侧标准文件集合G，按照已冻结的纳入/路径映射规则确认是否适用。
4. 对每份适用排名计算下列指标；记录材料缺失、排名截断与不适用原因。
5. D另取第一次可用失败对应的before和after两份快照，以相同G评分并计算差值。
6. 同时报告全部D任务数、产生可用失败数、更新成功数、缺记录数和未触发原因；不只展示改善案例。

| 指标 | 单任务计算 | 汇总 |
|---|---|---|
| File Hit@1 | 第1名属于G为1，否则0 | 对适用且有效记录的任务求平均，报告覆盖 |
| File Hit@5 | 前5名至少一个属于G为1，否则0 | 同上 |
| File Recall@5 | 前5名中属于G的不同文件数 / G的文件数 | 先每任务算，再平均 |
| RR / MRR | 第一个属于G的文件名次为r，则RR=1/r；完整排名未命中为0 | MRR是各任务RR的平均 |
| Function Hit@5 | 前5个真实函数候选是否命中无歧义函数目标 | 仅可映射且有函数排名的子集，报告覆盖 |

参考文件集合为空时，文件定位评分不适用，不填0。预期有排名却丢失文件时属于缺失，不能与A天然没有排名混在一起。应先补救缺失；无法补救要报告覆盖与可能偏差，不能声称定位结果覆盖完整实验。

**小例子：** G={`core/mod.py`}，候选顺序为`core/numbers.py`、`core/mod.py`、`core/mul.py`。则Hit@1=0、Hit@5=1、Recall@5=1、RR=1/2。若D重排把`core/mod.py`放第1，RR差值为1−1/2=0.5。

输出：每快照一行的`localization_scores.csv`、B/C/D初始排名汇总、D第一次可用失败前后变化表。D内部前后变化属于触发任务分析；不能仅凭它宣称相对C的因果提升，C–D主比较仍覆盖原定配对任务。

### 3.3 探索效率：A/B/C/D都比较

**材料路径：** trajectory → events；usage + timings + gold_locations → summary效率列。

**关键字段：** query_step、event_type、paths、content_kind、execution_status、evidence_ref、included_paths、input/output_tokens、agent_wall_seconds、indexing/ranking_seconds、usage_complete、trace_complete。

执行步骤：

1. 按冻结的inspection_rule从轨迹提取实际收到源码内容的事件；仅出现路径不算。先在少量样例人工核对提取结果。
2. 统一文件路径后去重，统计看过的不同Python源码文件数。评价范围与测试/生成文件处理写入规则。
3. 与G对照，找第一次看到相关源码的事件。初始源码上下文在query_step=0；若首个命中来自第s次查询后的观察，命中前模型步骤数为s−1；步0命中则为0。
4. 完整轨迹从未命中时记录`reached_reference=false`、首次命中步骤null；轨迹不完整时记录unknown，不把“没看到记录”当作“从未命中”。
5. 累加所有组件和失败调用的实际usage；统计真正执行的动作，计时范围包含方法开销。
6. 按相同任务和重复配对比较。先报告全体可核定运行的成本，再用“两条件都成功的任务”作补充分析。

| 指标 | 如何计算/报告 | 边界 |
|---|---|---|
| 唯一源码查看文件数 | source_content_seen事件的Python源码路径去重数 | 搜索源码片段、展开文件、定位上下文来源可分列 |
| 到达率 | 完整可评分轨迹中看到G的运行比例 | G不适用、轨迹缺失数量另报 |
| 首次命中前步骤 | 按上面统一query_step口径 | 未命中不设为0、最大步数或其他人为数值 |
| 总Token | sum(input_tokens + output_tokens) | 缺用量不能用已知部分冒充总量；缓存不重复加 |
| 方法总墙钟时间 | 使用规定范围内的agent_wall_seconds | 人工等待单列；索引/排序阶段不重复相加 |
| 实际命令数 | executed状态的工具动作数量 | 一次模型调用不一定只有一个命令 |
| 费用 | 同一价格口径下估算，实付另列 | 不把估算标成账单金额 |

输出：逐运行效率列、条件均值/中位数与覆盖数、A–D及相邻条件的配对差异。仅“更快停止但未解决”不能解释为整体方法更好，需要与修复成绩联合呈现。

### 3.4 轨迹分析分类：用事件和证据解释结果

**材料路径：** events + trajectory + rankings + failure_updates + patch + 官方结果 → trajectory_labels + cases。

**关键字段：** run_id、事件顺序、源码查看证据、编辑/测试结果、停止原因、official_resolved、analysis_success、intervention记录。

执行步骤：

1. 从统一汇总表区分成功、未解决、基础设施异常和结果待定。
2. 对未解决运行按统一分类手册选一个主因；可有多个次要标签。无法确定则unknown。
3. 记录支持判断的event_id、原始消息或日志位置。模型自述“我找到了问题”不能单独证明诊断正确。
4. 对代表性成功和失败案例，串联“收到推荐→看到源码→修改→验证→提交→官方结果”。
5. 模糊案例可由两人先独立标注，再讨论。若报告一致率，使用讨论前结果；只抽样标注时必须报告抽样范围。

| 主因 | 判断依据 | 需要哪些证据 |
|---|---|---|
| F1 未查看相关源码 | 完整可评分轨迹中没有看到G对应源码 | events + gold_locations；属于参考位置代理判断 |
| F2 诊断错误 | 看到了相关源码，但具体诊断/修改与复现证据不符 | 轨迹观察、修改、测试；不能仅凭最后失败下结论 |
| F3 补丁缺失/无效/不完整 | 没有可用提交，或应用/目标修复不完整 | patch、停止原因、应用日志及目标测试 |
| F4 回归/验证不足 | 出现可归属修改的回归，或有证据支持验证环节失效 | 编辑前后测试、官方结果和对应动作 |
| F5 环境/资源限制 | 环境错误或预算限制是直接阻断原因 | 错误日志、计时、预算与停止状态 |
| unknown | 证据不足，或多种解释无法判定 | 标明缺什么证据 |

这些类别可能重叠，主因选择规则需在开发阶段统一。例如直接因为预算耗尽停止，可主记F5，并次记此前反复错误修改；不能为了让分类看起来更好而随条件切换规则。

`trajectory_labels.jsonl`必要字段：run_id、outcome、primary_category、secondary_tags、rationale、evidence_refs、annotator_id、taxonomy_version、review_status；两人标注时分别保存各自原判与协商结果。

成功运行的primary_category记不适用，但可标注“中间回归、重复失败命令、人工介入、测试范围持续扩大”等过程现象。技术故障和人类介入也可独立成审计标签。

输出：失败类型数量/占比及分母、unknown数量、代表案例。若没有覆盖全部未解决运行，只能称“已标注样本的分布”，不能当全体失败分布。

### 3.5 波动性评估：同一任务的独立重复

**材料路径：** protocol.repeat_plan + run_plan + manifest + run_summary → variability + paired_comparisons。

**关键字段：** task_id、condition、repeat_id、attempt_id、role、有效attempt选择、analysis_success、Token/时间、模型与配置一致性。

当前proposal暂定：主实验每任务每条件一次；在预先选定的最多20题子集上，每条件总共3次独立运行，包含主实验那次。数量仍需按开发成本确认，不能把这个暂定安排写成已完成。

执行步骤：

1. 在看正式结果之前确定重复子集、重复次数和执行安排。每次从任务初始状态运行，不能继承上一轮补丁或对话。
2. 保持模型、设置、预算一致。若接口支持seed则记录，不支持写明；固定seed也不保证外部服务绝对确定。
3. 技术重试按attempt政策核定，不用多次重试中最好的一次代替独立重复。
4. 每个task×condition展示全部重复结果，再算平均成功比例、Token/时间均值与标准差或范围。
5. 同任务同repeat_id配对比较各条件。repeat_id是对齐实验安排，不意味着模型使用了相同随机轨迹。
6. 跨任务汇总先每任务计算，再在任务间平均。做置信区间时以任务为抽样单位，保留同任务条件与重复的结构，不能把重复运行当成额外独立任务。

**小例子：** 同一任务A三次为[0,1,0]，D三次为[1,1,0]。A成功比例1/3，D为2/3。应完整报告这两组结果，不能因为两边都至少成功一次就都记为100%。

输出：`variability.csv`逐任务各条件的重复结果与波动，主实验结果和重复子集结果分开。只有一次运行时，波动性填写“尚不能估计”，不能把不同任务之间的难度差异当作同一任务的随机波动。

## 4. 不同任务怎样放到同一张比较表？

### 4.1 先确定每个模块的适用范围

| 任务/运行情况 | 修复表现 | 文件排名 | 探索效率 | 轨迹分类 | 波动 |
|---|---|---|---|---|---|
| A，任务有可评分Python参考文件 | 按官方与协议 | N/A：没有显式排名 | 可算文件数、首次命中与资源 | 可分析 | 有独立重复才可估计 |
| B/C，任务有可评分Python参考文件 | 同上 | 初始排名 | 同上 | 可分析 | 同上 |
| D，有可用失败并重排 | 同上 | 初始 + 第一次可用失败前后 | 同上 | 可分析反馈是否被使用 | 同上 |
| D，未触发可用重排 | 同上 | 初始排名；前后差值N/A并解释原因 | 同上 | 分析未触发原因 | 同上 |
| 无纳入的Python参考文件，但仍属修复任务范围 | 可评价 | N/A，报告排除数 | Token/时间可算；参考首次命中N/A | 可分析可见过程，F1需谨慎 | 有重复可评价修复/成本波动 |
| 函数映射有歧义 | 不受影响 | 文件指标可算；函数指标N/A | 文件/成本仍可算 | 可分析 | 按可用指标 |
| 轨迹丢失或部分用量缺失 | 有官方证据仍可评修复 | 有独立排名可评定位 | 相应指标missing/incomplete | 不做无证据归因 | 只报告可用结果与覆盖 |
| 人工辅助pilot | 报告事实，单列 | 有材料才算 | 报告事实与人工时间限制 | 用于开发分类规则 | 不混入正式自动重复 |

新增、删除、重命名、配置或文档修改都是文件变化类型，不能仅按“改了多少行”给任务难度打分。任务纳入范围和定位映射规则在结果产生前确定；修复评价适用不代表每个定位指标都适用。

### 4.2 再做相同任务的配对

主比较A–D，增量比较A–B、B–C、C–D。先在同任务、同独立重复上算差异，再跨任务汇总。不得用A的简单任务集合对比D的另一组困难任务。

总体先报告所有冻结任务；再按有/无定位提示分组，补充仓库分组和任务数。提示标签在运行前基于原始Issue确定，A–D共享原文和标注。

修复按每任务一个结果汇总；测试数量不同不意味着任务权重应不同。定位按每任务先算Hit/Recall/RR；资源同时列总体和配对差异。小子组优先报告逐任务结果和案例，避免凭少数样例下普遍结论。

## 5. 角色5实际执行顺序

1. **运行前对接口。** 用第2节向角色1–4确认字段、保存时机和样例；冻结协议、任务标注、运行计划。
2. **收材料并验收。** 对齐任务、配置、run_id、补丁与官方报告；列出缺失材料。原件只读保存。
3. **生成标准记录。** 从原生文件提取usage、events、官方结果；候选排名由对应模块直接保存；必要时人工核查抽取。
4. **在评价侧准备定位目标。** 按固定规则提取参考文件/函数集合，保存来源与排除理由。
5. **生成五模块结果。** 修复、定位、效率先形成逐运行表；轨迹分类附证据；有独立重复才做波动。
6. **成对比较并分组。** 主实验与重复子集、人工辅助pilot分开；统计缺失和不适用覆盖。
7. **写报告与材料索引。** 每个主要结论指向具体表格、run_id和原始证据。

计算可由脚本完成；角色5的核心人工工作是确认口径、核查异常、复核分类和解释结果。无需逐行抄录全部轨迹。

## 6. 本轮交接与待确认事项

### 6.1 当前这轮可以交付

- 本说明：完整目录、来源字段、五模块执行流程。
- 材料接口清单：各文件/字段由谁负责，确认是否已保存，提供一份样例。
- 冻结前问题表：已确认、待确认、未实现分别列出。
- 现有pilot作为材料示例：官方结果、轨迹、补丁、usage与人工干预；标明缺少正式定位评分和独立重复。

### 6.2 正式运行前必须确认

| 事项 | 需要作出的决定 |
|---|---|
| 任务与重复 | 最终开发/正式任务数、重复子集、每条件次数、主重复编号 |
| 预算与执行 | 模型/版本、全程Token/成本/时间、命令时限、总预算实际执行方式 |
| 失败处理 | 什么允许技术重试、怎样选择有效attempt、基础设施错误是否排除及怎样报告 |
| 排名接口 | 是否保存完整排序、实际送给Agent的内容、D第一次可用失败的识别和更新状态 |
| 探索口径 | 搜索源码片段、初始源码上下文、测试文件、代码查看事件怎样计入 |
| 定位范围 | 新增/删除/重命名如何对应原始路径；函数映射和无法评分任务怎样处理 |
| 人工分类 | F1–F5边界与主因优先规则、标注样本、复核方式 |

### 6.3 本说明的实现状态

已完成的是文档约定和已有pilot分析经验整理。当前通用评价脚本、排名日志接口、累计预算控制是否可用，需要按上表逐项验收；不能因为文件提纲写了某个名称，就认为系统已自动生成该材料。

材料方案建议进入小组仓库供协作确认；未脱敏轨迹和受控参考材料另行归档。本次仅整理本地说明，不上传GitHub、不启动新的Agent或评测。

## 7. 依据与相关材料

- [当前proposal源文件](../../DSA4213_group_work/docs/proposal/DSA4213_proposal/main.tex)：第5.1–5.5节规定修复、定位、效率、轨迹和波动评价；第5.2节限制参考资料仅供离线评价。
- [角色5记录与交接指南](04_角色5的记录比较与交接.md)：原有字段、职责、pilot记录与指标解释。
- [本次pilot摘要](analysis/pilot_summary.json)：已整理的真实结果与未知值；不是正式A–D基线。

字段名、目录扩充、事件提取细则和待确认项属于本说明提出的实现建议；不能视为已冻结的proposal更改。
