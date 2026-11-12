# Improving Repository Navigation and Bug Localization in Minimal Software Engineering Agents

This repository contains the implementation and evaluation code for the DSA4213 Group 25 project.

The project studies whether explicit repository localization and runtime failure evidence can help a minimal software engineering agent navigate large repositories and localize relevant code more efficiently without reducing bug-fixing performance.

Our experiments use **mini-SWE-agent** on tasks from **SWE-bench Verified** and compare four localization conditions.

## Project Overview

A software engineering agent is given an issue description and a repository at the task-specific base commit. The agent interacts with the repository using shell commands and produces a final patch.

The baseline mini-SWE-agent performs repository exploration using free-form commands such as `grep`, `find`, and `cat`. Our system adds repository-localization guidance before the repair process and, in Condition D, may update that guidance using evidence from runtime failures.

The underlying mini-SWE-agent repair loop remains unchanged.

## Experimental Conditions

We evaluate four conditions:

- **Condition A — Baseline:** original mini-SWE-agent without additional localization guidance.
- **Condition B — Lexical localization:** top-ranked source files from BM25 ranking \(L\).
- **Condition C — Lexical + structural localization:** source files ranked using reciprocal rank fusion, RRF(\(L,S\)), where \(S\) is derived from repository import structure.
- **Condition D — Failure-aware localization:** Condition C plus bounded reranking when failed commands provide usable runtime evidence.

Conditions A–D use the same task, model, Docker environment, repair loop, and execution budgets. Only the localization context supplied to the agent differs.

## Repository Structure

```text
DSA4213_group_work/
├── configs/
│   └── tasks/                  # Task configuration files
├── data/
│   └── benchmark_metadata/     # Benchmark metadata
├── docs/
│   ├── analysis/               # Localization and index analyses
│   ├── architecture/           # Architecture documentation
│   ├── benchmark/              # Benchmark documentation
│   ├── evaluation/             # Evaluation protocol and timing definitions
│   └── final_report/           # Final report source files
├── experiments/
│   ├── bm25_results.json
│   ├── structural_results.json
│   └── condition_c_results.json
├── scripts/
│   ├── build_index.py
│   ├── run_bm25_batch.py
│   ├── run_structural.py
│   ├── run_rrf.py
│   ├── run_agent.py
│   ├── run_comparison.py
│   ├── localization_ablation.py
│   └── record_swebench_eval.py
├── src/                         # Repository indexing, localization, and agent integration
├── tests/                       # Project tests
├── .env.example
├── requirements.txt
└── README.md
```

## Environment Setup

Create and activate a Python virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the project dependencies:

```bash
pip install -r requirements.txt
```

The project pins:

```text
mini-swe-agent==2.4.6
```

The final experiments additionally use the official SWE-bench evaluation harness and task-specific SWE-bench Docker images.

## API Configuration

The final agent experiments use:

```text
openai/gpt-5.4-mini
```

through OpenRouter.

API credentials must be provided through environment variables and must not be committed to the repository.

A template is provided in:

```text
.env.example
```

For OpenRouter:

```bash
export OPENROUTER_API_KEY="your-key"
```

You can verify that the variable is available with:

```bash
python - <<'PY'
import os
print("OPENROUTER_API_KEY exists:", bool(os.getenv("OPENROUTER_API_KEY")))
PY
```

## Repository Localization Pipeline

### 1. BM25 lexical ranking

BM25 ranks repository entities using the issue description and aggregates entity scores to the file level.

Example:

```bash
python scripts/run_bm25_batch.py \
  --tasks <task-list> \
  --output experiments/bm25_results.json
```

The resulting ranking is used by Condition B.

### 2. Structural ranking

The structural component expands high-ranked lexical seed files using the repository import graph.

```bash
python scripts/run_structural.py \
  --lexical experiments/bm25_results.json \
  --output experiments/structural_results.json
```

The final configuration uses the top lexical files as seeds and retains them at the head of the structural ranking.

### 3. Reciprocal Rank Fusion

The lexical and structural rankings are combined using Reciprocal Rank Fusion with:

```text
RRF k = 60
```

Run:

```bash
python scripts/run_rrf.py \
  --lexical experiments/bm25_results.json \
  --structural experiments/structural_results.json \
  --output experiments/condition_c_results.json
```

The resulting ranking is used by Condition C and as the initial localization context for Condition D.

## Running the Agent

The unified experiment runner is:

```text
scripts/run_agent.py
```

Available options can be inspected using:

```bash
python scripts/run_agent.py --help
```

