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


def clean_output(output: str) -> str:
    return _ANSI.sub("", output)


@dataclass(frozen=True)
class Frame:
    path: str
    line: int
    symbol: str | None = None


@dataclass(frozen=True)
class ParsedTraceback:
    frames: tuple[Frame, ...]
    exception_types: tuple[str, ...]


def parse_traceback(output: str) -> ParsedTraceback:
    """Retain observed order, deduplicate locations; do not infer a root cause.

    Plain chained exceptions are retained. Custom exception names without a
    conventional suffix and ExceptionGroup tree formatting are not supported.
    """
    frames: list[Frame] = []
    exceptions: list[str] = []
    for line in clean_output(output).splitlines():
        match = _FRAME.match(line) or _SHORT.match(line)
        if match:
            frame = Frame(match['path'], int(match['line']), match.groupdict().get('symbol'))
            if frame.line > 0 and frame not in frames:
                frames.append(frame)
        exception = _EXCEPTION.match(line)
        if exception and exception['name'] not in exceptions:
            exceptions.append(exception['name'])
        # pytest short form: path.py:12: ValueError
        if match and 'symbol' not in match.groupdict():
            tail = line[match.end('line') + 1:].strip()
            exception = _EXCEPTION.match(tail)
            if exception and exception['name'] not in exceptions:
                exceptions.append(exception['name'])
    return ParsedTraceback(tuple(frames), tuple(exceptions))
