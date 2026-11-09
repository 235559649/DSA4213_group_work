# Held-out SWE-bench Verified set (seed 25)

This directory contains the **selected 40-task evaluation set** and its frozen selection record. The set was fixed before any formal repair outcome was observed. The formal A/B/C/D runs on this set have since been completed; their results are reported in the final report (`docs/final_report/`). The post-selection issue annotations did not affect the draw.

## What to run

Use [`results/tasks.csv`](results/tasks.csv) as the primary task manifest. It contains the task ID, repository, base commit, environment setup commit, and two stability fields:

- `in_stability_subset=True` marks the eight tasks selected for repeated runs, two per repository.
- `planned_repeats_per_condition=3` includes the first/main run and two additional runs. All other tasks have one run per condition.

The plain ID lists are [`results/task_ids.txt`](results/task_ids.txt) and [`results/stability_ids.txt`](results/stability_ids.txt). [`results/run_plan.jsonl`](results/run_plan.jsonl) expands the design into 224 planned A/B/C/D runs: 160 first runs and 64 additional stability runs. Every row still has `status=not_run`. Each condition and repeat must start independently from the task's base commit and equivalent environment; do not carry patches or conversation state between runs.

## Selection protocol

The source is `SWE-bench/SWE-bench_Verified`, native `test` split, revision `78f471bf655a3137b2e8a75af1501690ec009ec3`. The pinned source Parquet SHA-256 and allowed metadata columns are recorded in [`inputs/source_provenance.json`](inputs/source_provenance.json). The native split name does not imply that every task was unused by this project.

The project had development artifacts for 21 tasks; these are listed with reasons and source references in [`inputs/exclusions.csv`](inputs/exclusions.csv). After restricting to four repositories and removing those tasks, the eligible pool contained 348 tasks. The quotas were fixed at Django 12, SymPy 12, Sphinx 10, and pytest 6.

Within each repository, eligible records were sorted by `instance_id` and sampled without replacement with `random.Random(25)`. A separate `random.Random("stability:25")` selected two stability tasks from each repository's selected records in sorted ID order. Difficulty, issue text, localization scores, and repair outcomes were not selection filters. The metadata snapshot in [`inputs/benchmark_metadata.json`](inputs/benchmark_metadata.json) contains only the seven fields needed to rebuild the pool and task manifest; it has no reference patch or test patch.

To reproduce and check the committed selection from the included metadata and exclusions, run from this directory:

```sh
python scripts/reproduce.py
```

Python 3.12.14 was used for the original draw. The default command uses only the standard library and checks the committed task list, stability subset, CSV, and run plan. To write a fresh copy, pass `--output-dir <new-directory>`. To additionally audit the original Parquet and development evidence files, pass `--source-root <original-workspace>`; that optional audit requires PyArrow and the source files named in `inputs/source_provenance.json`. Those source artifacts are not duplicated here.

## Descriptive issue annotations

[`results/issue_annotations.json`](results/issue_annotations.json) records provisional labels and original issue excerpts for these 40 tasks. A **strong localization clue** names a repository implementation location, internal call stack, or concrete edit target. A **clear reproduction** gives enough inputs or steps and observable behavior to attempt a failing case. Public API usage alone is a weak location clue; a clear reproduction still may need a new test.

| Localization clue | Clear reproduction | Incomplete reproduction |
| --- | ---: | ---: |
| Weak | 23 | 5 |
| Strong | 8 | 4 |

These are first-pass text labels, not run results or validated difficulty estimates. The cells describe coverage; they do not establish a method advantage. Labels were assigned after the draw and were not used to replace tasks.

## Current limits

The run plan fixes tasks, base commits, conditions, and repeat IDs. The runner implementation, model version, prompts, budgets, infrastructure failure policy, and official SWE-bench harness results must be recorded separately before and during execution. A task counts as repaired only under the agreed official evaluation criterion.
