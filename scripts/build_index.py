"""Build the repository index for a Python checkout and print a summary.

Usage:
    python scripts/build_index.py <repo_path> [-o index.json]
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.repository.ast_parser import DEFAULT_MAX_TEXT_CHARS  # noqa: E402
from src.repository.indexer import DEFAULT_MAX_FILE_BYTES, build_index  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("repo", help="path to the repository checkout")
    parser.add_argument("-o", "--output", help="write the index as JSON to this file")
    parser.add_argument("--max-file-bytes", type=int, default=DEFAULT_MAX_FILE_BYTES)
    parser.add_argument("--max-text-chars", type=int, default=DEFAULT_MAX_TEXT_CHARS)
    args = parser.parse_args(argv)

    index = build_index(
        args.repo, max_file_bytes=args.max_file_bytes, max_text_chars=args.max_text_chars
    )

    kinds = Counter(r.kind for r in index.records)
    print(f"files:   {len(index.files)}")
    print(f"records: {len(index.records)} " + ", ".join(f"{k}={n}" for k, n in sorted(kinds.items())))
    print(f"errors:  {len(index.errors)}")
    for error in index.errors[:20]:
        where = f"{error.path}:{error.line}" if error.line else error.path
        print(f"  [{error.kind}] {where}: {error.message}")
    if len(index.errors) > 20:
        print(f"  ... and {len(index.errors) - 20} more")

    if args.output:
        index.save(args.output)
        print(f"saved to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
