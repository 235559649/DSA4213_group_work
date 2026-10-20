# Evaluation Protocol.v0.1

**Status:** Draft for team review. **Date:** 12 October 2026.

This protocol specifies evidence handover, required fields, and evaluation procedures for four conditions: **A**, the original agent; **B**, lexical localization; **C**, lexical and structural localization; and **D**, Condition C with failure-driven reranking. A–D is the primary comparison; A–B, B–C, and C–D assess incremental contributions. This document specifies requirements and does not certify that collection or analysis tooling is implemented.

## 1. Evidence Handover Requirements

### 1.1 Archive Structure

An `experiment_id` identifies a study with a fixed protocol and task set. Development and held-out studies should use separate IDs. Each `run_id` identifies one actual execution of a task, condition, and independent repeat, with a separate attempt number for permitted technical retries. Each experiment has one shared `analysis/` directory.

Native filenames may be retained if an artifact index provides equivalent references. Configuration, usage, and events may be extracted from complete native records rather than duplicated manually.

```text
experiments/<experiment_id>/
  protocol.json                     # Common rules and evaluation policies
  task_manifest.jsonl               # Task identity, versions, and hint annotation
  task_statements/<task_id>.txt      # Original task statement or fixed snapshot
  run_plan.jsonl                    # Planned tasks, conditions, and repeats
  runs/<run_id>/
    manifest.json                   # Run identity, status, and artifact references
    effective_config.json           # Effective settings; may reference trajectory
    trajectory.json                 # Original messages, actions, and observations
    usage.jsonl                     # Per-call usage; may be extracted
    timings.json                    # Run duration and method overhead
    events.jsonl                    # Standardized events, extracted or instrumented
    rankings.jsonl                  # Required for B–D
    failure_updates.jsonl           # Required for D
    patch.diff                      # Final patch, if produced
    predictions.jsonl               # Submitted Harness input
    intervention_log.jsonl          # Human interventions and protocol deviations
    evaluation/
      report.json                   # Official per-instance result
      test_output.txt               # Official test output
      run_instance.log              # Patch application and execution log
      aggregate_report.json         # Batch report, where available
    summary.json                    # Derived per-run results
    hashes.json                     # Recommended evidence checksums
  analysis/
    run_summary.csv                 # All runs, including failures
    paired_comparisons.csv          # Within-task condition differences
    localization_scores.csv         # Initial and D pre/post ranking scores
    trajectory_labels.jsonl         # Failure labels and evidence references
    variability.csv                 # Independent-repeat results
    cases.md                        # Representative cases
    final_report.md                 # Consolidated findings and limitations
```

The evaluator additionally retains `reference_manifest.jsonl`, reference patches or exact source references, and `gold_locations.jsonl` in storage inaccessible to the agent and online localization modules. Reference locations and benchmark test labels must not be supplied as agent inputs.

### 1.2 Ownership and Timing

| Source / owner | Required handover | Timing |
|---|---|---|
| Team and evaluation lead | Protocol, task annotations, run plan, scoring and retry policies | Before held-out execution |
| Environment and execution owner | Effective configuration, versions, trajectory, usage, timings, final patch, termination and intervention records | At startup, during execution, and at termination |
| Structural and retrieval owners | Index identity, initial candidate rankings, and context actually delivered to the agent | Before the first agent command |
| Failure-feedback owner | Failure evidence, usability decisions, update status, and linked pre/post ranking snapshots | At each relevant failure/update |
| Harness operator | Per-instance report, test output, execution log, and evaluated patch identity | After evaluation |
| Evaluation lead | Reference targets, standardized summaries, paired comparisons, labels, and report | During post-hoc analysis |

All A–D conditions must share task statements, base commits, model configuration, base prompts, environment, tool/network policies, and resource limits, except for the prescribed localization context. Freeze these settings, task eligibility, independent repeats, technical-retry rules, and infrastructure-failure handling before inspecting held-out results.

Retain unsuccessful runs. If a patch is absent, record the reason. If no intervention or D update occurs, record an explicit status; an empty or missing file alone is insufficient evidence.

## 2. Required Fields

### 2.1 Identification and Common Records

| Source → file | Required fields / branches |
|---|---|
| Common rules → `protocol` | `experiment_id`, `protocol_version`, freeze time; condition definitions; shared model/prompt/environment references; step, total-token, cost, agent-wall, command and Harness limits; enforcement status; retry/attempt selection, infrastructure, inspection, localization and repeat policies |
| Dataset → `task_manifest` | `task_id`, dataset ID/revision, dataset `split`, `experiment_partition` (development/heldout), `repo`, `base_commit`, original statement reference/hash, `has_localization_hint` (yes/no), original-text `annotation_basis`, repair eligibility and reason |
| Run plan → `run_plan` | `planned_run_key`, `task_id`, `condition`, `repeat_id`, role (main/repeat) |
| Runtime → `manifest`, `effective_config` | `run_id`, planned-run key, task/condition/repeat/attempt IDs, protocol version; actual code/model/environment versions and settings; start/end, termination and budget status; patch presence/reference/hash; formal eligibility; intervention/deviation status; artifact references and completeness |

