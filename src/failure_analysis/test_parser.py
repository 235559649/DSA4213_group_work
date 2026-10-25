"""Extract pytest summary node IDs; a failing test alone is not a source target."""

import re

from src.failure_analysis.traceback_parser import clean_output

_SUMMARY = re.compile(r"^\s*(?:FAILED|ERROR)\s+(.+?)(?:\s+-\s+.*)?$")


def parse_failing_tests(output: str) -> list[str]:
    result: list[str] = []
    for line in clean_output(output).splitlines():
        match = _SUMMARY.match(line)
        if match:
            node = match[1].strip().replace('\\', '/')
            if '.py' in node and node not in result:
                result.append(node)
    return result
