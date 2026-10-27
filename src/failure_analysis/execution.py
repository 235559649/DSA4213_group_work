"""Conservative command-form provenance for ordinary shell observations.

This is a bounded recognizer, not a shell interpreter or proof that an exception
is unexpected. Never runs a command. Mixed actions stay unknown; explicit
execution-layer provenance can supersede this inference in the controller.
"""
from __future__ import annotations

import ast
import re
import shlex

_PYTHON = re.compile(r'python(?:[23](?:\.\d+)*)?(?:\.exe)?$')
_HEREDOC = re.compile(r"(?P<head>[^\n]+?)<<\s*(?P<quote>['\"])(?P<tag>[A-Za-z_]\w*)(?P=quote)\s*\n(?P<body>.*?)\n(?P=tag)\s*", re.S)
_DISPLAY = {'cat', 'head', 'tail', 'sed', 'grep', 'rg', 'less', 'more', 'ls', 'find', 'pwd'}


def _words(command: str) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=';&|()<>\n')
    lexer.whitespace = ' \t\r'
    lexer.whitespace_split = True
    words = list(lexer)
    # Only a single quiet cwd prefix is understood; arbitrary shell expressions
    # or environment assignments are deliberately not reconstructed.
    if len(words) > 3 and words[0] == 'cd' and words[2] == '&&':
        words = words[3:]
    return words


def _python_kind(code: str) -> str:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        # Actual syntax failures are execution evidence, not source display.
        return 'execution'
    calls = [node.func for node in ast.walk(tree) if isinstance(node, ast.Call)]
    # A literal traceback printed by a display-only script must not trigger.
    display_names = {'print', 'repr', 'str', 'open', 'Path'}
    display_attrs = {'read', 'read_text', 'read_bytes', 'readlines', 'getsource'}
    if calls and all((isinstance(fn, ast.Name) and fn.id in display_names) or
                     (isinstance(fn, ast.Attribute) and fn.attr in display_attrs) for fn in calls):
        if not any(isinstance(node, (ast.Raise, ast.Assert)) for node in ast.walk(tree)):
            return 'source_display'
    return 'execution'


def infer_observation_kind(command: str) -> str:
    """Recognize single Python/pytest invocations or source-display forms.

    Python -c and quoted heredocs may include arbitrary Python syntax, but no
    additional shell actions. Unsupported compound commands remain unknown.
    A recognized execution may still print examples or expected exceptions;
    callers must not present inference as authoritative runtime metadata.
    """
    if not isinstance(command, str) or not command.strip():
        return 'unknown'
    command = command.strip()
    heredoc = _HEREDOC.fullmatch(command)
    try:
        words = _words(heredoc['head'] if heredoc else command)
    except ValueError:
        return 'unknown'
    if not words:
        return 'unknown'
    name = words[0].replace('\\', '/').rsplit('/', 1)[-1]
    if _PYTHON.fullmatch(name):
        if heredoc:
            if heredoc['tag'] in heredoc['body'].splitlines():
                return 'unknown'  # Multiple heredocs/actions cannot form one Python body.
            return _python_kind(heredoc['body']) if words[1:] in [[], ['-']] else 'unknown'
        if len(words) == 3 and words[1] == '-c':
            return _python_kind(words[2])
        if words[1:3] == ['-m', 'pytest'] and not any(
                word in {';', '&&', '||', '|', '>', '<', '\n', '&'} for word in words[3:]):
            return 'execution'
        return 'unknown'
    if heredoc or any(word in {';', '&&', '||', '|', '>', '<', '\n', '&', '(', ')'} for word in words):
        return 'unknown'
    if any('$(' in word or '`' in word for word in words):
        return 'unknown'
    if name in _DISPLAY or (name == 'git' and len(words) > 1 and words[1] in {'diff', 'show', 'status', 'log'}):
        return 'source_display'
    if name in {'pytest', 'pytest.exe'}:
        return 'execution'
    return 'unknown'
