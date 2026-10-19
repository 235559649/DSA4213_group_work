"""Build, query, save and load the index of a Python repository."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import posixpath
import re
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from src.repository.ast_parser import (
    DEFAULT_MAX_TEXT_CHARS,
    FileParseError,
    ImportStatement,
    decode_source,
    module_names,
    parse_file,
)
from src.repository.models import (
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
    # path -> repository files it imports (sorted); files without internal imports are omitted
    imports: dict[str, list[str]] = field(default_factory=dict)

    _by_id: dict[str, IndexRecord] = field(init=False, repr=False, compare=False)
    _by_path: dict[str, list[IndexRecord]] = field(init=False, repr=False, compare=False)
    _imported_by: dict[str, list[str]] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self._by_id = {r.id: r for r in self.records}
        self._by_path = {}
        for r in self.records:
            self._by_path.setdefault(r.path, []).append(r)
        self._imported_by = {}
        for importer in sorted(self.imports):
            for target in self.imports[importer]:
                self._imported_by.setdefault(target, []).append(importer)

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
            if r.symbol is not None and (r.symbol == name or r.symbol.endswith("." + name))
        ]

    # ----- import graph -----

    def imports_of(self, path: str) -> list[str]:
        """Repository files that `path` imports."""
        return list(self.imports.get(to_repo_path(path) or "", []))

    def imported_by(self, path: str) -> list[str]:
        """Repository files that import `path`."""
        return list(self._imported_by.get(to_repo_path(path) or "", []))

    def neighbors(self, path: str) -> list[str]:
        """One-hop import neighbors: files `path` imports or is imported by, sorted."""
        path = to_repo_path(path) or ""
        return sorted((set(self.imports_of(path)) | set(self.imported_by(path))) - {path})

    def is_test_file(self, path: str) -> bool:
        records = self._by_path.get(to_repo_path(path) or "")
        return bool(records) and records[0].is_test

    # ----- persistence -----

    def digest(self) -> str:
        """SHA-256 of the indexed content (files, records, errors, imports), ignoring metadata.

        Two indexes with the same digest give the same lookups and retrieval
        text, wherever and whenever they were built.
        """
        content = {k: v for k, v in self.to_dict().items() if k in ("files", "records", "errors", "imports")}
        payload = json.dumps(content, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "metadata": self.metadata,
            "files": self.files,
            "records": [asdict(r) for r in self.records],
            "errors": [asdict(e) for e in self.errors],
            "imports": self.imports,
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
            imports={path: list(targets) for path, targets in data["imports"].items()},
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
    """Index every Python file under the directory `repo_root`.

    Files that cannot be read, decoded or parsed are listed in `errors` and
    skipped; they never abort the build.
    """
    root = Path(repo_root)
    if not root.is_dir():
        raise NotADirectoryError(f"not a directory: {root}")

    return index_sources(
        iter_python_files(root),
        read_bytes=lambda path: (root / path).read_bytes(),
        file_size=lambda path: (root / path).stat().st_size,
        max_file_bytes=max_file_bytes,
        max_text_chars=max_text_chars,
        metadata={"repo_name": root.resolve().name},
    )


def index_sources(
    paths: Iterable[str],
    *,
    read_bytes: Callable[[str], bytes],
    file_size: Callable[[str], int],
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
    metadata: dict | None = None,
) -> RepositoryIndex:
    """Index the given repo-relative paths, reading them through callbacks.

    `build_index` reads from a directory; `src.repository.swebench` reads
    straight from git objects. Both produce identical indexes for identical
    files. `read_bytes` and `file_size` may raise OSError.
    """
    records: list[IndexRecord] = []
    errors: list[ParseError] = []
    files = sorted(paths)
    modules = module_names(files)
    raw_imports: dict[str, list[ImportStatement]] = {}

    for rel_path in files:
        try:
            size = file_size(rel_path)
            if size > max_file_bytes:
                errors.append(
                    ParseError(rel_path, TOO_LARGE, f"{size} bytes > limit {max_file_bytes}")
                )
                continue
            data = read_bytes(rel_path)
        except OSError as exc:
            errors.append(ParseError(rel_path, READ_ERROR, str(exc)))
            continue

        try:
            source = decode_source(data)
            parsed = parse_file(
                source, rel_path, module=modules[rel_path], max_text_chars=max_text_chars
            )
        except FileParseError as exc:
            errors.append(ParseError(rel_path, exc.kind, exc.message, exc.line))
            continue
        records.extend(parsed.records)
        raw_imports[rel_path] = parsed.imports

    imports = resolve_imports(raw_imports, modules)

    metadata = {
        **(metadata or {}),
        "python_version": platform.python_version(),
        "max_file_bytes": max_file_bytes,
        "max_text_chars": max_text_chars,
        "num_files": len(files),
        "num_records": len(records),
        "num_errors": len(errors),
        "num_import_edges": sum(len(targets) for targets in imports.values()),
    }
    return RepositoryIndex(
        records=records, errors=errors, files=files, metadata=metadata, imports=imports
    )


def resolve_imports(
    raw_imports: dict[str, list[ImportStatement]], modules: dict[str, str]
) -> dict[str, list[str]]:
    """Map import statements to repository files; drop everything external.

    `from a.b import c` points to a/b/c.py when `c` is a submodule, otherwise
    to the module a.b where `c` is defined. `import a.b` points to a.b only,
    not to the parent package a. Names claimed by two files of the same kind
    (e.g. two top-level `conftest.py` in different non-package directories)
    are ambiguous and not resolved. A package (`x/__init__.py`) wins over a
    module (`x.py`), as in Python.
    """
    by_module: dict[str, str] = {}
    ambiguous: set[str] = set()
    for path in sorted(modules):
        name = modules[path]
        if not name:
            continue
        if name not in by_module:
            by_module[name] = path
            continue
        is_package = path.endswith("__init__.py")
        if is_package != by_module[name].endswith("__init__.py"):
            if is_package:
                by_module[name] = path
        else:
            ambiguous.add(name)
    for name in ambiguous:
        del by_module[name]

    resolved = {}
    for path, statements in raw_imports.items():
        targets = set()
        for statement in statements:
            base = by_module.get(statement.module)
            if not statement.names:
                if base:
                    targets.add(base)
                continue
            for name in statement.names:
                submodule = by_module.get(f"{statement.module}.{name}") if name != "*" else None
                if submodule:
                    targets.add(submodule)
                elif base:
                    targets.add(base)
        targets.discard(path)
        if targets:
            resolved[path] = sorted(targets)
    return resolved


def is_indexed_path(path: str) -> bool:
    """Whether a repo-relative POSIX path is a .py file outside skipped directories.

    Symlinks are not visible from the path; callers skip them separately.
    """
    *dirs, filename = path.split("/")
    return filename.endswith(".py") and not any(
        _is_skipped_dir(d, at_root=i == 0) for i, d in enumerate(dirs)
    )


def iter_python_files(root: Path):
    """Yield repo-relative POSIX paths of .py files under `root`.

    Skips hidden directories, excluded directories, *.egg-info and symlinks.
    """
    for dirpath, dirnames, filenames in os.walk(root):
        at_root = Path(dirpath) == root
        dirnames[:] = [
            d
            for d in dirnames
            if not _is_skipped_dir(d, at_root)
            and not os.path.islink(os.path.join(dirpath, d))
        ]
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        for filename in filenames:
            if filename.endswith(".py") and not os.path.islink(os.path.join(dirpath, filename)):
                yield filename if rel_dir == "." else f"{rel_dir}/{filename}"


def _is_skipped_dir(name: str, at_root: bool) -> bool:
    return (
        name.startswith(".")
        or name in EXCLUDED_DIRS
        or name.endswith(".egg-info")
        or (at_root and name in EXCLUDED_ROOT_DIRS)
    )


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
