"""Test BM25 retrieval on a real SWE-bench task."""

from datasets import load_dataset

from src.localization.keyword import BM25Retriever
from src.repository.indexer import RepositoryIndex


TASK_ID = "django__django-11133"

INDEX_PATH = f".swebench_cache/index/{TASK_ID}.json"


def main():

    # 1. Load the real problem statement
    print("Loading SWE-bench problem statement...")

    dataset = load_dataset(
        "princeton-nlp/SWE-bench_Verified",
        split="test",
    )

    task = next(
        row for row in dataset
        if row["instance_id"] == TASK_ID
    )

    query = task["problem_statement"]

    # 2. Load repository index
    print("Loading Django repository index...")

    index = RepositoryIndex.load(INDEX_PATH)

    # 3. Run BM25
    print("Running BM25...")

    retriever = BM25Retriever(index)

    results = retriever.retrieve(query, top_k=10)

    # 4. Print results
    print("\nTop 10 BM25 Results:")
    print("-" * 80)

    for rank, (path, score) in enumerate(results, start=1):
        print(f"{rank:2d}. {path}")
        print(f"    BM25 score: {score:.4f}")


if __name__ == "__main__":
    main()