The run key is `task_id × condition × repeat_id × attempt_id`. API calls are not independent repeats. Preserve original Issues and assign hint labels before execution; reference solutions remain evaluation-only. Remove credentials from archived configuration.

### 2.2 Runtime and Localization Records

| Source → file | Required fields / branches |
|---|---|
| Agent → `trajectory` | Original ordered inputs/responses, commands, observations, errors, execution status, and submission; retain native structure and evidence references |
| API adapter → `usage` | `run_id`, `call_id`, model-query step, component, input/output/cached-input tokens, usage status, finish/error reason, retry link, estimated cost/currency/pricing basis; billed cost only when verified |
| Runtime → `timings` | Agent wall time, human waiting, setup, indexing/ranking and Harness times; measurement scope and completeness |
| Extractor/instrumentation → `events` | `event_id`, `run_id`, query step/action ID, type, paths, content provenance, execution/exit/timeout status, workspace-state reference, source evidence, extraction version |
| Localization → `rankings` | Snapshot/run IDs, stage (`initial`, `pre_update`, `post_update`), time/step, method/index/base-commit references; ordered `candidates[].path/rank/score` where applicable; completeness/depth; actual delivered context reference; trigger/update links |
| Failure module → `failure_updates` | Failure/run IDs, trigger event and raw evidence, workspace version, `usable` and reason, mapping status, update status, before/after snapshot IDs, no-update reason |
| Runtime → `patch`, `predictions`, `intervention_log` | Final/submitted patch identity; task and evaluation-run association; intervention time/step, type, content, reason, deviation and evidence |

Record complete algorithm-produced rankings and the context actually shown to the agent separately. Full MRR requires sufficient ranking depth; saving only top-5 cannot establish whether a target appears later. Function scoring additionally requires genuine ranked function candidates and stable identifiers from the original AST.

Count failed calls with available usage. Cached-input tokens are a subset of input tokens. Proposed, executed, and successful actions are distinct. Runtime must include method overhead without double-counting overlapping stage durations; Harness time and human waiting are reported separately.

### 2.3 Evaluation and Derived Records

| Source → file | Required fields / branches |
|---|---|
| Harness → `evaluation` | Evaluation/run/task IDs, evaluated patch hash, Harness version; `evaluation_status`, error reason, `patch_applied`, `official_resolved`; F2P/P2P passed and total counts; raw report/output/log references |
| Isolated evaluator → `gold_locations` | Task/base-commit identity, reference-patch source/hash, extraction-rule version; included/excluded paths and reasons, path mappings, file eligibility; function targets, original-AST reference and mapping status |
| Evaluation lead → `summary`, comparison tables | Run identity, eligibility and data coverage; repair/localization/efficiency scores; D trigger status; classification and evidence references; analysis version |
| Annotators → `trajectory_labels` | Run outcome, primary category, secondary tags, rationale, evidence references, annotator, taxonomy version and review status |

Keep `official_resolved` separate from protocol-adjudicated `analysis_success`. Use explicit statuses for missing, incomplete, not run, and not applicable; do not encode them as zero. Record every derived result's source. Reference targets come from benchmark patches, not agent-generated patches.

## 3. Evaluation Modules

### 3.1 Repair Performance

**Scope:** A–D, on the same eligible planned tasks.

**Inputs and fields:** Run plan, manifest, final/submitted patch, and Harness records; use task/condition/repeat/attempt IDs, termination/budget status, patch presence/application, evaluation status, official resolution, and F2P/P2P counts.

**Procedure:** Verify patch/report correspondence, select attempts under the frozen retry policy, and retain the official result. Apply the protocol's failure rules separately: under the current proposal, missing or unappliable patches and budget exhaustion count as unresolved. Resolve infrastructure cases under the declared policy; report pending/error counts and any exclusions rather than removing them silently.

**Measures:** Resolution rate and patch-application rate over the declared planned-run denominator; F2P/P2P pass fractions where their denominators are nonzero. Distinguish task-macro averages from test-micro averages. Agent-side tests provide intermediate evidence and do not replace Harness results.

**Output:** Per-run scores, condition-level rates and coverage, and paired success tables (both succeed, A only, D only, neither). Incomplete adjudication must be labelled provisional.

### 3.2 Localization Performance

**Scope:** Initial rankings for B–D; A has no explicit-ranking score. D additionally compares snapshots surrounding the first usable runtime failure.

**Inputs and fields:** `rankings`, `failure_updates`, and evaluation-only `gold_locations`; use snapshot stage/identity, candidate paths/ranks/depth, included reference paths, eligibility, failure usability and linked update status.

