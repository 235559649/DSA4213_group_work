"""Generate Condition C rankings using RRF (k=60).

Uses BM25 lexical ranking L and structural ranking S.
Does not access SWE-bench ground truth.

Usage:
    python scripts/run_rrf.py                             # experiments/*.json, as before
    python scripts/run_rrf.py --lexical experiments/test/bm25_results.json \\
        --structural experiments/test/structural_results.json \\
        --output experiments/test/condition_c_results.json
"""

import argparse
import json
import platform
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.localization.ranker import fuse_condition_c  # noqa: E402


BM25_PATH = Path("experiments/bm25_results.json")
STRUCTURAL_PATH = Path("experiments/structural_results.json")
OUTPUT_PATH = Path("experiments/condition_c_results.json")

RRF_K = 60


def load_results(path):
    """Load ranking results from JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--lexical", type=Path, default=BM25_PATH, help="BM25 rankings JSON (L)")
    parser.add_argument("--structural", type=Path, default=STRUCTURAL_PATH, help="structural rankings JSON (S)")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH, help="where to write Condition C rankings")
    parser.add_argument("--k", type=int, default=RRF_K, help="RRF constant (frozen at 60)")
    args = parser.parse_args(argv)

    print("Loading BM25 and Structural rankings...")

    lexical_results = load_results(args.lexical)
    structural_results = load_results(args.structural)

    structural_by_id = {
        task["instance_id"]: task
        for task in structural_results
    }

    all_results = []

    for task in lexical_results:
        task_id = task["instance_id"]

        if task_id not in structural_by_id:
            raise ValueError(
                f"Missing structural ranking for {task_id}"
            )

        lexical = task["ranked_files"]
        structural = structural_by_id[task_id]["ranked_files"]

        started = time.perf_counter()
        fused = fuse_condition_c(
            lexical_ranking=lexical,
            structural_ranking=structural,
            k=args.k,
        )
        rrf_seconds = time.perf_counter() - started

        all_results.append({
            "instance_id": task_id,
            "condition": "C",
            "rrf_k": args.k,
            "timing": {
                "rrf_seconds": round(rrf_seconds, 6),
                "measured_on": f"{platform.system()} {platform.machine()}, Python {platform.python_version()}",
            },
            "ranked_files": fused,
        })

        print(
            f"{task_id}: "
            f"BM25={len(lexical)}, "
            f"Structural={len(structural)}, "
            f"Fused={len(fused)}, RRF={rrf_seconds:.6f} s"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(
            all_results,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("\n" + "=" * 60)
    print("Condition C RRF fusion completed!")
    print(f"Tasks processed: {len(all_results)}")
    print(f"RRF k: {args.k}")
    print(f"Results saved to: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
