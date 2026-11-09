# Unified offline evaluator

## Slim checkout and complete evidence

This distribution deliberately omits large raw files. The example and 30 synthetic boundary tests work without them; the five recorded-evidence tests require an external manifest via OFFLINE_EVAL_MANIFEST. They skip explicitly when it is unset.

For full real-data analysis, follow [retrieval and reproduction](../../docs/FULL_EVIDENCE.md), extract the complete archive separately, and pass that archive's evidence/manifest.json to the analyzer. The local evidence/manifest.json is a retained full-data contract, not a partial-data manifest. Published results are precomputed from complete evidence. The metric implementation is unchanged from the full delivery.

## Purpose and setup

Analyze already-recorded localization-assisted repair runs with **Python 3.10+ and the standard library only**. Run commands from the package root, not this module directory. Windows PowerShell, Linux, and macOS use the same Python arguments. Substitute your Python executable if it is not named `python`.

```bash
python -m tools.offline_eval --help
python -m unittest discover -s tests -p test_offline_eval.py -v
python -m tools.offline_eval analyze --manifest examples/minimal/manifest.json --output local-output/example
```

There is no fixed task count. The manifest declares tasks, conditions, repeats, attempt selection, and artifact paths. D-only batches are supported; missing A/B/C runs are not fabricated. The tool also supports incomplete batches, multiple independent repeats, and infrastructure retries. Each declared task-condition-repeat has at most one selected attempt.

## Manifest contract (schema version 1)

See the runnable synthetic [example manifest](../../examples/minimal/manifest.json) and the real [evidence manifest](../../evidence/manifest.json).

| Field | Meaning |
|---|---|
| `schema_version` | Must be `1`. |
| `package_root` | Root relative to the manifest's directory; default `.`. |
| `experiments` | Experiment IDs, planned task IDs, available conditions, and independent repeat IDs. |
| `records` | Every actual execution attempt, including excluded attempts. |
| `labels` | Optional package-relative JSON mapping task IDs to evaluation-only `paths`. |
| `comparisons` | Optional baseline and candidate experiment lists, joined by task, condition, and repeat. |
| `cohorts` | Optional descriptive unions of disjoint task-condition-repeat records, with optional task filters. |

Each record requires `experiment_id`, `run_id`, `task_id`, `condition`, `repeat_id`, `attempt_id`, `selected` (Boolean), `selection_reason`, and `artifacts`. Attempt selection is explicit; the tool never chooses the most successful attempt. Do not reuse `repeat_id` to count infrastructure retries as additional independent samples.

All artifact paths are relative to `package_root`. Use forward slashes. Paths escaping that root, absolute paths, duplicate run IDs within an experiment, and multiple selected attempts for one planned combination are rejected. A listed file must exist. Omit the artifact key when a file was not recorded.

| Artifact key | Expected recorded format |
|---|---|
| `result` | Required `run_result.json`: matching run/task/condition IDs, usage, config, status, runtime. |
| `trajectory` | JSON with `messages`; model responses are read from `messages[*].extra.response`. |
| `official_report` | SWE-bench report object keyed by the exact task ID, containing `resolved`, patch application, and test status. |
| `ranking` | Full initial ranking: list of `{file, rank, ...}` records. |
| `prompt_candidates` | Delivered initial candidate list. Original ranks may have gaps after filtering. |
| `effective_task` | UTF-8 task text checked against the first user message. |
| `patch` | Agent-produced patch; can exist even when submission failed. |
| `official_patch` | Optional native Harness patch for a byte comparison. |
| `timings` | Optional explicit agent-wall and Harness timing record. |
| `feedback_events` | JSONL events in recorded chronological order. |
| `feedback_summary` | Preserved controller summary; metrics use recorded events/config fields. |

Other artifact keys are allowed and checked for existence. They do not change metric definitions. Unknown upstream schemas require a documented adapter; this is not a parser for arbitrary experiment ZIP formats.

## Metric definitions and boundaries

**Success.** Only `official_report[task_id].resolved` supplies repair success. Agent completion, patch generation, local test success, and feedback delivery are different properties. Missing official reports remain `null`. Summaries expose selected/evaluated/expected denominators; a selected-run success rate is unknown if any selected official outcome is missing. Evaluated-only rates must be read with their denominator.

**Localization.** The target paths are offline evaluation proxies derived in prior audits. `RR` is the reciprocal of the first target's full-ranking rank; `Hit@k` means any target is in the first k ranks; `Recall@5` is the fraction of target files in the first five ranks. A missing ranking is unknown; an existing ranking with no target is a miss. Condition A has no supplied localization ranking, so its metrics are not applicable. No function-level metric is inferred from file-level rankings.

**Visibility.** `target_display_positions` counts positions in the actual recorded candidate list. It is different from `target_ranks`. A source-only candidate at display position 5 can retain full-ranking rank 12. Visible hit/recall uses the supplied candidate list, not an assumed Top-20 prefix. The file's presence does not prove the agent read or used it.

