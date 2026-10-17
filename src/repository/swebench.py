"""Build the repository index for a SWE-bench Verified task from its ID.

    from src.repository.swebench import build_task_index, load_task

    task = load_task("django__django-11133")    # repo, base_commit, problem_statement, ...
    index = build_task_index("django__django-11133")

Everything is downloaded on first use and cached:

    <cache>/tasks/<dataset>@<revision>.jsonl   task fields (whitelist only)
    <cache>/repos/<owner>__<name>.git           one bare clone per repository
    <cache>/index/<instance_id>.json             one index per task

The cache defaults to `.swebench_cache/` in the project root; set the
SWEBENCH_CACHE_DIR environment variable or pass `cache_dir` to move it.

Source files are read straight from git objects at `base_commit`, so nothing
is checked out: the index sees exactly the files of that commit, the same
files the task container has under /testbed (minus files generated at
install time, such as a setuptools-scm `_version.py`).

Only the fields in TASK_FIELDS are ever read from the dataset. The reference
patch, test patch, FAIL_TO_PASS / PASS_TO_PASS and hints are evaluation-only
or excluded by the evaluation protocol, and never reach the cache.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from src.repository.ast_parser import DEFAULT_MAX_TEXT_CHARS
from src.repository.indexer import (
    DEFAULT_MAX_FILE_BYTES,
    RepositoryIndex,
    index_sources,
    is_indexed_path,
)

DATASET = "SWE-bench/SWE-bench_Verified"
# Pinned in docs/benchmark/candidate_pool_v0.1.md.
DATASET_REVISION = "78f471bf655a3137b2e8a75af1501690ec009ec3"
DATASET_FILE = "data/test-00000-of-00001.parquet"
DATASET_URL = f"https://huggingface.co/datasets/{DATASET}/resolve/{{revision}}/{DATASET_FILE}"

GIT_URL = "https://github.com/{repo}.git"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CACHE_ENV_VAR = "SWEBENCH_CACHE_DIR"

_INSTANCE_ID = re.compile(r"^[A-Za-z0-9_.-]+$")
_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


@dataclass(frozen=True)
class Task:
    """The task fields localization may use. Nothing evaluation-only."""

    instance_id: str
    repo: str  # "django/django"
    base_commit: str
    problem_statement: str  # the original issue text, used as the retrieval query
    version: str  # the dataset's repository version group, e.g. "3.0"
    created_at: str


TASK_FIELDS = tuple(f.name for f in fields(Task))


# ----- cache -----


def resolve_cache_dir(cache_dir: str | os.PathLike | None = None) -> Path:
    cache = Path(cache_dir or os.environ.get(CACHE_ENV_VAR) or PROJECT_ROOT / ".swebench_cache")
    cache.mkdir(parents=True, exist_ok=True)
    # Keep downloads out of git wherever the cache lives.
    ignore = cache / ".gitignore"
    if not ignore.exists():
        ignore.write_text("*\n", encoding="utf-8")
    return cache


# ----- tasks -----


def load_tasks(
    cache_dir: str | os.PathLike | None = None, *, revision: str = DATASET_REVISION
) -> dict[str, Task]:
    """All tasks of the pinned dataset revision, keyed by instance_id."""
    cache = resolve_cache_dir(cache_dir)
    tasks_file = cache / "tasks" / f"{DATASET.replace('/', '__')}@{revision}.jsonl"
    if not tasks_file.exists():
        _download_tasks(revision, tasks_file)

    tasks = {}
    with open(tasks_file, encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            task = Task(**{name: row[name] for name in TASK_FIELDS})
            tasks[task.instance_id] = task
    return tasks


def load_task(instance_id: str, cache_dir: str | os.PathLike | None = None) -> Task:
    tasks = load_tasks(cache_dir)
    if instance_id not in tasks:
        raise KeyError(f"{instance_id!r} is not a task in {DATASET}@{DATASET_REVISION[:8]}")
    return tasks[instance_id]


def _download_tasks(revision: str, tasks_file: Path) -> None:
    """Download the dataset, keep only TASK_FIELDS, and delete the download."""
    try:
        import pyarrow.parquet as pq
    except ImportError:
        raise ImportError("loading SWE-bench tasks needs pyarrow: pip install pyarrow") from None

    tasks_file.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".parquet", dir=tasks_file.parent)
    os.close(fd)
    try:
        _fetch(DATASET_URL.format(revision=revision), Path(tmp))
        rows = pq.read_table(tmp, columns=list(TASK_FIELDS)).to_pylist()
    finally:
        os.unlink(tmp)

    partial = tasks_file.with_name(tasks_file.name + ".partial")
    with open(partial, "w", encoding="utf-8") as f:
        for row in rows:
            task = Task(**{name: "" if row[name] is None else str(row[name]) for name in TASK_FIELDS})
            f.write(json.dumps(asdict(task), ensure_ascii=False) + "\n")
    partial.replace(tasks_file)


def _fetch(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=120) as response, open(dest, "wb") as out:
        shutil.copyfileobj(response, out)


# ----- source -----


def ensure_repo(repo: str, cache_dir: str | os.PathLike | None = None) -> Path:
    """Path to a bare clone of `repo` ("owner/name"), cloning it on first use."""
    if not _REPO.match(repo):
        raise ValueError(f"not an owner/name repository: {repo!r}")
    target = resolve_cache_dir(cache_dir) / "repos" / (repo.replace("/", "__") + ".git")
    if target.is_dir():
        return target

    partial = target.with_name(target.name + ".partial")
    if partial.exists():  # left over from an interrupted clone
        _rmtree(partial)
    partial.parent.mkdir(parents=True, exist_ok=True)
    _git("clone", "--bare", "--quiet", GIT_URL.format(repo=repo), str(partial))
    partial.rename(target)
    return target


def ensure_commit(repo_dir: Path, commit: str) -> None:
    """Make sure `commit` exists in the clone, fetching it if the clone predates it."""
    if _has_commit(repo_dir, commit):
        return
    _git("-C", str(repo_dir), "fetch", "--quiet", "origin", commit)
    if not _has_commit(repo_dir, commit):
        raise RuntimeError(f"commit {commit} not found in {repo_dir.name}")
    # Keep the fetched commit referenced so `git gc` never prunes it.
    _git("-C", str(repo_dir), "update-ref", f"refs/swebench/{commit}", commit)


def build_commit_index(
    repo: str,
    commit: str,
    *,
    cache_dir: str | os.PathLike | None = None,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
) -> RepositoryIndex:
    """Index the Python files of `repo` at `commit`, read from git objects."""
    repo_dir = ensure_repo(repo, cache_dir)
    ensure_commit(repo_dir, commit)

    entries = _list_python_blobs(repo_dir, commit)  # path -> (blob id, size)
    wanted = [blob for blob, size in entries.values() if size <= max_file_bytes]
    blobs = _read_blobs(repo_dir, wanted)

    return index_sources(
        entries,
        read_bytes=lambda path: blobs[entries[path][0]],
        file_size=lambda path: entries[path][1],
        max_file_bytes=max_file_bytes,
        max_text_chars=max_text_chars,
        metadata={"repo": repo, "commit": commit, "source": "git"},
    )


def build_task_index(
    instance_id: str,
    *,
    cache_dir: str | os.PathLike | None = None,
    rebuild: bool = False,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
) -> RepositoryIndex:
    """The index of a task's repository at its base_commit, cached per task."""
    if not _INSTANCE_ID.match(instance_id):
        raise ValueError(f"not a SWE-bench instance id: {instance_id!r}")
    cache = resolve_cache_dir(cache_dir)
    index_file = cache / "index" / f"{instance_id}.json"

    if index_file.exists() and not rebuild:
        try:
            index = RepositoryIndex.load(index_file)
        except (ValueError, KeyError, TypeError):
            index = None  # older schema or damaged file: rebuild below
        if (
            index is not None
            and index.metadata.get("max_file_bytes") == max_file_bytes
            and index.metadata.get("max_text_chars") == max_text_chars
        ):
            return index

    task = load_task(instance_id, cache)
    index = build_commit_index(
        task.repo,
        task.base_commit,
        cache_dir=cache,
        max_file_bytes=max_file_bytes,
        max_text_chars=max_text_chars,
    )
    index.metadata.update(
        instance_id=instance_id,
        dataset=DATASET,
        dataset_revision=DATASET_REVISION,
        index_sha256=index.digest(),
    )
    index.save(index_file)
    return index


