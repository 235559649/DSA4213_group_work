"""Evaluate BM25 localization on SWE-bench development tasks.

Metrics: Hit@1, Hit@5, Recall@5, and MRR (full ranking).
"""

import csv
import json
from pathlib import Path

from datasets import load_dataset

RESULT_PATH = Path("results/bm25_results.json")
OUTPUT_PATH = Path("results/bm25_evaluation.csv")
DATASET_REVISION = "78f471bf655a3137b2e8a75af1501690ec009ec3"


def extract_modified_files(patch: str) -> set[str]:
    """Extract modified Python source paths from the reference patch."""
    files = set()
    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:].strip()
            if path.endswith(".py"):
                files.add(path)
    return files


def evaluate_ranking(ranked_files: list[dict], true_files: set[str]) -> dict:
    """Evaluate a complete file ranking; empty ground truth is not scored."""
    if not true_files:
        return {
            "hit_at_1": None,
            "hit_at_5": None,
            "recall_at_5": None,
            "mrr": None,
            "matched_files_at_5": "",
        }

    # Ranking order is the order in the JSON; discard repeated paths, if any.
    paths = list(dict.fromkeys(item["path"] for item in ranked_files))
    top5_matches = true_files.intersection(paths[:5])
    first_correct_rank = next(
        (rank for rank, path in enumerate(paths, start=1) if path in true_files),
        None,
    )
    return {
        "hit_at_1": int(bool(paths) and paths[0] in true_files),
        "hit_at_5": int(bool(top5_matches)),
        "recall_at_5": len(top5_matches) / len(true_files),
        "mrr": 1.0 / first_correct_rank if first_correct_rank is not None else 0.0,
        "matched_files_at_5": "; ".join(sorted(top5_matches)),
    }


def main() -> None:
    print("Loading BM25 results...")
    with RESULT_PATH.open("r", encoding="utf-8") as f:
        bm25_results = json.load(f)

    print("Loading SWE-bench Verified dataset...")
    dataset = load_dataset(
        "SWE-bench/SWE-bench_Verified",
        split="test",
        revision=DATASET_REVISION,
    )
    tasks = {row["instance_id"]: row for row in dataset}
    evaluation = []

    for result in bm25_results:
        task_id = result["instance_id"]
        if task_id not in tasks:
            raise ValueError(f"Task not found: {task_id}")

        # Ground truth is used only for offline evaluation, never for retrieval.
        true_files = extract_modified_files(tasks[task_id]["patch"])
        true_files = {
            path for path in true_files
            if not (
                path.startswith("tests/")
                or path.startswith("testing/")
                or "/tests/" in path
            )
        }
        metrics = evaluate_ranking(result["ranked_files"], true_files)
        evaluation.append({
            "instance_id": task_id,
            "num_true_files": len(true_files),
            "hit_at_1": metrics["hit_at_1"],
            "hit_at_5": metrics["hit_at_5"],
            "recall_at_5": metrics["recall_at_5"],
            "mrr": metrics["mrr"],
            "true_files": "; ".join(sorted(true_files)),
            "matched_files_at_5": metrics["matched_files_at_5"],
        })
        print(
            f"{task_id}: Hit@1={metrics['hit_at_1']}, "
            f"Hit@5={metrics['hit_at_5']}, "
            f"Recall@5={metrics['recall_at_5']}, MRR={metrics['mrr']}"
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "instance_id", "num_true_files", "hit_at_1", "hit_at_5",
            "recall_at_5", "mrr", "true_files", "matched_files_at_5",
        ])
        writer.writeheader()
        writer.writerows(evaluation)

    valid = [row for row in evaluation if row["mrr"] is not None]
    print("\n" + "=" * 60)
    print("BM25 Evaluation Summary")
    print("=" * 60)
    print(f"Total tasks: {len(evaluation)}")
    print(f"Evaluated tasks: {len(valid)}")
    for key, label in [
        ("hit_at_1", "Hit@1"),
        ("hit_at_5", "Hit@5"),
        ("recall_at_5", "Mean Recall@5"),
        ("mrr", "MRR"),
    ]:
        mean = sum(row[key] for row in valid) / len(valid) if valid else 0.0
        print(f"{label}: {mean:.2%}" if key != "mrr" else f"{label}: {mean:.4f}")
    print(f"Results saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
