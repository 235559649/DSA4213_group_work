"""Turn the source of one Python file into index records."""

from __future__ import annotations

import ast
import io
import re
import tokenize
import warnings
from dataclasses import dataclass

from src.repository.models import (
    CLASS,
    DECODE_ERROR,
    FUNCTION,
    METHOD,
    MODULE,
    RECURSION_ERROR,
    SYNTAX_ERROR,
    IndexRecord,
)

DEFAULT_MAX_TEXT_CHARS = 2000

# The line breaks Python's tokenizer counts. str.splitlines() also splits on
# form feeds and other characters, which would shift line numbers.
_LINE_BREAK = re.compile(r"\r\n|\r|\n")

_DEFS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)

_TEST_DIRS = {"test", "tests", "testing"}


class FileParseError(Exception):
    """Raised when a file cannot be decoded or parsed."""

    def __init__(self, kind: str, message: str, line: int | None = None):
        super().__init__(message)
        self.kind = kind
        self.message = message
        self.line = line


def decode_source(data: bytes) -> str:
    """Decode file bytes the way Python does: BOM, coding cookie, else UTF-8."""
    # Python versions disagree on where null bytes are rejected; report them
    # the same way everywhere.
    if b"\x00" in data:
        raise FileParseError(SYNTAX_ERROR, "source code cannot contain null bytes")
    try:
        encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
        return data.decode(encoding)
    except (SyntaxError, UnicodeDecodeError, LookupError) as exc:
        raise FileParseError(DECODE_ERROR, str(exc)) from None


def module_name(path: str, package_dirs: set[str] | None = None) -> str:
    """The dotted name Python would import the file as.

    Without `package_dirs`, every directory counts as a package:
    'shop/pricing.py' -> 'shop.pricing', 'shop/utils/__init__.py' -> 'shop.utils'.

    With `package_dirs` (directories that contain an __init__.py), the name
    starts below the outermost directory that is not a package, so in a
    src layout 'src/_pytest/mark/structures.py' -> '_pytest.mark.structures',
    and in a non-package test directory 'testing/test_x.py' -> 'test_x'.
    """
    parts = path[: -len(".py")].split("/") if path.endswith(".py") else path.split("/")
    if package_dirs is not None:
        dirs = parts[:-1]
        top = len(dirs)
        while top > 0 and "/".join(dirs[:top]) in package_dirs:
            top -= 1
        parts = parts[top:]
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def module_names(paths) -> dict[str, str]:
    """Import names for a whole repository: path -> dotted module name."""
    package_dirs = {p[: -len("/__init__.py")] for p in paths if p.endswith("/__init__.py")}
    return {p: module_name(p, package_dirs) for p in paths}


def is_test_path(path: str) -> bool:
    parts = path.split("/")
    filename = parts[-1]
    return (
        any(part in _TEST_DIRS for part in parts[:-1])
        or filename.startswith("test_")
        or filename.endswith("_test.py")
        or filename in ("tests.py", "conftest.py")
    )


@dataclass(frozen=True)
class ImportStatement:
    """One import, with relative imports already made absolute.

    `import a.b` -> ImportStatement("a.b", ())
    `from a.b import c, d` -> ImportStatement("a.b", ("c", "d"))
    `from . import x` in package `shop` -> ImportStatement("shop", ("x",))
    """

    module: str
    names: tuple[str, ...]


@dataclass(frozen=True)
class ParsedFile:
    records: list[IndexRecord]  # module record first, then definitions in source order
    imports: list[ImportStatement]


def parse_source(
    source: str,
    path: str,
    *,
    module: str | None = None,
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
) -> list[IndexRecord]:
    """Parse one file and return its module record followed by its definitions.

    Raises FileParseError if the source is not valid Python for the running
    interpreter.
    """
    return parse_file(source, path, module=module, max_text_chars=max_text_chars).records


def parse_file(
    source: str,
    path: str,
    *,
    module: str | None = None,
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
) -> ParsedFile:
    """Parse one file into its records and its import statements.

    `module` is the file's import name (see `module_names`); it defaults to
    `module_name(path)`. Raises FileParseError like `parse_source`.
    """
    try:
        with warnings.catch_warnings():
            # e.g. invalid escape sequences in old code; not our concern here.
            warnings.simplefilter("ignore")
            tree = ast.parse(source, filename=path)
    except SyntaxError as exc:
        raise FileParseError(SYNTAX_ERROR, exc.msg or str(exc), exc.lineno) from None
    except ValueError as exc:  # null bytes, before Python 3.12
        raise FileParseError(SYNTAX_ERROR, str(exc)) from None
    except RecursionError:
        raise FileParseError(RECURSION_ERROR, "source is nested too deeply to parse") from None

    module = module_name(path) if module is None else module
    try:
        collector = _Collector(source, path, module, max_text_chars)
        return ParsedFile(collector.collect(tree), collector.imports)
    except RecursionError:
        raise FileParseError(RECURSION_ERROR, "source is nested too deeply to index") from None


