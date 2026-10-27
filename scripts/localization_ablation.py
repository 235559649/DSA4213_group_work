"""Offline localization ablation: score each ranking variant against the reference files.

Usage:
    python scripts/localization_ablation.py --tasks-from experiments/bm25_results.json -o ablation.md

No agent runs and no model calls: every ranking is recomputed from the
task's index and problem statement, then scored against the files the
reference patch modifies (src/evaluation/gold.py, evaluation side only).
Metrics follow proposal section 5.2 / protocol section 3.2.

Variants:
  L    BM25 file ranking (Condition B)
  S0   structural ranking alone, proposal definition (neighbors only, no seeds)
  C    RRF(L, S), S with the seeds first, as used in the experiments (Condition C)
  C0   RRF(L, S0), the proposal's original Condition C
  L', C'  L and C restricted to source files, as the prompt policy
          source_only+related_tests_v1 shows them (B' and C')

Reference file paths are printed only with --show-paths.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agent.context import is_source_file  # noqa: E402
from src.evaluation.gold import reference_files, target_files  # noqa: E402
from src.evaluation.localization import score_ranking, summarize  # noqa: E402
from src.localization.keyword import BM25Retriever  # noqa: E402
from src.localization.ranker import fuse_condition_c  # noqa: E402
from src.localization.structural import structural_ranking  # noqa: E402
from src.repository.swebench import build_task_index, load_task, resolve_cache_dir  # noqa: E402

VARIANTS = {
    "L": "BM25 (B)",
    "S0": "structural only, no seeds",
    "C": "RRF(L, S), seeds first (C as run)",
    "C0": "RRF(L, S0) (proposal's C)",
    "L'": "L, source files only (B' prompt policy)",
    "C'": "C, source files only (C' prompt policy)",
}
PRIMARY = ["hit@1", "hit@5", "recall@5", "rr"]
EXTRA = ["hit@10", "hit@20"]


def rank_variants(index, problem_statement: str) -> dict[str, list[str]]:
    lexical = BM25Retriever(index).retrieve(problem_statement)
    lexical_items = [{"path": p, "rank": i, "bm25_score": s} for i, (p, s) in enumerate(lexical, 1)]
    with_seeds = structural_ranking(index, lexical)
    without_seeds = structural_ranking(index, lexical, include_seeds=False)
    as_items = lambda ranking: [{"file": c.file, "rank": c.rank, "score": c.score} for c in ranking]
    rankings = {
        "L": [p for p, _ in lexical],
        "S0": [c.file for c in without_seeds],
        "C": [x["file"] for x in fuse_condition_c(lexical_items, as_items(with_seeds))],
        "C0": [x["file"] for x in fuse_condition_c(lexical_items, as_items(without_seeds))],
    }
    # The prompt policy source_only+related_tests_v1 (src/agent/context.py)
    # shows only source files; score the list the agent would see.
    rankings["L'"] = [f for f in rankings["L"] if is_source_file(f)]
    rankings["C'"] = [f for f in rankings["C"] if is_source_file(f)]
    return rankings


def compare_with_lexical(ranking: list[str], lexical: list[str]) -> dict:
    """Layer 1: does the variant actually change what a top-k prompt would show?"""
    return {
        "top5_differs": ranking[:5] != lexical[:5],
        "top20_differs": ranking[:20] != lexical[:20],
        "top20_overlap": len(set(ranking[:20]) & set(lexical[:20])) / max(1, min(20, len(lexical))),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("instance_ids", nargs="*")
    parser.add_argument("--tasks-from", help="a rankings JSON with one entry per instance_id")
    parser.add_argument("--cache-dir", help="SWE-bench cache directory (default: .swebench_cache)")
    parser.add_argument("--show-paths", action="store_true", help="print reference file paths")
    parser.add_argument("--json", help="also write per-task results as JSON")
    parser.add_argument("-o", "--output", help="write the Markdown report here instead of stdout")
    args = parser.parse_args(argv)

    instance_ids = list(args.instance_ids)
    if args.tasks_from:
        with open(args.tasks_from, encoding="utf-8") as f:
            instance_ids += [task["instance_id"] for task in json.load(f)]
    if not instance_ids:
        parser.error("give instance ids or --tasks-from")
    cache = resolve_cache_dir(args.cache_dir)
    references = reference_files(cache)

    rows = []
    for instance_id in instance_ids:
        task = load_task(instance_id, cache)
        index = build_task_index(instance_id, cache_dir=cache)
        targets, excluded = target_files(references.get(instance_id, []), index)
        rankings = rank_variants(index, task.problem_statement)
        rows.append(
            {
                "instance_id": instance_id,
                "targets": targets,
                "excluded": excluded,
                "scores": {v: score_ranking(rankings[v], targets) for v in VARIANTS},
                "mechanism": {v: compare_with_lexical(rankings[v], rankings["L"]) for v in VARIANTS if v != "L"},
            }
        )
        print(f"{instance_id}: {len(targets)} target file(s)", file=sys.stderr)

    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    text = render(rows, show_paths=args.show_paths)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


def render(rows: list[dict], *, show_paths: bool) -> str:
    scored = [r for r in rows if r["targets"]]
    n = len(rows)
    lines = [
        f"Tasks: {n}; scored: {len(scored)}; "
        f"excluded (no modified Python source file): {n - len(scored)}.",
        "",
        "Layer 1, mechanism: how often each variant changes the ranking a prompt would show, against L.",
        "",
        "| Variant | Top-5 differs from L | Top-20 differs from L | Mean top-20 overlap with L |",
        "|---|---|---|---|",
    ]
    for key in VARIANTS:
        if key == "L":
            continue
        m = [r["mechanism"][key] for r in rows]
        lines.append(
            f"| {key} | {sum(x['top5_differs'] for x in m)}/{n} | {sum(x['top20_differs'] for x in m)}/{n} "
            f"| {sum(x['top20_overlap'] for x in m) / n:.2f} |"
        )
    lines += [
        "",
        "Layer 2, localization effectiveness: scores against the reference files (proposal 5.2).",
        "",
        "| Variant | " + " | ".join(m.replace("rr", "MRR") for m in PRIMARY + EXTRA) + " |",
        "|---|" + "---|" * len(PRIMARY + EXTRA),
    ]
    for key, label in VARIANTS.items():
        summary = summarize(r["scores"][key] for r in rows)
        cells = [f"{summary[m]:.3f}" if m in ("rr", "recall@5") else f"{summary[m]:.2f}" for m in PRIMARY + EXTRA]
        lines.append(f"| {key}: {label} | " + " | ".join(cells) + " |")

    lines += [
        "",
        "Rank of the first reference file in each ranking (- = not ranked):",
        "",
        "| Task | Targets | " + " | ".join(VARIANTS) + (" | Reference files |" if show_paths else " |"),
        "|---|---|" + "---|" * len(VARIANTS) + ("---|" if show_paths else ""),
    ]
    for r in rows:
        if not r["targets"]:
            ranks = ["n/a"] * len(VARIANTS)
        else:
            ranks = [str(r["scores"][v]["first_hit"] or "-") for v in VARIANTS]
        line = f"| {r['instance_id']} | {len(r['targets'])} | " + " | ".join(ranks) + " |"
        if show_paths:
            line += " " + "; ".join(r["targets"]) + " |"
        lines.append(line)

    excluded = [(r["instance_id"], path, why) for r in rows for path, why in r["excluded"].items()]
    if excluded:
        lines += ["", "Files left out of G:", ""]
        lines += [f"- {iid}: {path if show_paths else '(path hidden)'} ({why})" for iid, path, why in excluded]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
