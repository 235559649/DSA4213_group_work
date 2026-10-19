"""Run full positive BM25 rankings on the 20 SWE-bench development tasks."""

import csv
import json
from pathlib import Path


from src.localization.keyword import BM25Retriever
from src.repository.swebench import build_task_index, load_task


# Development task IDs selected by Role 5 (unchanged).
TASK_IDS = [
    "django__django-11133",
    "django__django-12262",
    "django__django-13158",
    "django__django-13417",
    "django__django-14017",
    "django__django-14539",
    "sympy__sympy-23262",
    "sympy__sympy-17630",
    "sympy__sympy-21379",
    "sympy__sympy-19346",
    "sympy__sympy-20154",
    "sympy__sympy-20438",
    "sphinx-doc__sphinx-8595",
    "sphinx-doc__sphinx-7462",
    "sphinx-doc__sphinx-9673",
    "sphinx-doc__sphinx-8721",
    "pytest-dev__pytest-7571",
    "pytest-dev__pytest-7205",
    "pytest-dev__pytest-7490",
    "pytest-dev__pytest-10356",
]

RESULT_DIR = Path("results")


def main() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    print("Using the team's pinned SWE-bench task loader...")

    all_results = []
    summary = []

    for i, task_id in enumerate(TASK_IDS, start=1):
        print(f"\n[{i}/{len(TASK_IDS)}] Processing {task_id}")
        try:
            task = load_task(task_id)
            index = build_task_index(task_id)
            query = task.problem_statement
            retriever = BM25Retriever(index)

            # IMPORTANT: no top_k cutoff; save ALL positive-scoring files.
            results = retriever.retrieve(query)
            ranked_files = [
                {
                    "rank": rank,
                    "path": path,
                    "bm25_score": round(score, 4),
                }
                for rank, (path, score) in enumerate(results, start=1)
            ]

            all_results.append({
                "instance_id": task_id,
                "ranked_files": ranked_files,
            })
            summary.append({
                "instance_id": task_id,
                "status": "success",
                "num_indexed_files": len(index.files),
                "num_records": len(index.records),
                "num_retrieved": len(ranked_files),
                "top1_file": ranked_files[0]["path"] if ranked_files else "",
                "top1_score": ranked_files[0]["bm25_score"] if ranked_files else 0,
            })
            print(f"  Indexed files: {len(index.files)}")
            print(f"  Full positive ranking: {len(ranked_files)} files")
            print("  Preview (first 10 only; saved JSON contains ALL files):")
            for item in ranked_files[:10]:
                print(
                    f"  {item['rank']:2d}. {item['path']} "
                    f"({item['bm25_score']:.4f})"
                )
        except Exception as exc:
            print(f"  ERROR: {exc}")
            summary.append({
                "instance_id": task_id,
                "status": "failed",
                "num_indexed_files": 0,
                "num_records": 0,
                "num_retrieved": 0,
                "top1_file": "",
                "top1_score": 0,
            })

    json_path = Path("experiments/bm25_results.json")
json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(all_results, handle, indent=2, ensure_ascii=False)

    csv_path = RESULT_DIR / "bm25_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "instance_id", "status", "num_indexed_files", "num_records",
                "num_retrieved", "top1_file", "top1_score",
            ],
        )
        writer.writeheader()
        writer.writerows(summary)

    print("\n" + "=" * 60)
    print("BM25 batch testing completed!")
    print(f"Successful tasks: {sum(x['status'] == 'success' for x in summary)}/{len(TASK_IDS)}")
    print(f"Full ranking JSON: {json_path}")
    print(f"Summary CSV: {csv_path}")


if __name__ == "__main__":
    main()