# ----- git plumbing -----


def _git(*args: str, input: bytes | None = None) -> bytes:
    try:
        result = subprocess.run(["git", *args], input=input, capture_output=True)
    except FileNotFoundError:
        raise RuntimeError("git is not installed or not on PATH") from None
    if result.returncode != 0:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError(f"git {args[2] if args[0] == '-C' else args[0]} failed: {message}")
    return result.stdout


def _has_commit(repo_dir: Path, commit: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo_dir), "cat-file", "-e", f"{commit}^{{commit}}"], capture_output=True
    )
    return result.returncode == 0


def _list_python_blobs(repo_dir: Path, commit: str) -> dict[str, tuple[str, int]]:
    """Indexed .py files at `commit`: path -> (blob id, size). Skips symlinks and submodules."""
    out = _git("-C", str(repo_dir), "ls-tree", "-r", "-l", "-z", "--full-tree", commit)
    entries = {}
    for entry in out.split(b"\0"):
        if not entry:
            continue
        meta, raw_path = entry.split(b"\t", 1)
        mode, kind, blob, size = meta.split()
        if kind != b"blob" or mode == b"120000":  # submodules are "commit"; 120000 is a symlink
            continue
        path = raw_path.decode("utf-8", "replace")
        if is_indexed_path(path):
            entries[path] = (blob.decode(), int(size))
    return entries


def _read_blobs(repo_dir: Path, blob_ids: list[str]) -> dict[str, bytes]:
    """Read many blobs with a single `git cat-file --batch`."""
    unique = list(dict.fromkeys(blob_ids))  # identical files share a blob
    if not unique:
        return {}
    out = _git("-C", str(repo_dir), "cat-file", "--batch", input="\n".join(unique).encode() + b"\n")
    blobs, pos = {}, 0
    for blob in unique:  # output follows input order: "<id> blob <size>\n<content>\n"
        header_end = out.index(b"\n", pos)
        header = out[pos:header_end].split()
        if len(header) != 3:
            raise RuntimeError(f"git cat-file: unexpected output for {blob}: {header!r}")
        size = int(header[2])
        start = header_end + 1
        blobs[blob] = out[start : start + size]
        pos = start + size + 1
    return blobs


def _rmtree(path: Path) -> None:
    # Git marks object files read-only, which makes rmtree fail on Windows.
    def make_writable_and_retry(func, target, _exc):
        os.chmod(target, stat.S_IWRITE)
        func(target)

    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=make_writable_and_retry)
    else:
        shutil.rmtree(path, onerror=make_writable_and_retry)
