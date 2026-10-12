"""Turn the source of one Python file into index records."""

from __future__ import annotations

import ast
import io
import re
import tokenize
import warnings

from src.repository.models import (
    CLASS,
    DECODE_ERROR,
    FUNCTION,
    METHOD,
    MODULE,
    MODULE_SYMBOL,
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


def module_name(path: str) -> str:
    """'shop/utils/__init__.py' -> 'shop.utils', 'shop/pricing.py' -> 'shop.pricing'."""
    parts = path[: -len(".py")].split("/") if path.endswith(".py") else path.split("/")
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def is_test_path(path: str) -> bool:
    parts = path.split("/")
    filename = parts[-1]
    return (
        any(part in _TEST_DIRS for part in parts[:-1])
        or filename.startswith("test_")
        or filename.endswith("_test.py")
        or filename in ("tests.py", "conftest.py")
    )


def parse_source(
    source: str,
    path: str,
    *,
    max_text_chars: int = DEFAULT_MAX_TEXT_CHARS,
) -> list[IndexRecord]:
    """Parse one file and return its module record followed by its definitions.

    Raises FileParseError if the source is not valid Python for the running
    interpreter.
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

    try:
        return _Collector(source, path, max_text_chars).collect(tree)
    except RecursionError:
        raise FileParseError(RECURSION_ERROR, "source is nested too deeply to index") from None


class _Collector:
    def __init__(self, source: str, path: str, max_text_chars: int):
        self.lines = _LINE_BREAK.split(source)
        if self.lines[-1] == "":
            self.lines.pop()
        self.path = path
        self.module = module_name(path)
        self.is_test = is_test_path(path)
        self.max_text_chars = max_text_chars
        self.records: list[IndexRecord] = []
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
                id=self._unique_id(self.path),
                path=self.path,
                module=self.module,
                symbol=MODULE_SYMBOL,
                name=MODULE_SYMBOL,
                kind=MODULE,
                start_line=1,
                end_line=max(1, len(self.lines)),
                parent=None,
                signature="",
                docstring=self._truncate(docstring),
                text=self._truncate(text),
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
            else:
                self._visit_children(child, parent_id, prefix, in_class)

    def _add_definition(self, node, parent_id: str, prefix: str, in_class: bool) -> None:
        symbol = f"{prefix}{node.name}"
        if isinstance(node, ast.ClassDef):
            kind = CLASS
        else:
            kind = METHOD if in_class else FUNCTION

        start_line = min([node.lineno] + [d.lineno for d in node.decorator_list])
        end_line = node.end_lineno or node.lineno
        signature = _signature(node)
        docstring = ast.get_docstring(node) or ""

        if kind == CLASS:
            body_text = "\n".join(
                part for part in (signature, docstring, " ".join(_member_names(node.body))) if part
            )
        else:
            body_text = "\n".join(self.lines[start_line - 1 : end_line])

        record = IndexRecord(
            id=self._unique_id(f"{self.path}::{symbol}"),
            path=self.path,
            module=self.module,
            symbol=symbol,
            name=node.name,
            kind=kind,
            start_line=start_line,
            end_line=end_line,
            parent=parent_id,
            signature=signature,
            docstring=self._truncate(docstring),
            text=self._truncate(f"{self.path}\n{symbol}\n{body_text}"),
            is_test=self.is_test,
        )
        self.records.append(record)
        self._visit_children(
            node, parent_id=record.id, prefix=f"{symbol}.", in_class=kind == CLASS
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
