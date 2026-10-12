"""Build, query, save and load the index of a Python repository."""

from __future__ import annotations

import json
import os
import platform
import posixpath
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from src.repository.ast_parser import (
    DEFAULT_MAX_TEXT_CHARS,
    FileParseError,
    decode_source,
    parse_source,
)
from src.repository.models import (
    MODULE,
    READ_ERROR,
    SCHEMA_VERSION,
    TOO_LARGE,
    IndexRecord,
    ParseError,
)

DEFAULT_MAX_FILE_BYTES = 2_000_000

# Skipped at any depth.
EXCLUDED_DIRS = frozenset({"__pycache__", "node_modules", "site-packages"})
# Skipped only directly under the repository root, since a package may
# legitimately contain e.g. a "build" subpackage.
EXCLUDED_ROOT_DIRS = frozenset({"build", "dist", "env", "venv"})

_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:/")


@dataclass
class RepositoryIndex:
    records: list[IndexRecord]
    errors: list[ParseError]
    files: list[str]  # every Python file visited, parsed or not
    metadata: dict = field(default_factory=dict)

    _by_id: dict[str, IndexRecord] = field(init=False, repr=False, compare=False)
    _by_path: dict[str, list[IndexRecord]] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._by_id = {r.id: r for r in self.records}
        self._by_path = {}
        for r in self.records:
            self._by_path.setdefault(r.path, []).append(r)

    # ----- lookups -----

    def get(self, record_id: str) -> IndexRecord | None:
        return self._by_id.get(record_id)

    def records_in_file(self, path: str) -> list[IndexRecord]:
        return list(self._by_path.get(to_repo_path(path) or "", []))

    def children(self, record_id: str) -> list[IndexRecord]:
        record = self._by_id.get(record_id)
        if record is None:
            return []
        return [r for r in self._by_path[record.path] if r.parent == record_id]

    def find_enclosing(self, path: str, line: int) -> IndexRecord | None:
        """The innermost record containing `line`, e.g. for a traceback frame.

        Falls back to the module record for module-level lines. Returns None
        if the file is not indexed or the line is outside the file.
        """
        candidates = [r for r in self.records_in_file(path) if r.contains(line)]
        if not candidates:
            return None
        return max(candidates, key=lambda r: (r.start_line, -r.end_line))

    def find_by_name(self, name: str) -> list[IndexRecord]:
        """Records whose name or dotted symbol suffix equals `name`.

        `find_by_name("total")` and `find_by_name("Cart.total")` both match
        the `Cart.total` method.
        """
        return [
            r
            for r in self.records
            if r.kind != MODULE and (r.symbol == name or r.symbol.endswith("." + name))
        ]

    # ----- persistence -----

    def to_dict(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "metadata": self.metadata,
            "files": self.files,
            "records": [asdict(r) for r in self.records],
            "errors": [asdict(e) for e in self.errors],
        }

    @classmethod
    def from_dict(cls, data: dict) -> RepositoryIndex:
        version = data.get("schema_version")
        if version != SCHEMA_VERSION:
            raise ValueError(f"index schema version {version!r}, expected {SCHEMA_VERSION}")
        return cls(
            records=[IndexRecord(**r) for r in data["records"]],
            errors=[ParseError(**e) for e in data["errors"]],
            files=list(data["files"]),
            metadata=dict(data.get("metadata", {})),
        )

    def save(self, path: str | os.PathLike) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, separators=(",", ":"))

    @classmethod
    def load(cls, path: str | os.PathLike) -> RepositoryIndex:
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))


def build_index(
    repo_root: str | os.PathLike,
    *,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
) -> RepositoryIndex:
    """Index every Python file under `repo_root`.

    Files that cannot be read, decoded or parsed are listed in `errors` and
    skipped; they never abort the build.
    """
    root = Path(repo_root)
    if not root.is_dir():
        raise NotADirectoryError(f"not a directory: {root}")

    records: list[IndexRecord] = []
    errors: list[ParseError] = []
    files = list(iter_python_files(root))

    for rel_path in files:
        full_path = root / rel_path
        try:
            size = full_path.stat().st_size
            if size > max_file_bytes:
                errors.append(
                    ParseError(rel_path, TOO_LARGE, f"{size} bytes > limit {max_file_bytes}")
                )
                continue
            data = full_path.read_bytes()
        except OSError as exc:
            errors.append(ParseError(rel_path, READ_ERROR, str(exc)))
            continue

        try:
            source = decode_source(data)
            records.extend(parse_source(source, rel_path, max_text_chars=max_text_chars))
        except FileParseError as exc:
            errors.append(ParseError(rel_path, exc.kind, exc.message, exc.line))

    metadata = {
        "repo_name": root.resolve().name,
        "python_version": platform.python_version(),
        "max_file_bytes": max_file_bytes,
        "max_text_chars": max_text_chars,
        "num_files": len(files),
        "num_records": len(records),
        "num_errors": len(errors),
    }
    return RepositoryIndex(records=records, errors=errors, files=files, metadata=metadata)


def iter_python_files(root: Path):
    """Yield repo-relative POSIX paths of .py files, in sorted order.

    Skips hidden directories, excluded directories, *.egg-info and symlinks.
    """
    for dirpath, dirnames, filenames in os.walk(root):
        at_root = Path(dirpath) == root
        dirnames[:] = sorted(
            d
            for d in dirnames
            if not d.startswith(".")
            and d not in EXCLUDED_DIRS
            and not d.endswith(".egg-info")
            and not (at_root and d in EXCLUDED_ROOT_DIRS)
            and not os.path.islink(os.path.join(dirpath, d))
        )
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        for filename in sorted(filenames):
            if filename.endswith(".py") and not os.path.islink(os.path.join(dirpath, filename)):
                yield filename if rel_dir == "." else f"{rel_dir}/{filename}"


def to_repo_path(path: str | os.PathLike, repo_root: str | os.PathLike | None = None) -> str | None:
    """Normalize a path to the repo-relative POSIX form used by the index.

    `repo_root` strips an absolute prefix, e.g. a container checkout:
    `to_repo_path("/testbed/shop/pricing.py", "/testbed") == "shop/pricing.py"`.
    Returns None for paths outside the repository.
    """
    p = str(path).replace("\\", "/")
    if repo_root is not None:
        root = str(repo_root).replace("\\", "/").rstrip("/")
        if p.startswith(root + "/"):
            p = p[len(root) + 1 :]
    if p.startswith("/") or _WINDOWS_DRIVE.match(p):
        return None
    p = posixpath.normpath(p)
    if p == "." or p == ".." or p.startswith("../"):
        return None
    return p