class _Collector:
    def __init__(self, source: str, path: str, module: str, max_text_chars: int):
        self.lines = _LINE_BREAK.split(source)
        if self.lines[-1] == "":
            self.lines.pop()
        self.path = path
        self.module = module
        self.is_package = path == "__init__.py" or path.endswith("/__init__.py")
        self.is_test = is_test_path(path)
        self.max_text_chars = max_text_chars
        self.records: list[IndexRecord] = []
        self.imports: list[ImportStatement] = []
        self.ids: set[str] = set()

    def collect(self, tree: ast.Module) -> list[IndexRecord]:
        docstring = ast.get_docstring(tree) or ""
        text = "\n".join(
            part
            for part in (self.path, self.module, docstring, " ".join(_member_names(tree.body)))
            if part
        )
        self.records.append(
            IndexRecord(
                path=self.path,
                symbol=None,
                symbol_type=MODULE,
                start_line=1,
                end_line=max(1, len(self.lines)),
                retrieval_text=self._truncate(text),
                id=self._unique_id(self.path),
                module=self.module,
                name=None,
                parent=None,
                signature="",
                docstring=self._truncate(docstring),
                is_test=self.is_test,
            )
        )
        self._visit_children(tree, parent_id=self.records[0].id, prefix="", in_class=False)
        return self.records

    def _visit_children(self, node: ast.AST, parent_id: str, prefix: str, in_class: bool) -> None:
        # Definitions can sit inside if/try/with/for blocks, so walk every child
        # and only open a new scope at a def or class.
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _DEFS):
                self._add_definition(child, parent_id, prefix, in_class)
            elif isinstance(child, (ast.Import, ast.ImportFrom)):
                # Imports anywhere count: module level, inside functions,
                # under `try`, `if TYPE_CHECKING`, ...
                self._add_import(child)
            else:
                self._visit_children(child, parent_id, prefix, in_class)

    def _add_import(self, node: ast.Import | ast.ImportFrom) -> None:
        if isinstance(node, ast.Import):
            self.imports.extend(ImportStatement(alias.name, ()) for alias in node.names)
            return

        names = tuple(alias.name for alias in node.names)
        if node.level == 0:
            if node.module:
                self.imports.append(ImportStatement(node.module, names))
            return

        # Relative import: level 1 is the current package, each extra level one up.
        package = self.module.split(".") if self.is_package else self.module.split(".")[:-1]
        package = [part for part in package if part]
        up = node.level - 1
        if up > len(package):
            return  # beyond the top-level package; Python would fail too
        base = package[: len(package) - up] + (node.module.split(".") if node.module else [])
        if base:
            self.imports.append(ImportStatement(".".join(base), names))

    def _add_definition(self, node, parent_id: str, prefix: str, in_class: bool) -> None:
        symbol = f"{prefix}{node.name}"
        if isinstance(node, ast.ClassDef):
            symbol_type = CLASS
        else:
            symbol_type = METHOD if in_class else FUNCTION

        start_line = min([node.lineno] + [d.lineno for d in node.decorator_list])
        end_line = node.end_lineno or node.lineno
        signature = _signature(node)
        docstring = ast.get_docstring(node) or ""

        if symbol_type == CLASS:
            body_text = "\n".join(
                part for part in (signature, docstring, " ".join(_member_names(node.body))) if part
            )
        else:
            body_text = "\n".join(self.lines[start_line - 1 : end_line])

        record = IndexRecord(
            path=self.path,
            symbol=symbol,
            symbol_type=symbol_type,
            start_line=start_line,
            end_line=end_line,
            retrieval_text=self._truncate(f"{self.path}\n{symbol}\n{body_text}"),
            id=self._unique_id(f"{self.path}::{symbol}"),
            module=self.module,
            name=node.name,
            parent=parent_id,
            signature=signature,
            docstring=self._truncate(docstring),
            is_test=self.is_test,
        )
        self.records.append(record)
        self._visit_children(
            node, parent_id=record.id, prefix=f"{symbol}.", in_class=symbol_type == CLASS
        )

    def _unique_id(self, base: str) -> str:
        # Redefinitions (property setters, `if PY2: def f ... else: def f`)
        # get "#2", "#3"... in source order.
        candidate, n = base, 1
        while candidate in self.ids:
            n += 1
            candidate = f"{base}#{n}"
        self.ids.add(candidate)
        return candidate

    def _truncate(self, text: str) -> str:
        return text[: self.max_text_chars]


def _signature(node) -> str:
    if isinstance(node, ast.ClassDef):
        bases = [ast.unparse(b) for b in node.bases] + [ast.unparse(k) for k in node.keywords]
        return f"class {node.name}({', '.join(bases)})" if bases else f"class {node.name}"
    keyword = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    signature = f"{keyword} {node.name}({ast.unparse(node.args)})"
    if node.returns is not None:
        signature += f" -> {ast.unparse(node.returns)}"
    return signature


def _member_names(body: list[ast.stmt]) -> list[str]:
    """Names defined or assigned directly in a module or class body."""
    names = []
    for stmt in body:
        if isinstance(stmt, _DEFS):
            names.append(stmt.name)
        elif isinstance(stmt, ast.Assign):
            names.extend(t.id for t in stmt.targets if isinstance(t, ast.Name))
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
            names.append(stmt.target.id)
    return names
