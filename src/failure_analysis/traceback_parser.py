"""Parse plain Python and pytest short traceback locations without executing text."""

from __future__ import annotations

import re
from dataclasses import dataclass

_ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_FRAME = re.compile(r'^\s*File "(?P<path>.+)", line (?P<line>\d+)(?:, in (?P<symbol>.+))?\s*$')
_SHORT = re.compile(r"^\s*(?P<path>.+?\.py):(?P<line>\d+):(?:\s.*)?$")
_EXCEPTION = re.compile(
    r"^\s*(?:E\s+)?(?P<name>(?:[A-Za-z_]\w*\.)*[A-Za-z_]\w*(?:Error|Exception)|"
    r"AssertionError|KeyboardInterrupt|SystemExit|StopIteration)(?::.*)?$"
)
_CUSTOM_EXCEPTION = re.compile(
    r"^(?P<name>(?:[A-Za-z_]\w*\.)*[A-Z][A-Za-z_0-9]*)(?::(?P<message>.*))?$"
)
_LOG_LABELS = {'INFO', 'DEBUG', 'WARNING', 'ERROR', 'CRITICAL', 'TRACE', 'NOTICE', 'STATUS', 'RESULT'}


def clean_output(output: str) -> str:
    return _ANSI.sub("", output)


@dataclass(frozen=True)
class Frame:
    path: str
    line: int
    symbol: str | None = None


@dataclass(frozen=True)
class ExceptionDetail:
    name: str
    message: str


@dataclass(frozen=True)
class ParsedTraceback:
    frames: tuple[Frame, ...]
    exception_types: tuple[str, ...]
    exception_details: tuple[ExceptionDetail, ...] = ()


def _exception_detail(line: str, *, allow_custom: bool) -> ExceptionDetail | None:
    text = line.strip()
    if text.startswith('E '):
        text = text[2:].lstrip()
    known = _EXCEPTION.fullmatch(text)
    custom = _CUSTOM_EXCEPTION.fullmatch(text) if allow_custom else None
    match = known or custom
    if not match:
        return None
    if not known and match['name'] in _LOG_LABELS:
        return None
    return ExceptionDetail(match['name'], text.partition(':')[2].strip())


def parse_traceback(output: str) -> ParsedTraceback:
    """Retain observed order, deduplicate locations; do not infer a root cause.

    Custom names are accepted only after traceback frames, on an unindented
    terminal exception line (or pytest's E line / explicit short location).
    Capitalized log labels without traceback evidence are not exceptions.
    ExceptionGroup tree formatting remains unsupported.
    """
    frames: list[Frame] = []
    exceptions: list[str] = []
    details: list[ExceptionDetail] = []
    awaiting_exception = False
    for line in clean_output(output).splitlines():
        match = _FRAME.match(line) or _SHORT.match(line)
        if match:
            frame = Frame(match['path'], int(match['line']), match.groupdict().get('symbol'))
            if frame.line > 0 and frame not in frames:
                frames.append(frame)
            awaiting_exception = True
        terminal_line = line == line.lstrip() or line.lstrip().startswith('E ')
        detail = _exception_detail(line, allow_custom=awaiting_exception and terminal_line)
        # pytest short form: path.py:12: ValueError
        if match and 'symbol' not in match.groupdict():
            tail = line[match.end('line') + 1:].strip()
            detail = _exception_detail(tail, allow_custom=True)
        if detail:
            if detail.name not in exceptions:
                exceptions.append(detail.name)
            details.append(detail)
            awaiting_exception = False
    return ParsedTraceback(tuple(frames), tuple(exceptions), tuple(details))
