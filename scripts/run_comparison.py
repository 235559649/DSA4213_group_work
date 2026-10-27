"""Per-task comparison table: localization -> what the agent was shown -> repair.

Usage:
    python scripts/run_comparison.py --runs-dir runs -o comparison.md

Reads every run directory under --runs-dir (those containing
run_result.json) and, for each run, reports where the first reference file
was in the full ranking delivered to the run, whether it was among the
candidates shown to the agent, for Condition D how the first usable runtime
failure changed that rank (proposal section 5.2), and whether the official
evaluation resolved the task. Reference files come from
src/evaluation/gold.py (evaluation side only); their paths are printed only
with --show-paths.

Whether the agent actually opened the reference file is a trajectory
question; take it from the evaluation lead's trajectory labels.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.gold import reference_files, target_files  # noqa: E402
from src.evaluation.localization import first_hit  # noqa: E402
from src.repository.swebench import build_task_index, resolve_cache_dir  # noqa: E402

CONDITIONS = ("A", "B", "C", "D")


def read_run(run_dir: Path, targets: list[str]) -> dict:
    """What one run recorded, reduced to the comparison columns."""
    result = json.loads((run_dir / "run_result.json").read_text(encoding="utf-8"))
    evaluation = (result.get("evaluation") or {}).get("official_swebench_evaluation") or {}
    config = result.get("config") or {}
    row = {
        "run_id": result.get("run_id", run_dir.name),
        "task_id": result.get("task_id"),
        "condition": result.get("condition"),
        "resolved": evaluation.get("resolved"),
        "cost_usd": (result.get("usage") or {}).get("cost_usd"),
        "delivered_size": None,  # None: no ranking file in the run directory
        "delivered_rank": None,
        "prompt_rank": None,
        "prompt_size": None,
        "d_failures": None,
        "d_updates": None,
        "d_first_usable": None,
    }

    full = _read_json(run_dir / "localization_candidates.json")
    prompt = _read_json(run_dir / "prompt_candidates.json")
    if full is not None:
        row["delivered_size"] = len(full)
        row["delivered_rank"] = first_hit([c["file"] for c in full], targets)
    if prompt is not None:
        row["prompt_size"] = len(prompt)
        row["prompt_rank"] = first_hit([c["file"] for c in prompt], targets)

    if row["condition"] == "D":
        events = _read_jsonl(run_dir / "failure_feedback" / "failure_updates.jsonl")
        summary = config.get("failure_feedback") or {}
        row["d_failures"] = summary.get("failures_observed", len(events))
        row["d_updates"] = summary.get("updates_applied", sum(bool(e.get("update_applied")) for e in events))
        usable = next((e for e in events if (e.get("analysis") or {}).get("usable")), None)
        if usable is not None:
            before = usable.get("before_ranking")
            after = usable.get("proposed_ranking")
            row["d_first_usable"] = {
                "status": usable.get("update_status"),
                "before": first_hit([c["file"] for c in before], targets) if before else None,
                "after": first_hit([c["file"] for c in after], targets) if after else None,
            }
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs-dir", required=True, help="directory holding one folder per run")
    parser.add_argument("--cache-dir", help="SWE-bench cache directory (default: .swebench_cache)")
    parser.add_argument("--show-paths", action="store_true", help="print reference file paths")
    parser.add_argument("-o", "--output", help="write the Markdown here instead of stdout")
    args = parser.parse_args(argv)

    cache = resolve_cache_dir(args.cache_dir)
    references = reference_files(cache)
    run_dirs = sorted(p.parent for p in Path(args.runs_dir).glob("*/run_result.json"))
    if not run_dirs:
        parser.error(f"no run_result.json under {args.runs_dir}")

    targets_by_task: dict[str, list[str]] = {}
    rows = []
    for run_dir in run_dirs:
        task_id = json.loads((run_dir / "run_result.json").read_text(encoding="utf-8"))["task_id"]
        if task_id not in targets_by_task:
            index = build_task_index(task_id, cache_dir=cache)
            targets_by_task[task_id], _ = target_files(references.get(task_id, []), index)
        rows.append(read_run(run_dir, targets_by_task[task_id]))

    text = render(rows, targets_by_task, show_paths=args.show_paths)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


def render(rows: list[dict], targets_by_task: dict[str, list[str]], *, show_paths: bool) -> str:
    rows = sorted(rows, key=lambda r: (r["task_id"], CONDITIONS.index(r["condition"]) if r["condition"] in CONDITIONS else 9, r["run_id"]))
    lines = [
        "| Task | Cond. | Run | Rank in delivered ranking | In prompt (rank / size) "
        "| D: failures / updates | D: first usable failure, rank before -> after | Resolved |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        d_first = r["d_first_usable"]
        lines.append(
            f"| {r['task_id']} | {r['condition']} | {r['run_id'][-8:]} "
            f"| {_delivered(r)} "
            f"| {_prompt(r)} "
            f"| {_d_counts(r)} "
            f"| {_d_first(d_first) if r['condition'] == 'D' else ''} "
            f"| {_resolved(r['resolved'])} |"
        )

    lines += ["", "Per condition:", "", "| Cond. | Runs | Resolved | Reference file in prompt | D runs with a usable failure |", "|---|---|---|---|---|"]
    by_condition = defaultdict(list)
    for r in rows:
        by_condition[r["condition"]].append(r)
    for condition in sorted(by_condition, key=lambda c: CONDITIONS.index(c) if c in CONDITIONS else 9):
        runs = by_condition[condition]
        evaluated = [r for r in runs if r["resolved"] is not None]
        resolved = f"{sum(r['resolved'] for r in evaluated)}/{len(evaluated)}"
        if len(evaluated) < len(runs):
            resolved += f" ({len(runs) - len(evaluated)} not evaluated)"
        shown = [r for r in runs if r["prompt_size"] is not None]
        if condition == "A":
            in_prompt = "n/a"
        else:
            in_prompt = f"{sum(r['prompt_rank'] is not None for r in shown)}/{len(shown)}"
            if len(shown) < len(runs):
                in_prompt += f" ({len(runs) - len(shown)} missing)"
        usable = f"{sum(r['d_first_usable'] is not None for r in runs)}/{len(runs)}" if condition == "D" else ""
        lines.append(f"| {condition} | {len(runs)} | {resolved} | {in_prompt} | {usable} |")

    if show_paths:
        lines += ["", "Reference files:", ""]
        lines += [f"- {task}: {'; '.join(paths) or '(none)'}" for task, paths in sorted(targets_by_task.items())]
    return "\n".join(lines) + "\n"


def _rank(rank) -> str:
    return str(rank) if rank is not None else "-"


def _delivered(r: dict) -> str:
    # Missing data is reported as missing, never as a miss (protocol 2.3).
    if r["condition"] == "A":
        return "n/a"
    if r["delivered_size"] is None:
        return "missing"
    return _rank(r["delivered_rank"])


def _prompt(r: dict) -> str:
    if r["condition"] == "A":
        return "n/a"
    if r["prompt_size"] is None:
        return "missing"
    return f"{r['prompt_rank']} / {r['prompt_size']}" if r["prompt_rank"] else f"no / {r['prompt_size']}"


def _d_counts(r: dict) -> str:
    return f"{r['d_failures']} / {r['d_updates']}" if r["condition"] == "D" else ""


def _d_first(d_first) -> str:
    if d_first is None:
        return "none"
    before, after = d_first["before"], d_first["after"]
    if after is None and d_first["status"] != "applied":
        return f"{_rank(before)} -> no update ({d_first['status']})"
    return f"{_rank(before)} -> {_rank(after)}"


def _resolved(value) -> str:
    return {True: "yes", False: "no"}.get(value, "not evaluated")


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    sys.exit(main())
