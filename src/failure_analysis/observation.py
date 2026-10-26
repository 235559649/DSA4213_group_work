"""Inspect one tool observation without executing it or changing update policy.

Output text cannot establish its own provenance. The caller must supply whether
it came from execution, source display, an expected failure, or an unknown/mixed
action. Unknown rc=0 observations are diagnostic-only by design.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import re

from src.failure_analysis.traceback_parser import clean_output, parse_traceback

_HEADER = 'Traceback (most recent call last):'
_FRAME = re.compile(r'^  File "[^"]+", line [1-9][0-9]*(?:, in .+)?$')
_TERMINAL = re.compile(r'^(?:[A-Za-z_]\w*\.)*[A-Z]\w*(?::.*)?$')
_PYTEST = re.compile(r'^=+ .*\b[1-9][0-9]* (?:failed|errors?)\b.* =+$')
_KINDS = {'execution', 'source_display', 'expected_failure', 'unknown'}


@dataclass(frozen=True)
class ObservationEvidence:
    returncode: int | None
    process_status: str
    observation_kind: str
    evidence_kinds: tuple[str, ...]
    observed_failure: bool
    should_analyze: bool
    reason: str
    output_sha256: str
    output_truncated: bool

    def to_dict(self) -> dict:
        return asdict(self)


def _has_complete_traceback(text: str) -> bool:
    active = frames = False
    for line in text.splitlines():
        if line == _HEADER:
            active, frames = True, False
        elif active and _FRAME.fullmatch(line):
            frames = True
        elif active and frames and _TERMINAL.fullmatch(line):
            # Existing parser rejects log labels; custom terminals require a frame.
            parsed = parse_traceback(_HEADER + '\n  File "observed.py", line 1\n' + line)
            if parsed.exception_details:
                return True
            active = frames = False
        elif active and (not line or line.startswith((' ', '\t'))):
            continue
        else:
            active = frames = False
    return False


def detect_observation(
    output: str, *, returncode: int | None, observation_kind: str = 'unknown',
    output_truncated: bool = False,
) -> ObservationEvidence:
    """Return trigger advice, never a source ranking or a defect verdict.

    ``execution`` must be established by the caller, not inferred from Error
    keywords or a shell-command substring. Mixed shell actions default to
    unknown. Nonzero unknown observations retain the existing analysis route.
    Truncation disallows a new rc=0 trigger; nonzero status is still evidence.
    Bare exceptions and pytest failures can be logged without inventing frames.
    The caller must still perform environment classification, fresh-index
    mapping, UpdateGate checks and actual delivery acknowledgement.
    """
    if not isinstance(output, str):
        raise TypeError('output must be a string')
    if returncode is not None and (isinstance(returncode, bool) or not isinstance(returncode, int)):
        raise TypeError('returncode must be an integer or None')
    if observation_kind not in _KINDS:
        raise ValueError('unsupported observation_kind')
    if not isinstance(output_truncated, bool):
        raise TypeError('output_truncated must be a boolean')
    text = clean_output(output)
    nonzero = returncode is not None and returncode != 0
    status = 'unknown' if returncode is None else 'nonzero' if nonzero else 'zero'
    kinds = []
    if nonzero:
        kinds.append('nonzero_exit')
    complete = _has_complete_traceback(text)
    pytest_failure = any(_PYTEST.fullmatch(line) for line in text.splitlines())
    if complete:
        kinds.append('complete_traceback')
    if pytest_failure:
        kinds.append('pytest_failure_summary')
    if not complete and parse_traceback(text).exception_details:
        kinds.append('exception_summary')
    excluded = observation_kind in {'source_display', 'expected_failure'}
    trusted = observation_kind == 'execution'
    observed = not excluded and (nonzero or (trusted and (complete or pytest_failure or 'exception_summary' in kinds)))
    analyze = not excluded and (nonzero or (trusted and not output_truncated and (complete or pytest_failure)))
    reason = (
        observation_kind if excluded else
        'nonzero_exit' if nonzero else
        'provenance_required' if not trusted and kinds else
        'truncated_diagnostic_only' if output_truncated and kinds else
        'runtime_failure_evidence' if analyze else
        'weak_diagnostic_only' if observed else 'no_failure_evidence'
    )
    return ObservationEvidence(returncode, status, observation_kind, tuple(kinds),
        observed, analyze, reason, hashlib.sha256(output.encode()).hexdigest(), output_truncated)
