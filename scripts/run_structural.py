"""Compute structural rankings S for SWE-bench tasks from lexical rankings L.

Usage:
    python scripts/run_structural.py --lexical bm25_results.json -o structural_results.json

The input is the retrieval module's output, a JSON list of
    {"instance_id": ..., "ranked_files": [{"rank": 1, "path": ..., "bm25_score": ...}, ...]}
("file" is accepted for "path", "score" for "bm25_score"). Each output file
entry has the LocalizationCandidate fields (file, rank, score, symbol,
symbol_type, reason) plus "relations", the structured evidence. Indexes come
from the SWE-bench cache and are built on first use.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.localization.structural import DEFAULT_NUM_SEEDS, structural_ranking  # noqa: E402
from src.repository.swebench import build_task_index, resolve_cache_dir  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lexical", required=True, help="lexical rankings JSON (role 3 output)")
    parser.add_argument("-o", "--output", required=True, help="where to write structural rankings")
    parser.add_argument("--num-seeds", type=int, default=DEFAULT_NUM_SEEDS)
    parser.add_argument(
        "--include-test-neighbors", action="store_true", help="count test files as neighbors"
    )
    parser.add_argument("--cache-dir", help="SWE-bench cache directory (default: .swebench_cache)")
    args = parser.parse_args(argv)

    with open(args.lexical, encoding="utf-8") as f:
        tasks = json.load(f)
    cache = resolve_cache_dir(args.cache_dir)

    results = []
    for task in tasks:
        instance_id = task["instance_id"]
        lexical = [
            (item.get("file", item.get("path")), item.get("bm25_score", item.get("score")))
            for item in sorted(task["ranked_files"], key=lambda item: item["rank"])
        ]
        index = build_task_index(instance_id, cache_dir=cache)
        ranking = structural_ranking(
            index,
            lexical,
            num_seeds=args.num_seeds,
            exclude_test_neighbors=not args.include_test_neighbors,
        )
        results.append(
            {
                "instance_id": instance_id,
                "index_sha256": index.metadata.get("index_sha256"),
                "num_seeds": args.num_seeds,
                "exclude_test_neighbors": not args.include_test_neighbors,
                "num_lexical_files": len(lexical),
                "ranked_files": [
                    {
                        "file": c.file,
                        "rank": c.rank,
                        "score": round(c.score, 6),
                        "symbol": c.symbol,
                        "symbol_type": c.symbol_type,
                        "reason": c.reason,
                        "relations": [
                            {**asdict(r), "weight": round(r.weight, 6)} for r in c.relations
                        ],
                    }
                    for c in ranking
                ],
            }
        )
        print(f"{instance_id}: {len(ranking)} structural candidates")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"saved to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
