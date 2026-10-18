"""Evaluate BM25 file retrieval on 20 SWE-bench development tasks."""

import csv
import json
import re
from pathlib import Path

from datasets import load_dataset


RESULT_PATH = Path("results/bm25_results.json")
OUTPUT_PATH = Path("results/bm25_evaluation.csv")

DATASET_REVISION = "78f471bf655a3137b2e8a75af1501690ec009ec3"


def extract_modified_files(patch):
    """Extract Python source files modified by a reference patch."""

    files = set()

    for line in patch.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:].strip()

            if path.endswith(".py"):
                files.add(path)

    return files


def main():

    print("Loading BM25 results...")

    with open(RESULT_PATH, "r", encoding="utf-8") as f:
        bm25_results = json.load(f)

    print("Loading SWE-bench Verified dataset...")

    dataset = load_dataset(
        "SWE-bench/SWE-bench_Verified",
        split="test",
        revision=DATASET_REVISION,
    )

    tasks = {
        row["instance_id"]: row
        for row in dataset
    }

    evaluation = []

    for result in bm25_results:

        task_id = result["instance_id"]

        if task_id not in tasks:
            raise ValueError(f"Task not found: {task_id}")

        # Reference patch is used only for offline evaluation.
        patch = tasks[task_id]["patch"]

        true_files = extract_modified_files(patch)

        # Evaluate source-code localization, not test-file changes.
        true_files = {
            path for path in true_files
            if not (
                path.startswith("tests/")
                or path.startswith("testing/")
                or "/tests/" in path
            )
        }

        predicted_files = {
            item["path"]
            for item in result["ranked_files"][:10]
        }

        matched = true_files & predicted_files

        recall = (
            len(matched) / len(true_files)
            if true_files else None
        )

        hit = (
            int(len(matched) > 0)
            if true_files else None
        )

        evaluation.append({
            "instance_id": task_id,
            "num_true_files": len(true_files),
            "num_matched": len(matched),
            "recall_at_10": recall,
            "hit_at_10": hit,
            "true_files": "; ".join(sorted(true_files)),
            "matched_files": "; ".join(sorted(matched)),
        })

        print(f"\n{task_id}")
        print(f"  True files: {sorted(true_files)}")
        print(f"  Matched: {sorted(matched)}")
        print(f"  Recall@10: {recall}")
        print(f"  Hit@10: {hit}")

    # Save evaluation results.
    OUTPUT_PATH.parent.mkdir(exist_ok=True)

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "instance_id",
                "num_true_files",
                "num_matched",
                "recall_at_10",
                "hit_at_10",
                "true_files",
                "matched_files",
            ],
        )

        writer.writeheader()
        writer.writerows(evaluation)

    valid = [
        row for row in evaluation
        if row["recall_at_10"] is not None
    ]

    mean_recall = (
        sum(row["recall_at_10"] for row in valid) / len(valid)
        if valid else 0
    )

    hit_rate = (
        sum(row["hit_at_10"] for row in valid) / len(valid)
        if valid else 0
    )

    print("\n" + "=" * 60)
    print("BM25 Evaluation Summary")
    print("=" * 60)

    print(f"Total tasks: {len(evaluation)}")
    print(f"Evaluated tasks: {len(valid)}")
    print(f"Mean Recall@10: {mean_recall:.2%}")
    print(f"Hit@10: {hit_rate:.2%}")
    print(f"Results saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()