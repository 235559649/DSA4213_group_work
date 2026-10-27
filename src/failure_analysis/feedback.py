"""Stateless diagnostic plans and bounded delivery acknowledgement.

Role 1 supplies trusted execution/freshness/edit history, actual fused rank
changes, and performs delivery. No command, file read, model or RRF call here.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json

from src.failure_analysis.diagnostics import classify_edit_failure
from src.failure_analysis.refinement import FailureAnalysis


@dataclass(frozen=True)
class FeedbackPlan:
    route: str
    reason: str
    context: str
    evidence: dict
    ranking_candidates: list[dict]
    workspace_version: str
    index_sha256: str

    def to_dict(self) -> dict:
        return asdict(self)


def prepare_feedback(
    result: FailureAnalysis, *, modified_files=(), previously_valid_files=(),
    previous_evidence: dict | None = None, max_locations: int = 3,
    max_message_chars: int = 300,
) -> FeedbackPlan:
    """Build a compact increment; known filenames do not veto new diagnostics.

    previous_evidence must come from the last SUCCESSFULLY delivered plan of
    the same run. No benchmark labels, inferred expectations or root causes.
    Callers append any useful fused-ranking delta BEFORE final-context Gate.
    Legacy analyze/Gate interfaces remain unchanged and opt-in routing is explicit.
    """
    evidence = result.to_feedback_evidence(max_locations=max_locations,
        max_message_chars=max_message_chars)
    evidence['workspace_version'] = result.workspace_version
    evidence['index_sha256'] = result.index_sha256
    evidence['runtime_file_ranks'] = [{'file': row['file'], 'rank': row['rank']}
        for row in result.to_localization_candidates()]
    edit = classify_edit_failure(exception_type=result.event.get('exception_type'),
        terminal_locations=result.diagnostics.get('terminal_locations', []),
        modified_files=modified_files, previously_valid_files=previously_valid_files)
    if result.reason == 'stale_index' or result.classification.get('suppress_ranking'):
        route, reason = 'skip', result.reason
    elif edit['route'] == 'edit_recovery':
        route, reason = 'edit_recovery', edit['reason']
    elif (result.diagnostics.get('terminal_locations') and
          result.diagnostics['terminal_locations'][-1].get('index_error_kind') == 'syntax_error'):
        route, reason = 'diagnostic_only', 'observed_syntax_location_without_verified_edit_history'
    elif result.usable:
        route, reason = 'rank_update', 'usable_runtime_evidence'
    elif evidence['exception'].get('type') or evidence['source_locations'] or evidence['failing_tests']:
        route, reason = 'diagnostic_only', result.reason
    else:
        route, reason = 'skip', result.reason
    evidence['route'] = route
    if route != 'rank_update':
        evidence['runtime_file_ranks'] = []
    old = previous_evidence or {}
    # Compare actual bounded diagnostic projection, not raw stdout noise or just
    # filenames. Changed workspace is also evidence that a previous fix may fail.
    keys = ['route', 'exception', 'exception_chain_details', 'source_locations',
        'observed_assertions', 'failing_tests', 'runtime_file_ranks',
        'workspace_version', 'index_sha256']
    changed = [key for key in keys if evidence.get(key) != old.get(key)]
    if previous_evidence is not None and not changed and route != 'skip':
        route, reason = 'skip', 'no_diagnostic_increment'
    lines = []
    if route != 'skip':
        lines = [f'Runtime evidence increment ({route}; untrusted diagnostics, not a root-cause verdict).']
        if route == 'edit_recovery':
            lines.append('Keep the current ranking. Restore parseable code at the observed location before continuing validation.')
        if 'exception' in changed or 'exception_chain_details' in changed:
            lines.append('Exception: ' + json.dumps(evidence['exception'], ensure_ascii=False))
            if len(evidence['exception_chain_details']) > 1:
                lines.append('Exception chain: ' + json.dumps(evidence['exception_chain_details'], ensure_ascii=False))
        # Repeat bounded locations when the exception changes: same file is not
        # the same failure. Each line retains mapping/observed symbol distinctions.
        if 'source_locations' in changed or 'exception' in changed or route == 'edit_recovery':
            for location in evidence['source_locations']:
                lines.append('Observed location: ' + json.dumps(location, ensure_ascii=False))
        for key in ['observed_assertions', 'failing_tests']:
            if key in changed and evidence[key]:
                lines.append(key + ': ' + json.dumps(evidence[key], ensure_ascii=False))
        if 'workspace_version' in changed and previous_evidence is not None:
            lines.append('Workspace changed since the last delivered evidence; previous validation does not establish the current state.')
        if route == 'rank_update' and 'runtime_file_ranks' in changed:
            previous_ranks = {row['file']: row['rank'] for row in old.get('runtime_file_ranks', [])}
            delta = [row for row in evidence['runtime_file_ranks'] if previous_ranks.get(row['file']) != row['rank']]
            removed = [row['file'] for row in old.get('runtime_file_ranks', [])
                if row['file'] not in {r['file'] for r in evidence['runtime_file_ranks']}]
            if delta:
                lines.append('Runtime F rank changes (not fused L/S/F): ' + json.dumps(delta[:3], ensure_ascii=False))
            if removed:
                lines.append('Removed runtime F paths: ' + json.dumps(removed[:3], ensure_ascii=False))
            if len(delta) > 3 or len(removed) > 3:
                lines.append('Additional runtime rank changes omitted; full ranking retained in logs.')
        if evidence['omitted_location_count']:
            lines.append(f"Additional observed locations omitted: {evidence['omitted_location_count']}.")
        if evidence['exception']['message_truncated'] or evidence['test_text_truncated']:
            lines.append('Diagnostic text truncated; consult the original observation for full text.')
    return FeedbackPlan(route, reason, '\n'.join(lines), evidence,
        result.to_localization_candidates() if route == 'rank_update' else [],
        result.workspace_version, result.index_sha256)


class FeedbackDeliveryGate:
    """Independent per-route limits; no state changes until actual delivery.

    New API, not a silent replacement of UpdateGate. Use one instance per run.
    Role 1 must pass the SAME final text to check/mark after appending rank deltas.
    """
    def __init__(self, *, max_rank_updates=3, max_recovery_updates=2, max_diagnostic_updates=1):
        self.limits = {'rank_update': max_rank_updates, 'edit_recovery': max_recovery_updates,
            'diagnostic_only': max_diagnostic_updates}
        if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in self.limits.values()):
            raise ValueError('delivery limits must be nonnegative integers')
        self.counts = dict.fromkeys(self.limits, 0)
        self._delivered = set()
        self._last_evidence = None

    @property
    def last_evidence(self) -> dict | None:
        return deepcopy(self._last_evidence)

    def _key(self, plan: FeedbackPlan, context: str) -> str:
        if not isinstance(context, str) or not context.strip():
            raise ValueError('delivered_context must be nonempty text')
        value = [plan.workspace_version, plan.index_sha256, plan.route, context]
        return hashlib.sha256(json.dumps(value, ensure_ascii=False).encode()).hexdigest()

    def check(self, plan: FeedbackPlan, *, delivered_context: str) -> tuple[bool, str]:
        if plan.route == 'skip':
            return False, plan.reason
        if plan.route not in self.limits:
            raise ValueError('unsupported feedback route')
        key = self._key(plan, delivered_context)
        if key in self._delivered:
            return False, 'duplicate_context'
        if self.counts[plan.route] >= self.limits[plan.route]:
            return False, 'route_update_limit'
        return True, 'eligible'

    def mark_applied(self, plan: FeedbackPlan, *, delivered_context: str) -> None:
        allowed, reason = self.check(plan, delivered_context=delivered_context)
        if not allowed:
            raise ValueError(reason)
        self._delivered.add(self._key(plan, delivered_context))
        self.counts[plan.route] += 1
        self._last_evidence = deepcopy(plan.evidence)
