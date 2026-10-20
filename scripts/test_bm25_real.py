"""Smoke-test full positive BM25 retrieval on a pinned SWE-bench task."""

from src.localization.keyword import BM25Retriever
from src.repository.swebench import build_task_index, load_task

TASK_ID = "django__django-11133"


def main() -> None:
    print(f"Loading task {TASK_ID} using the team's pinned dataset...")
    task = load_task(TASK_ID)
    print("Loading/building repository index...")
    index = build_task_index(TASK_ID)

    print("Running BM25...")
    ranking = BM25Retriever(index).retrieve(task.problem_statement)
    print(f"Positive-scoring files: {len(ranking)}")
    print("Top 10 preview (full ranking retained in memory):")
    for rank, (path, score) in enumerate(ranking[:10], start=1):
        print(f"{rank:2d}. {path} | BM25 score: {score:.4f}")
    if not ranking:
        raise RuntimeError(f"BM25 returned no positive-scoring files for {TASK_ID}")


if __name__ == "__main__":
    main()
