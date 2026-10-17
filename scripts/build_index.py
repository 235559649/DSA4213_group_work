"""Build the repository index and print a summary.

Usage:
    python scripts/build_index.py <repo_path> [-o index.json]
    python scripts/build_index.py --task django__django-11133 [more ids...]

With --task, the SWE-bench task's repository is downloaded at its base_commit
and the index is cached under the SWE-bench cache (see src/repository/swebench.py).
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.repository.ast_parser import DEFAULT_MAX_TEXT_CHARS  # noqa: E402
from src.repository.indexer import DEFAULT_MAX_FILE_BYTES, RepositoryIndex, build_index  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", nargs="?", help="path to a local repository checkout")
    parser.add_argument(
        "--task", nargs="+", metavar="INSTANCE_ID", help="SWE-bench Verified instance id(s)"
    )
    parser.add_argument("-o", "--output", help="also write the index as JSON to this file")
    parser.add_argument("--cache-dir", help="SWE-bench cache directory (default: .swebench_cache)")
    parser.add_argument("--rebuild", action="store_true", help="ignore cached task indexes")
    parser.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    parser.add_argument("--max-text-chars", type=int, default=DEFAULT_MAX_TEXT_CHARS)
    args = parser.parse_args(argv)

    if (args.repo is None) == (args.task is None):
        parser.error("give either a repository path or --task")
    if args.output and args.task and len(args.task) > 1:
        parser.error("-o works with a single --task")
    limits = {"max_file_bytes": args.max_file_bytes, "max_text_chars": args.max_text_chars}

    if args.repo:
        index = build_index(args.repo, **limits)
        print_summary(index, args.repo)
        if args.output:
            index.save(args.output)
            print(f"saved to {args.output}")
        return 0

    from src.repository.swebench import build_task_index, load_task, resolve_cache_dir

    cache = resolve_cache_dir(args.cache_dir)
    for instance_id in args.task:
        task = load_task(instance_id, cache)
        index = build_task_index(instance_id, cache_dir=cache, rebuild=args.rebuild, **limits)
        print_summary(index, f"{instance_id} ({task.repo} @ {task.base_commit[:12]})")
        print(f"cached:  {cache / 'index' / (instance_id + '.json')}")
        if args.output:
            index.save(args.output)
            print(f"saved to {args.output}")
        print()
    return 0


def print_summary(index: RepositoryIndex, title: str) -> None:
    types = Counter(r.symbol_type for r in index.records)
    print(f"== {title}")
    print(f"files:   {len(index.files)}")
    print(f"records: {len(index.records)} " + ", ".join(f"{t}={n}" for t, n in sorted(types.items())))
    print(f"errors:  {len(index.errors)}")
    for error in index.errors[:20]:
        where = f"{error.path}:{error.line}" if error.line else error.path
        print(f"  [{error.kind}] {where}: {error.message}")
    if len(index.errors) > 20:
        print(f"  ... and {len(index.errors) - 20} more")


if __name__ == "__main__":
    sys.exit(main())
