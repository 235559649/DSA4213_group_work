"""Run full positive BM25 rankings on the 20 SWE-bench development tasks."""

import csv
import json
import platform
import time
from pathlib import Path


from src.localization.keyword import BM25Retriever
from src.repository.indexer import RepositoryIndex
from src.repository.swebench import build_task_index, load_task, resolve_cache_dir


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
            build_task_index(task_id)  # builds and caches on first use

            # Time only loading the cached index, as run_structural.py does, so a
            # first build is not counted twice (it is index_build_seconds).
            started = time.perf_counter()
            index = RepositoryIndex.load(resolve_cache_dir() / "index" / f"{task_id}.json")
            index_load_seconds = time.perf_counter() - started
            query = task.problem_statement

            started = time.perf_counter()
            retriever = BM25Retriever(index)
            bm25_init_seconds = time.perf_counter() - started

            # IMPORTANT: no top_k cutoff; save ALL positive-scoring files.
            started = time.perf_counter()
            results = retriever.retrieve(query)
            bm25_seconds = time.perf_counter() - started
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
                "timing": {
                    "index_build_seconds": index.metadata.get("build_seconds"),
                    "index_load_seconds": round(index_load_seconds, 4),
                    "bm25_init_seconds": round(bm25_init_seconds, 4),
                    "bm25_seconds": round(bm25_seconds, 4),
                    "measured_on": f"{platform.system()} {platform.machine()}, Python {platform.python_version()}",
                },
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
            print(f"  BM25 initialization: {bm25_init_seconds:.4f} s; retrieval: {bm25_seconds:.4f} s")
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
