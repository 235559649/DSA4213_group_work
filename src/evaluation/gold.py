"""Reference locations for offline evaluation. Evaluation side only.

The localization modules and the agent must never import this module: it
reads the reference patch, which the evaluation protocol reserves for
evaluation. Only the list of files each reference patch touches is kept,
cached in `<cache>/eval/`; the patch text itself is never stored.

The localization target set G of a task (protocol section 3.2) is the set of
Python source files the reference patch modifies, excluding tests,
documentation, and files that do not exist at base_commit (added files
cannot be ranked).
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path

from src.repository import swebench
from src.repository.ast_parser import is_test_path
from src.repository.indexer import RepositoryIndex

_DIFF_HEADER = re.compile(r"^diff --git a/(.+?) b/(.+)$")
_DOC_DIRS = {"doc", "docs"}

MODIFIED, ADDED, DELETED, RENAMED = "modified", "added", "deleted", "renamed"


@dataclass(frozen=True)
class ChangedFile:
    path: str
    status: str  # MODIFIED, ADDED, DELETED or RENAMED


def changed_files(patch: str) -> list[ChangedFile]:
    """Files a unified git diff touches, with how each was changed."""
    files: list[ChangedFile] = []
    path, status = None, MODIFIED
    for line in patch.splitlines():
        header = _DIFF_HEADER.match(line)
        if header:
            if path is not None:
                files.append(ChangedFile(path, status))
            path, status = header.group(2), MODIFIED
        elif path is not None:
            if line.startswith("new file mode"):
                status = ADDED
            elif line.startswith("deleted file mode"):
                status = DELETED
            elif line.startswith("rename from"):
                status = RENAMED
    if path is not None:
        files.append(ChangedFile(path, status))
    return files


def reference_files(
    cache_dir: str | os.PathLike | None = None, *, revision: str = swebench.DATASET_REVISION
) -> dict[str, list[ChangedFile]]:
    """instance_id -> files the reference patch touches, for the pinned dataset."""
    cache = swebench.resolve_cache_dir(cache_dir)
    cached = cache / "eval" / f"reference_files@{revision}.json"
    if not cached.exists():
        _download_reference_files(revision, cached)
    with open(cached, encoding="utf-8") as f:
        data = json.load(f)
    return {iid: [ChangedFile(**entry) for entry in entries] for iid, entries in data.items()}


def target_files(
    changes: list[ChangedFile], index: RepositoryIndex
) -> tuple[list[str], dict[str, str]]:
    """The target set G and, for every other changed file, why it was left out."""
    indexed = set(index.files)
    targets, excluded = [], {}
    for change in changes:
        path = change.path
        if not path.endswith(".py"):
            excluded[path] = "not_python"
        elif change.status != MODIFIED:
            excluded[path] = change.status
        elif is_test_path(path):
            excluded[path] = "test"
        elif path.split("/", 1)[0] in _DOC_DIRS:
            excluded[path] = "documentation"
        elif path not in indexed:
            excluded[path] = "not_indexed"
        else:
            targets.append(path)
    return sorted(set(targets)), excluded


def _download_reference_files(revision: str, cached: Path) -> None:
    try:
        import pyarrow.parquet as pq
    except ImportError:
        raise ImportError("reading reference patches needs pyarrow: pip install pyarrow") from None

    cached.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".parquet", dir=cached.parent)
    os.close(fd)
    try:
        swebench._fetch(swebench.DATASET_URL.format(revision=revision), Path(tmp))
        rows = pq.read_table(tmp, columns=["instance_id", "patch"]).to_pylist()
    finally:
        os.unlink(tmp)

    data = {
        row["instance_id"]: [vars(change) for change in changed_files(row["patch"] or "")]
        for row in rows
    }
    partial = cached.with_name(cached.name + ".partial")
    partial.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    partial.replace(cached)
