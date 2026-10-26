"""Explain where files land in L, S and C for one task, and why S moved them.

Usage:
    python scripts/explain_ranking.py sphinx-doc__sphinx-7462 sphinx/domains/python.py

Reads the ranking files in experiments/ (override with --lexical,
--structural, --fused). Prints, per file, its rank in the lexical ranking L,
the structural ranking S and the fused Condition C ranking, followed by the
seeds that gave it structural score. Useful for case studies; it never
reads reference patches, so pick the files to explain yourself.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("instance_id")
    parser.add_argument("files", nargs="+", help="repo-relative paths to explain")
    parser.add_argument("--lexical", default="experiments/bm25_results.json")
    parser.add_argument("--structural", default="experiments/structural_results.json")
    parser.add_argument("--fused", default="experiments/condition_c_results.json")
    parser.add_argument("--top", type=int, default=5, help="also print the top N of each ranking")
    args = parser.parse_args(argv)

    lexical = _ranked(args.lexical, args.instance_id, "path")
    structural_task = _task(args.structural, args.instance_id)
    structural = {f["file"]: f for f in structural_task["ranked_files"]}
    fused = _ranked(args.fused, args.instance_id, "file")
    lexical_rank = {path: rank for rank, path in enumerate(lexical, start=1)}
    fused_rank = {path: rank for rank, path in enumerate(fused, start=1)}

    print(f"{args.instance_id}: |L| = {len(lexical)}, |S| = {len(structural)}, |C| = {len(fused)}")
    for name, ranking in (("L", lexical), ("S", list(structural)), ("C", fused)):
        print(f"  top {args.top} of {name}: " + ", ".join(ranking[: args.top]))

    for path in args.files:
        entry = structural.get(path)
        print(f"\n{path}")
        print(
            f"  L rank {lexical_rank.get(path, '-')}, "
            f"S rank {entry['rank'] if entry else '-'}, "
            f"C rank {fused_rank.get(path, '-')}"
        )
        if not entry:
            continue
        print(f"  structural score {entry['score']:.4f} from {len(entry['relations'])} relation(s):")
        for relation in entry["relations"]:
            if relation["relation"] == "seed":
                print(f"    - itself a seed (lexical #{relation['seed_rank']})")
            else:
                verb = "imported by" if relation["relation"] == "imported_by" else "imports"
                print(
                    f"    - {verb} lexical #{relation['seed_rank']} {relation['seed']} "
                    f"(+{relation['weight']:.4f})"
                )
    return 0


def _task(path: str, instance_id: str) -> dict:
    with open(path, encoding="utf-8") as f:
        for task in json.load(f):
            if task["instance_id"] == instance_id:
                return task
    raise SystemExit(f"{instance_id} not found in {path}")


def _ranked(path: str, instance_id: str, key: str) -> list[str]:
    files = sorted(_task(path, instance_id)["ranked_files"], key=lambda f: f["rank"])
    return [f.get(key) or f.get("file") or f.get("path") for f in files]


if __name__ == "__main__":
    sys.exit(main())
