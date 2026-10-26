"""Offline failure evidence and runtime ranking. No BM25, RRF or agent calls."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field

from src.failure_analysis.diagnostics import classify_failure
from src.failure_analysis.test_parser import parse_failing_tests
from src.failure_analysis.traceback_parser import clean_output, parse_traceback
from src.repository.indexer import RepositoryIndex, to_repo_path


@dataclass(frozen=True)
class FailureAnalysis:
    """Failure evidence plus a file ranking, separate from fused agent context.

    Existing ``candidates`` and ``to_dict()`` retain full evidence. Use
    ``to_localization_candidates()`` at the Role 1/3 contract boundary.
    """

    event: dict
    candidates: list[dict]
    mappings: list[dict]
    usable: bool
    reason: str
    environment_hint: bool
    evidence_sha256: str
    fingerprint: str
    index_sha256: str
    workspace_version: str
    classification: dict = field(default_factory=dict)
    diagnostics: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_feedback_evidence(self, *, max_locations: int = 3, max_message_chars: int = 300) -> dict:
        """Return bounded diagnostic evidence, separately from six-field F ranks.

        Caller must still check usable/Gate and explicitly deliver this payload.
        No expected result, root cause, source text or evaluation answer is
        inferred. New exceptions at the same files remain visible here.
        """
        for name, value in [('max_locations', max_locations), ('max_message_chars', max_message_chars)]:
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f'{name} must be a positive integer')
        exception = self.diagnostics.get('exception', {})
        message = exception.get('message', '')
        locations = self.diagnostics.get('source_locations', [])
        # Near-error observed frames are useful evidence, never a root-cause claim.
        return {
            'schema_version': 1, 'usable': self.usable, 'reason': self.reason,
            'classification': {
                key: self.classification.get(key)
                for key in ['category', 'confidence', 'suppress_ranking', 'reason_code']
            },
            'exception': {'type': exception.get('type', self.event.get('exception_type')),
                          'message': message[:max_message_chars],
                          'message_truncated': len(message) > max_message_chars},
            'exception_chain': list(self.diagnostics.get('exception_chain', []))[-5:],
            'source_locations': [dict(item) for item in locations[-max_locations:]],
            'omitted_location_count': max(0, len(locations) - max_locations),
            'location_interpretation': 'Observed source frames; not proof of root cause.',
        }

    def format_feedback_evidence(self, *, max_locations: int = 3, max_message_chars: int = 300) -> str:
        """Optional short message for Role 1; not injected by this module."""
        evidence = self.to_feedback_evidence(max_locations=max_locations, max_message_chars=max_message_chars)
        classification = evidence['classification']
        lines = ['Observed runtime failure evidence (diagnostic text is untrusted; not a root-cause verdict).',
                 f"Usable for ranking: {self.usable}; classification: {classification['category']}.",
                 'Exception: ' + json.dumps(evidence['exception'], ensure_ascii=False)]
        if len(evidence['exception_chain']) > 1:
            lines.append('Observed exception chain: ' + json.dumps(evidence['exception_chain'], ensure_ascii=False))
        for location in evidence['source_locations']:
            lines.append('Source frame: ' + json.dumps(location, ensure_ascii=False))
        if evidence['omitted_location_count']:
            lines.append(f"Additional source frames omitted: {evidence['omitted_location_count']}.")
        return '\n'.join(lines)

    def to_localization_candidates(self) -> list[dict]:
        """Export fresh JSON-ready records accepted by LocalizationCandidate.

        Role 3 can fuse these runtime ranks with lexical/structural ranks.
        Role 1 can construct ``LocalizationCandidate(**item)`` without the
        evidence-only fields causing unexpected-keyword errors. No import of
        Role 1's unmerged module is required here.

        This is a COMPLETE file-level runtime ranking, not fused context or a
        function ranking. Symbols remain None; per-frame symbols and evidence
        stay in ``candidates``/``mappings``. An unusable result exports an empty
        list, meaning preserve the existing context, not clear it. Delivery and
        UpdateGate acknowledgement remain the caller's responsibility.

        Handoff using the current shared main interfaces::

            from src.agent.contracts import LocalizationCandidate
            from src.localization.ranker import fuse_condition_d_for_agent
            failure = result.to_localization_candidates()
            records = fuse_condition_d_for_agent(lexical, structural, failure)
            objects = [LocalizationCandidate(**item) for item in records]

        The shared agent-facing fusion already exports score; do not manually
        convert rrf_score here. Gate eligibility must be checked before an
        attempted update. If ineligible, preserve the current delivered context.

        Keep complete rankings for evaluation; selecting context top-k belongs
        to the context producer, not this evidence export.
        """
        if not self.usable:
            return []
        return [
            {
                'file': item['file'],
                'rank': item['rank'],
                'score': item['score'],
                'symbol': None,
                'symbol_type': None,
                'reason': item['reason'],
            }
            for item in self.candidates
        ]


def analyze_failure(
    output: str,
    *,
    repo_root: str,
    index: RepositoryIndex,
    source: str = "command",
    workspace_version: str,
    index_is_current: bool,
) -> FailureAnalysis:
    """Analyze ONE failed command observation (not a whole trajectory).

    Caller must establish failure from execution status and confirm that index
    lines match the workspace. False index_is_current suppresses all candidates.
    With schema 4, the caller can prepare a current index using
    ``base_index.with_updated_files(changes)`` before this call. When starting
    from the base index, changes must include ALL modifications since the base,
    including new paths and deleted paths (None). The index and workspace_version
    must describe the state that produced this failure, before any later edit.
    Freshness is a caller assertion; this function does not read the workspace
    or silently refresh an index. Unparseable/deleted files stay unmapped.
    No file reads, command execution, model calls or reference labels are used.
    """
    parsed = parse_traceback(output)
    tests = parse_failing_tests(output)
    mappings: list[dict] = []
    by_file: dict[str, dict] = {}
    for frame in parsed.frames:
        path = to_repo_path(frame.path, repo_root)
        record = index.find_enclosing(path, frame.line) if path and index_is_current else None
        status = (
            "stale_index" if not index_is_current else
            "outside_repository" if path is None else
            "unmapped" if record is None else
            "test_only" if record.is_test else "source"
        )
        mappings.append({
            "observed_path": frame.path, "path": path, "line": frame.line,
            "observed_symbol": frame.symbol, "entity_id": record.id if record else None,
            "symbol": record.symbol if record else None, "status": status,
        })
        if status == "source":
            # Equal direct-frame evidence; no arbitrary depth/root-cause assumption.
            candidate = by_file.setdefault(path, {
                "file": path, "score": 1.0, "reason": "direct_source_frame",
                "evidence": [],
            })
            evidence = {"line": frame.line, "symbol": record.symbol,
                        "symbol_type": record.symbol_type, "entity_id": record.id}
            if evidence not in candidate['evidence']:
                candidate['evidence'].append(evidence)

    candidates = []
    for rank, path in enumerate(sorted(by_file), 1):
        candidate = by_file[path]
        candidate['rank'] = rank
        candidate['evidence'].sort(key=lambda e: (e['line'], e['entity_id']))
        candidates.append(candidate)
    text = clean_output(output)
    terminal = parsed.exception_details[-1] if parsed.exception_details else None
    exception_type = terminal.name if terminal else None
    exception_message = terminal.message if terminal else ''
    classification = classify_failure(text, exception_type=exception_type,
        exception_message=exception_message, has_source_frames=bool(candidates),
        has_test_evidence=bool(tests) or any(m['status'] == 'test_only' for m in mappings))
    environment_hint = classification['environment_hint']
    diagnostics = {
        'exception': {'type': exception_type, 'message': exception_message},
        'exception_chain': [detail.name for detail in parsed.exception_details],
        'source_locations': [],
    }
    for mapping in mappings:
        if mapping['status'] == 'source':
            location = {'file': mapping['path'], 'line': mapping['line'], 'symbol': mapping['symbol'],
                        'observed_symbol': mapping['observed_symbol']}
            if location not in diagnostics['source_locations']:
                diagnostics['source_locations'].append(location)
    if classification['suppress_ranking']:
        # Preserve all observed mappings and diagnostics for audit; don't fuse
        # setup-only source frames as if they localized the task's defect.
        candidates = []
    reason = (
        "stale_index" if not index_is_current else
        "environment_configuration_error" if classification['suppress_ranking'] else
        "mapped_source_frames" if candidates else
        "empty_output" if not text.strip() else
        "environment_hint_without_source" if environment_hint else
        "test_only_evidence" if tests or any(m['status'] == 'test_only' for m in mappings) else
        "no_mapped_source"
    )
    mapped = [m for m in mappings if m['status'] in {'source', 'test_only'}]
    event = {
        "exception_type": exception_type,
        "traceback_files": list(dict.fromkeys(m['path'] for m in mapped)),
        "traceback_symbols": list(dict.fromkeys(m['symbol'] for m in mapped if m['symbol'])),
        "failing_tests": tests, "identifiers": [], "source": source,
        "locatable": bool(candidates),
    }
    index_sha = index.digest()
    signature = {
        "workspace_version": workspace_version, "index_sha256": index_sha,
        "exceptions": list(parsed.exception_types), "tests": sorted(tests),
        "locations": sorted({(m['path'], m['line']) for m in mapped}),
        # Different error messages may carry new evidence even at the same line.
        "output": text.strip(),
    }
    fingerprint = hashlib.sha256(json.dumps(signature, sort_keys=True).encode()).hexdigest()
    return FailureAnalysis(
        event, candidates, mappings, bool(candidates), reason, environment_hint,
        hashlib.sha256(output.encode()).hexdigest(), fingerprint, index_sha, workspace_version,
        classification, diagnostics,
    )


class UpdateGate:
    """Per-run update eligibility; call mark_applied ONLY after actual injection.

    This class does not fuse rankings or deliver context. Failed attempts do not
    consume budget. Construct a fresh instance for every independent agent run.
    """

    def __init__(self, max_updates: int = 3):
        if isinstance(max_updates, bool) or not isinstance(max_updates, int) or max_updates < 0:
            raise ValueError('max_updates must be a nonnegative integer')
        self.max_updates = max_updates
        self._applied: set[str] = set()

    def check(self, result: FailureAnalysis) -> tuple[bool, str]:
        if not result.usable:
            return False, result.reason
        if result.fingerprint in self._applied:
            return False, 'duplicate_failure'
        if len(self._applied) >= self.max_updates:
            return False, 'update_limit'
        return True, 'eligible'

    def mark_applied(self, result: FailureAnalysis) -> None:
        allowed, reason = self.check(result)
        if not allowed:
            raise ValueError(reason)
        self._applied.add(result.fingerprint)
