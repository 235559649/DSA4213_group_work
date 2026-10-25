"""Report repository index coverage for SWE-bench tasks as a Markdown table.

Usage:
    python scripts/index_coverage.py --tasks-from experiments/bm25_results.json
    python scripts/index_coverage.py django__django-11133 sympy__sympy-17630 --rebuild

Indexes come from the SWE-bench cache and are built on first use. With
--rebuild every index is rebuilt and the build time is reported (the
repositories must already be cloned for the time to exclude the download).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.repository.swebench import (  # noqa: E402
    build_task_index,
    ensure_commit,
    ensure_repo,
    list_python_blobs,
    load_task,
    resolve_cache_dir,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("instance_ids", nargs="*", help="SWE-bench instance ids")
    parser.add_argument("--tasks-from", help="a rankings JSON with one entry per instance_id")
    parser.add_argument("--rebuild", action="store_true", help="rebuild indexes and time them")
    parser.add_argument("--cache-dir", help="SWE-bench cache directory (default: .swebench_cache)")
    parser.add_argument("-o", "--output", help="write the Markdown here instead of stdout")
    args = parser.parse_args(argv)

    instance_ids = list(args.instance_ids)
    if args.tasks_from:
        with open(args.tasks_from, encoding="utf-8") as f:
            instance_ids += [task["instance_id"] for task in json.load(f)]
    if not instance_ids:
        parser.error("give instance ids or --tasks-from")
    cache = resolve_cache_dir(args.cache_dir)

    rows = []
    for instance_id in instance_ids:
        task = load_task(instance_id, cache)
        repo_dir = ensure_repo(task.repo, cache)
        ensure_commit(repo_dir, task.base_commit)
        started = time.perf_counter()
        index = build_task_index(instance_id, cache_dir=cache, rebuild=args.rebuild)
        seconds = time.perf_counter() - started
        source_bytes = sum(size for _, size in list_python_blobs(repo_dir, task.base_commit).values())
        types = Counter(r.symbol_type for r in index.records)
        rows.append(
            {
                "instance_id": instance_id,
                "commit": task.base_commit[:10],
                "files": len(index.files),
                "test_files": sum(1 for path in index.files if index.is_test_file(path)),
                "source_mb": source_bytes / 2**20,
                "records": len(index.records),
                "classes": types["class"],
                "functions": types["function"] + types["method"],
                "errors": index.errors,
                "import_edges": index.metadata["num_import_edges"],
                "files_with_imports": len(index.imports),
                "index_mb": (cache / "index" / f"{instance_id}.json").stat().st_size / 2**20,
                "seconds": seconds if args.rebuild else None,
            }
        )
        print(f"{instance_id}: {len(index.files)} files", file=sys.stderr)

    text = render(rows, timed=args.rebuild)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


def render(rows: list[dict], *, timed: bool) -> str:
    header = (
        "| Task | Commit | .py files | Test files | Source (MB) | Records | Classes "
        "| Functions / methods | Parse errors | Import edges | Index JSON (MB) |"
        + (" Build (s) |" if timed else "")
    )
    lines = [header, "|" + "---|" * (header.count("|") - 1)]
    for r in rows:
        errors = ", ".join(f"{e.path} ({e.kind})" for e in r["errors"]) or "0"
        line = (
            f"| {r['instance_id']} | `{r['commit']}` | {r['files']} | {r['test_files']} "
            f"| {r['source_mb']:.1f} | {r['records']} | {r['classes']} | {r['functions']} "
            f"| {errors} | {r['import_edges']} | {r['index_mb']:.1f} |"
        )
        if timed:
            line += f" {r['seconds']:.1f} |"
        lines.append(line)

    total_errors = sum(len(r["errors"]) for r in rows)
    lines += [
        "",
        f"Tasks: {len(rows)}. Python files indexed: {sum(r['files'] for r in rows)}. "
        f"Records: {sum(r['records'] for r in rows)}. Parse errors: {total_errors}. "
        f"Largest source tree: {max(r['source_mb'] for r in rows):.1f} MB.",
    ]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