### Condition A

Condition A runs the original mini-SWE-agent without additional localization candidates:

```bash
python scripts/run_agent.py \
  --benchmark swebench \
  --condition A \
  --instance-id <instance-id> \
  --task-config <task-config>
```

### Condition B

Condition B supplies BM25 candidates:

```bash
python scripts/run_agent.py \
  --benchmark swebench \
  --condition B \
  --instance-id <instance-id> \
  --task-config <task-config> \
  --candidates experiments/bm25_results.json \
  --localization-top-k 20
```

### Condition C

Condition C supplies the fused lexical and structural ranking:

```bash
python scripts/run_agent.py \
  --benchmark swebench \
  --condition C \
  --instance-id <instance-id> \
  --task-config <task-config> \
  --candidates experiments/condition_c_results.json \
  --localization-top-k 20
```

### Condition D

Condition D uses the Condition C localization strategy and enables bounded runtime-failure feedback:

```bash
python scripts/run_agent.py \
  --benchmark swebench \
  --condition D \
  --instance-id <instance-id> \
  --task-config <task-config> \
  --localization-top-k 20
```

The frozen failure-feedback limits are:

```text
ranking updates:     maximum 3
edit recovery:       maximum 2
diagnostic updates:  maximum 1
failure weight:      1.0
```

Runtime feedback is delivered only when a failed command provides usable repository-backed evidence.

## Localization Prompt Policy

For Conditions B–D, localization guidance is advisory rather than restrictive.

The final prompt policy presents:

- up to 20 ranked source files;
- up to 3 related test files separately;
- no reference patch or official benchmark test labels.

The agent may inspect any file in the repository even if that file is not included in the localization hint.

## Experimental Setup

The final study uses:

| Setting | Value |
| --- | --- |
| Benchmark | SWE-bench Verified |
| Dataset revision | `78f471bf655a3137b2e8a75af1501690ec009ec3` |
| Development set | 20 tasks |
| Held-out set | 40 tasks |
| Conditions | A, B, C, D |
| Main runs | 40 tasks × 4 conditions = 160 |
| Stability subset | 8 held-out tasks |
| Additional stability runs | 8 × 4 × 2 = 64 |
| Total formal agent runs | 224 |
| Agent | mini-SWE-agent 2.4.6 |
| Model | `openai/gpt-5.4-mini` via OpenRouter |
| Localization top-k | 20 |
| RRF constant | 60 |
| Maximum model steps | 250 |
| Cost limit | USD 3 per run |
| Command timeout | 60 seconds |

Development tasks were used for implementation debugging and design choices. The 40-task held-out set was frozen before final results were inspected.

The 8-task stability subset was executed for two additional rounds under every condition to measure run-to-run variation.

Technical retries caused by infrastructure failures are tracked separately from independent experimental repeats.

## Evaluation

Generated patches are evaluated using the official SWE-bench harness.

Official benchmark information such as the reference patch and `FAIL_TO_PASS` / `PASS_TO_PASS` labels is not exposed to the agent during patch generation.

Recorded evaluation results can be attached to an experiment run with:

```bash
python scripts/record_swebench_eval.py --help
```

Cross-condition summaries can be generated using:

```bash
python scripts/run_comparison.py \
  --runs-dir <runs-directory> \
  --output comparison.md
```

The project evaluates three groups of metrics:

1. **Repair performance** — whether the generated patch resolves the SWE-bench task.
2. **Localization quality** — including Hit@1, Hit@5, Recall@5, and MRR.
3. **Efficiency** — including model calls, repository exploration, localization overhead, cost, and wall-clock time.

Development-set localization ablations can be reproduced with:

```bash
python scripts/localization_ablation.py --help
```

## Reproducibility and Safety

Each SWE-bench task executes inside its task-specific Docker environment.

To separate infrastructure setup from formal agent execution, required Docker images should be available before a formal run begins. Interrupted experiment batches can be resumed while preserving already recorded formal results.

The project follows the following safeguards:

- API credentials are supplied through environment variables and are not committed.
- Only `.env.example` is included in the repository.
- Repository content and tool output are treated as untrusted inputs.
- Reference patches and official test labels are evaluation-only information.
- Generated patches are evaluated using the official harness.
- Generated patches should receive human review before use outside the benchmark environment.

## Final Report

The LaTeX source for the final report is located at:

```text
docs/final_report/
```

The report can be compiled by uploading the directory to Overleaf or, with a local LaTeX installation, using:

```bash
cd docs/final_report
latexmk -pdf main.tex
```