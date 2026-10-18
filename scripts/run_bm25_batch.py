"""Run BM25 retrieval on the 20 SWE-bench development tasks."""

import csv
import json
import subprocess
import sys
from pathlib import Path

from datasets import load_dataset

from src.localization.keyword import BM25Retriever
from src.repository.indexer import RepositoryIndex


# 20 tasks selected by Role 5
TASK_IDS = [
    # Django
    "django__django-11133",
    "django__django-12262",
    "django__django-13158",
    "django__django-13417",
    "django__django-14017",
    "django__django-14539",

    # SymPy
    "sympy__sympy-23262",
    "sympy__sympy-17630",
    "sympy__sympy-21379",
    "sympy__sympy-19346",
    "sympy__sympy-20154",
    "sympy__sympy-20438",

    # Sphinx
    "sphinx-doc__sphinx-8595",
    "sphinx-doc__sphinx-7462",
    "sphinx-doc__sphinx-9673",
    "sphinx-doc__sphinx-8721",

    # pytest
    "pytest-dev__pytest-7571",
    "pytest-dev__pytest-7205",
    "pytest-dev__pytest-7490",
    "pytest-dev__pytest-10356",
]

CACHE_DIR = Path(".swebench_cache/index")
RESULT_DIR = Path("results")
RESULT_DIR.mkdir(exist_ok=True)


def main():

    print("Loading SWE-bench Verified dataset...")

    dataset = load_dataset(
        "SWE-bench/SWE-bench_Verified",
        split="test",
        revision="78f471bf655a3137b2e8a75af1501690ec009ec3",
    )

    tasks = {
        row["instance_id"]: row
        for row in dataset
        if row["instance_id"] in TASK_IDS
    }

    all_results = []
    summary = []

    for i, task_id in enumerate(TASK_IDS, start=1):

        print(f"\n[{i}/20] Processing {task_id}")

        index_path = CACHE_DIR / f"{task_id}.json"

        try:
            # Build index if not cached
            if not index_path.exists():

                subprocess.run(
                    [
                        sys.executable,
                        "scripts/build_index.py",
                        "--task",
                        task_id,
                    ],
                    check=True,
                )

            # Load index
            index = RepositoryIndex.load(index_path)

            # Get original issue description
            query = tasks[task_id]["problem_statement"]

            # Run BM25
            retriever = BM25Retriever(index)
            results = retriever.retrieve(query, top_k=10)

            ranked_files = [
                {
                    "rank": rank,
                    "path": path,
                    "bm25_score": round(score, 4),
                }
                for rank, (path, score)
                in enumerate(results, start=1)
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
            print(f"  Retrieved: {len(ranked_files)}")

            for item in ranked_files:
                print(
                    f"  {item['rank']:2d}. "
                    f"{item['path']} "
                    f"({item['bm25_score']:.4f})"
                )

        except Exception as e:

            print(f"  ERROR: {e}")

            summary.append({
                "instance_id": task_id,
                "status": "failed",
                "num_indexed_files": 0,
                "num_records": 0,
                "num_retrieved": 0,
                "top1_file": "",
                "top1_score": 0,
            })

    # Save JSON for Role 2
    json_path = RESULT_DIR / "bm25_results.json"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    # Save CSV summary
    csv_path = RESULT_DIR / "bm25_summary.csv"

    with open(csv_path, "w", newline="", encoding="utf-8") as f:

        writer = csv.DictWriter(
            f,
            fieldnames=[
                "instance_id",
                "status",
                "num_indexed_files",
                "num_records",
                "num_retrieved",
                "top1_file",
                "top1_score",
            ],
        )

        writer.writeheader()
        writer.writerows(summary)

    print("\n" + "=" * 60)
    print("BM25 batch testing completed!")
    print(f"Successful tasks: {sum(x['status'] == 'success' for x in summary)}/20")
    print(f"JSON results: {json_path}")
    print(f"CSV summary: {csv_path}")


if __name__ == "__main__":
    main()