**Procedure:** Normalize and deduplicate paths under fixed rules. Define G as reference-patch-modified Python source files, excluding tests, documentation and generated files. Score initial lists before the first agent command. For D, score the linked pre/post lists for the first usable failure; retain update failures and non-trigger reasons rather than selecting a later beneficial update.

| Measure | Definition |
|---|---|
| File Hit@1 / Hit@5 | 1 if at least one file in the first 1 / 5 positions belongs to G; otherwise 0 |
| File Recall@5 | Number of distinct G files in top-5 divided by the size of G |
| RR / MRR | RR = 1 / first target rank; 0 if absent from a complete ranking. MRR is the task-average RR |
| Function Hit@5 | Whether top-5 ranked functions hit an unambiguously mapped original-AST target; report eligible-task coverage |

**Output:** Initial scores, D pre/post changes, usable-failure/update counts, and coverage/exclusion reasons. An empty G is not applicable. Missing rankings are missing data. A truncated list requires a declared truncated metric, not an assumed full-MRR miss. Added/deleted/renamed paths require predefined mapping rules. Correct alternative repairs may modify different files, so localization scores are interpreted alongside official repair outcomes.

### 3.3 Exploration Efficiency

**Scope:** A–D. Reference-dependent measures require eligible G and adequate trajectories; resource measures remain applicable without G.

**Inputs and fields:** `trajectory`, `events`, `usage`, `timings`, and `gold_locations`; use source-content events, paths, query steps, execution status, token counts, duration and completeness.

**Procedure:** Extract actual agent-visible source content under a frozen inspection rule. Path-only listings do not count; file reads, source-bearing search results and localization excerpts retain separate provenance. Module-internal reads count only if content is delivered to the agent. Deduplicate inspected Python source paths and identify the first G inspection. Initial delivered source uses step 0; model queries start at 1. A first hit after query s has s−1 preceding model steps (0 for initial context).

**Measures:** Unique source files inspected, reference-file reach rate, steps before first reference inspection, total input/output tokens, method-inclusive wall time, executed commands and estimated API cost. Never-hit runs have no artificial first-hit step; incomplete traces have unknown reach status. Missing usage is disclosed, not treated as zero.

**Output:** Per-run measures, condition summaries and within-task differences. Report all eligible runs, with a supplementary comparison of tasks solved by both conditions. A fast unsuccessful stop is not sufficient evidence of overall improvement.

### 3.4 Trajectory Analysis and Failure Classification

**Scope:** Representative successes and failures; full failure-distribution claims require complete classification or a disclosed sampling design.

**Inputs and fields:** Events, original trajectory, rankings/updates, patch, interventions and official outcome; use event order, inspection/edit/test evidence, termination and outcome status.

**Procedure:** Assign one primary reason to each classified unsuccessful run, allow secondary tags, and attach raw evidence references. Ambiguous or insufficiently evidenced cases remain unknown. Apply a coding guide consistently; independently code a subset before reconciliation. Report agreement from pre-reconciliation labels if measured. Agent self-reports alone do not establish successful localization or diagnosis.

| Category | Main reason |
|---|---|
| F1 | No relevant source inspected, under the reference-location proxy |
| F2 | Relevant code inspected, but cause misdiagnosed |
| F3 | Missing, invalid or incomplete patch |
| F4 | Regression or inadequate validation |
| F5 | Environment or resource-limit obstruction |
| Unknown | Insufficient evidence for attribution |

**Output:** Category counts with coverage/denominators and evidence-backed cases linking recommendation, inspection, modification, tests and final evaluation. Successful runs may carry intermediate-error tags but receive no unsuccessful-run primary category.

### 3.5 Variability and Paired Comparison

**Scope:** A preselected repeat subset. A single execution cannot estimate run-to-run variability.

**Inputs and fields:** Protocol/run plan and per-run summaries; use task/condition/repeat/attempt IDs, main/repeat role, configuration consistency, repair scores and resource measures.

**Procedure:** Freeze repeat tasks and counts before examining outcomes. Each independent run starts from the original task state without inherited conversations or patches. Record seeds where supported; technical retries remain attempts, not repeats. Select effective attempts under the declared policy and retain all attempts for audit.

**Measures:** Individual repeat outcomes, per-task/per-condition success proportions, and resource means with standard deviation or range. Report main-study and repeat-subset results separately; do not use best-of-repeats scores. Pair conditions within task and repeat, then aggregate by task. Task-level paired bootstrap intervals may be used when sample size permits, retaining within-task repeats rather than treating them as independent tasks.

**Output:** Repeat results, within-task paired differences and uncertainty estimates where justified. Report all-task results first, then pre-annotated hint/no-hint groups and optional repository groups with sample sizes. Small subgroups support descriptive results and cases rather than broad claims. Task difficulty and test counts do not substitute for independent-repeat variability.
