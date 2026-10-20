"""Generate Condition C rankings using RRF (k=60).

Uses BM25 lexical ranking L and structural ranking S.
Does not access SWE-bench ground truth.
"""

import json
from pathlib import Path

from src.localization.ranker import fuse_condition_c


BM25_PATH = Path("experiments/bm25_results.json")
STRUCTURAL_PATH = Path("experiments/structural_results.json")
OUTPUT_PATH = Path("experiments/condition_c_results.json")

RRF_K = 60


def load_results(path):
    """Load ranking results from JSON."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    print("Loading BM25 and Structural rankings...")

    lexical_results = load_results(BM25_PATH)
    structural_results = load_results(STRUCTURAL_PATH)

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

        fused = fuse_condition_c(
            lexical_ranking=lexical,
            structural_ranking=structural,
            k=RRF_K,
        )

        all_results.append({
            "instance_id": task_id,
            "condition": "C",
            "rrf_k": RRF_K,
            "ranked_files": fused,
        })

        print(
            f"{task_id}: "
            f"BM25={len(lexical)}, "
            f"Structural={len(structural)}, "
            f"Fused={len(fused)}"
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            all_results,
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("\n" + "=" * 60)
    print("Condition C RRF fusion completed!")
    print(f"Tasks processed: {len(all_results)}")
    print(f"RRF k: {RRF_K}")
    print(f"Results saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()