**Usage.** Sum every response-bearing trajectory message, including responses stored on error/user messages. Do not count only assistant messages or use the final response's tokens. Missing response usage remains unknown. Incomplete response counts invalidate complete-run usage totals and preserve partial totals separately. A confirmed zero-call startup failure has zero model usage; this does not imply zero runtime. Provider-reported costs are not reconciled against billing. The input count already includes cached tokens; do not add cached tokens again.

**D feedback.** The first event with `analysis.usable=true` is retained even if no update was applied. The first actual delivery is reported separately. `diagnostic_only` can be delivered with `usable=false`; usable localization evidence is not a universal definition of useful diagnosis. Route, applied flag, actual ordering change, text delivery, and recorded hash are separate fields. Repeated identical messages are matched chronologically. A delivered-context hash is checked when present. Delivery timing is checked against response-bearing messages. If a trajectory is incomplete, inspect the resulting audit failures rather than assuming correct delivery.

**Timing.** `runtime_seconds`, `agent_wall_seconds`, and `harness_seconds` remain separate because their scopes differ. New D records expose `initial_localization_seconds` and `feedback_total_seconds`. Their sum is an observed D localization/feedback subtotal inside the run, not extra time to add to runtime. Per-event processing time is a subset of controller feedback time; never add both to estimate total overhead. Legacy `localization_overhead_seconds` is preserved under `legacy_localization_overhead_seconds`; it is not substituted for missing new timing. Missing historical timing is unknown, not zero. C-D wall-time differences also contain different agent actions and environment variance, so they are not a direct measurement of D overhead.

**Comparisons.** Within-batch A-D is the overall comparison; C-D examines the incremental D mechanism. Cross-version comparisons match the same task/condition/repeat, with retry numbers allowed to differ. Unmatched rows are retained and excluded from paired differences. System/user prompt hashes, model names, and base commits are reported as equality checks; equality does not prove deterministic execution, and changes prevent single-factor causal claims. Descriptive cohorts cannot double-count task-condition-repeat combinations.

## Outputs

- `analysis.json`: run records, metrics, feedback events, missing combinations, comparisons, and audit failures.
- `run_summary.csv`: all attempts, including excluded attempts.
- `condition_summary.csv`: per-batch/condition selected and all-attempt totals, each with known/total coverage.
- `comparisons.csv`: paired and unmatched comparisons.
- `feedback_events.csv`: event-level routes, delivery, ranks, and processing time.
- `d_timing.csv`: per-run initial localization, controller feedback, runtime fraction, and nested event timing with coverage counts.

The destination must not exist. Exit code `0` means analysis completed without an explicit failed consistency check; `1` means outputs were written but one or more checks failed; `2` means input/CLI validation failed. Unknown checks are not passes. Incomplete evidence can therefore produce exit code `0` with missing outcomes: inspect `missing_selected`, denominators, and null fields.

Patch/submission comparison normalizes CRLF to LF and strips surrounding whitespace to match historical writers. The output separately exposes exact byte equality; official patch byte equality is checked when that artifact exists. This package does not claim byte equality where only normalized text is available.

## Adding a new experiment

1. Copy the recorded result, trajectory, patch, rankings, feedback, timing, and official result into a new evidence directory. Do not execute or import scripts from an untrusted export.
2. Add its planned tasks/conditions/repeats and every execution attempt to a new manifest. Record the predetermined selection rule and exclusion reasons.
3. Add evaluation-only file labels if localization scoring is needed. Keep labels outside agent inputs. Without labels, repair and cost analysis still work.
4. Add comparison entries only when the intended baseline is identifiable. Review prompt/config changes before interpreting differences.
5. Run analysis to a fresh output directory, review audit failures and missing-data denominators, then author the error analysis against the actual trajectories.

For example, this small fixture can be analyzed without the real evidence:

```bash
python -m tools.offline_eval analyze --manifest examples/minimal/manifest.json --output local-output/example
```

There is no need to edit Python code when changing from 3 tasks to 4, 6, 25, or another count, provided the recorded schema remains compatible. Memory usage grows with the total trajectory/event data loaded; large experiments may need batch-level manifests.

## Human analysis is separate

The Chinese reports preserve detailed source-view and failure analyses from prior audits, with trajectory message references. [Historical annotations](../../evidence/annotations/README.md) preserve the prior extracted source-exposure records. These are not automatically regenerated by this evaluator. Exact source-view verification against base-commit Git blobs requires additional source evidence that is deliberately not bundled as a repository cache. Do not describe those annotations as newly verified or infer source comprehension from a grep hit.

The tool does not classify root causes, execute agent patches, compare against reference repair implementations, or synthesize causal conclusions. It supplies auditable measurements for that analysis.
