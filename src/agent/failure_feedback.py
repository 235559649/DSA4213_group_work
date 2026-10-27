"""D runtime routing for mini-SWE-agent 2.4.6.

Uses existing Role 2 index updates, Role 3 fusion and Role 4 evidence/Gate.
Initial L/S are frozen per run. The first eligible evidence increment per
decision is delivered with independent ranking/recovery/diagnostic limits.
No hidden evaluation inputs are used.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import shlex
import time
from dataclasses import asdict

from src.agent.context import select_prompt_candidates
from src.agent.contracts import LocalizationCandidate
from src.failure_analysis import analyze_failure
from src.failure_analysis.feedback import FeedbackDeliveryGate, prepare_feedback
from src.failure_analysis.execution import infer_observation_kind
from src.failure_analysis.observation import detect_observation
from src.localization.keyword import BM25Retriever
from src.localization.ranker import RRF_K, fuse_condition_c_for_agent, fuse_condition_d_for_agent
from src.localization.structural import structural_ranking
from src.repository.indexer import index_sources, iter_python_files

SNAPSHOT_LIMIT = 64 * 1024 * 1024


class LocalSourceReader:
    def __init__(self, root):
        self.root = str(Path(root).resolve())

    def __call__(self):
        if not Path(self.root).is_dir():
            raise NotADirectoryError(self.root)
        files = {}
        size = 0
        for path in iter_python_files(Path(self.root)):
            file = Path(self.root) / path
            if size + file.stat().st_size > SNAPSHOT_LIMIT:
                raise RuntimeError('D source snapshot exceeds 64 MiB limit')
            data = file.read_bytes()
            size += len(data)
            if size > SNAPSHOT_LIMIT:
                raise RuntimeError('D source snapshot exceeds 64 MiB limit')
            files[path] = data
        return files


class RemoteSourceReader:
    """Read task Python sources through the existing container executor.

    No host paths/credentials are mounted. Invalid, truncated or oversized
    output is a snapshot failure, never a claim of a fresh index.
    Docker transport still needs on-machine integration verification.
    """
    def __init__(self, execute, root='/testbed'):
        self.execute = execute
        self.root = root

    def __call__(self):
        # Container code deliberately supports historical task Python versions.
        code = '''import base64,json,os
root=ROOT
if not os.path.isdir(root):raise RuntimeError('D task root missing')
files={}
total=0
for current,dirs,names in os.walk(root):
    at_root=os.path.normpath(current)==os.path.normpath(root)
    dirs[:]=[d for d in dirs if not d.startswith('.') and d not in ('__pycache__','node_modules','site-packages') and not d.endswith('.egg-info') and not(at_root and d in ('build','dist','env','venv')) and not os.path.islink(os.path.join(current,d))]
    for name in names:
        path=os.path.join(current,name)
        if not name.endswith('.py') or os.path.islink(path):continue
        with open(path,'rb') as stream:data=stream.read(67108865-total)
        total+=len(data)
        if total>67108864:raise RuntimeError('D snapshot too large')
        files[os.path.relpath(path,root).replace(os.sep,'/')]=base64.b64encode(data).decode('ascii')
print(json.dumps(files,sort_keys=True))
'''.replace('ROOT', repr(self.root), 1)
        encoded = base64.b64encode(code.encode()).decode()
        command = 'python -c ' + shlex.quote("import base64;exec(base64.b64decode('" + encoded + "'))")
        response = self.execute({'command': command})
        if response.get('returncode') != 0:
            raise RuntimeError('D container snapshot command failed')
        raw = response.get('output', '')
        if len(raw) > SNAPSHOT_LIMIT * 2:
            raise RuntimeError('D encoded snapshot exceeds limit')
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError('D snapshot must be a path-content mapping')
        return {path: base64.b64decode(data, validate=True) for path, data in payload.items()}


def validate_failure_weight(value):
    """Validate before creating environments, reading sources or calling models."""
    fuse_condition_d_for_agent([], [], [], failure_weight=value)
    return float(value)


def validate_failure_limits(max_updates, max_recovery_updates, max_diagnostic_updates):
    return FeedbackDeliveryGate(max_rank_updates=max_updates,
        max_recovery_updates=max_recovery_updates,
        max_diagnostic_updates=max_diagnostic_updates).limits.copy()


def failure_fusion_config(weight, *, max_updates=3, max_recovery_updates=2,
                         max_diagnostic_updates=1):
    return {'failure_weight': weight, 'ranking_strategy': 'near_exception',
            'fusion_policy': 'weighted_rrf', 'k': RRF_K,
            'feedback_routing_policy': 'evidence_increment_v3',
            'feedback_route_limits': validate_failure_limits(max_updates,
                max_recovery_updates, max_diagnostic_updates)}


class FailureFeedbackController:
    """Attach to the actual environment and model calls, without changing algorithms."""
    def __init__(self, agent, reader, task, run_dir, max_updates=3, top_k=5, *,
                 failure_weight=1.0, max_recovery_updates=2, max_diagnostic_updates=1):
        self.failure_weight = validate_failure_weight(failure_weight)
        self.gate = FeedbackDeliveryGate(max_rank_updates=max_updates,
            max_recovery_updates=max_recovery_updates, max_diagnostic_updates=max_diagnostic_updates)
        # Same validation and selection semantics as Role 1's A/B/C context.
        select_prompt_candidates([], top_k)
        self.agent = agent
        self.reader = reader
        self.root = reader.root
        self.directory = Path(run_dir)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.top_k = top_k
        self.pending = []
        self.events = []
        self.observations = []
        self.applied = 0
        self.closed = False
        self.overhead_seconds = 0.0
        self.feedback_total_seconds = 0.0
        self.actions_observed = 0
        self.process_failures = 0
        self.analysis_count = 0
        self.snapshot_count = 0
        self._execute = agent.env.execute
        self._query = agent.model.query
        started = time.monotonic()
        timing_started = time.perf_counter()
        self.base_sources = reader()
        self.base = index_sources(self.base_sources,
            read_bytes=self.base_sources.__getitem__, file_size=lambda p: len(self.base_sources[p]))
        # A file is previously valid only if this run has actually indexed it
        # without errors. Newly added/broken files are not assumed valid.
        self.previously_valid_files = set(self.base.files) - {e.path for e in self.base.errors}
        self.latest_snapshot_action = 0
        self.latest_workspace_version = self._source_version(self.base_sources)
        self.lexical = [{'path': p, 'rank': i, 'bm25_score': s} for i, (p, s) in
            enumerate(BM25Retriever(self.base).retrieve(task), 1)]
        self.structural = [asdict(x) for x in structural_ranking(self.base,
            [(x['path'], x['bm25_score']) for x in self.lexical])]
        self.ranking = fuse_condition_c_for_agent(self.lexical, self.structural)
        self._save_json('initial_rankings.json', {'index_sha256': self.base.digest(),
            'lexical': self.lexical, 'structural': self.structural, 'fused': self.ranking})
        self.initial_localization_seconds = time.perf_counter() - timing_started
        self.overhead_seconds += time.monotonic() - started
        agent.env.execute = self.execute
        agent.model.query = self.query

    def _save_json(self, filename, value):
        (self.directory / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

    def _persist(self):
        text = ''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in self.events)
        (self.directory / 'failure_updates.jsonl').write_text(text, encoding='utf-8')
        text = ''.join(json.dumps(o, ensure_ascii=False) + '\n' for o in self.observations)
        (self.directory / 'observations.jsonl').write_text(text, encoding='utf-8')

    @staticmethod
    def _source_version(sources):
        return hashlib.sha256(json.dumps({p: hashlib.sha256(b).hexdigest()
            for p, b in sorted(sources.items())}, sort_keys=True).encode()).hexdigest()

    def initial_candidates(self):
        return select_prompt_candidates(self.initial_full_candidates(), self.top_k)

    def initial_full_candidates(self):
        return [LocalizationCandidate(**x) for x in self.ranking]

    def _record_feedback_time(self, event, started):
        # Accumulate only active processing slices, never command/model waiting.
        # Writing the final timing values is outside the measured slices.
        elapsed = time.perf_counter() - started
        event['feedback_processing_seconds'] += elapsed
        self.feedback_total_seconds += elapsed

    def execute(self, action, *args, **kwargs):
        response = self._execute(action, *args, **kwargs)
        started = time.monotonic()
        timing_started = time.perf_counter()
        self.actions_observed += 1
        code = response.get('returncode')
        if isinstance(code, int) and not isinstance(code, bool) and code != 0:
            self.process_failures += 1
        raw = response.get('output', '')
        # Trusted execution metadata wins. The model's own action metadata
        # cannot assert provenance; a limited command grammar is the fallback.
        kind = response.get('observation_kind')
        basis = 'execution_metadata'
        if kind not in {'execution', 'source_display', 'expected_failure', 'unknown'}:
            command = action.get('command', '') if isinstance(action, dict) else ''
            kind = infer_observation_kind(command)
            basis = 'conservative_command_form'
        observation = detect_observation(raw, returncode=code, observation_kind=kind,
            output_truncated=response.get('output_truncated', False) is True)
        self.observations.append({'step': self.agent.n_calls, 'action': action,
            'action_number': self.actions_observed, 'observation': observation.to_dict(),
            'observation_kind_basis': basis})
        if not observation.evidence_kinds:
            self._persist()
            self.feedback_total_seconds += time.perf_counter() - timing_started
            self.overhead_seconds += time.monotonic() - started
            return response
        number = len(self.events) + 1
        event = {'event_id': f'failure-{number}', 'step': self.agent.n_calls,
                 'action_number': self.actions_observed,
                 'returncode': code, 'update_applied': False,
                 'ranking_updated': False, 'update_status': 'pending', 'action': action,
                 'observation': observation.to_dict(), 'observation_kind_basis': basis,
                 'feedback_processing_seconds': 0.0}
        evidence_file = f'failure-{number}-output.txt'
        (self.directory / evidence_file).write_text(raw, encoding='utf-8')
        event['raw_evidence'] = evidence_file
        try:
            if not observation.should_analyze:
                event.update(update_status='skipped', no_update_reason=observation.reason)
                return response
            # Exhausting the ranking budget must not disable recovery/diagnostic
            # routes. Avoid source snapshots only when ALL routes are exhausted.
            if all(self.gate.counts[r] >= limit for r, limit in self.gate.limits.items()):
                event.update(update_status='skipped', no_update_reason='update_limit')
                return response
            self.snapshot_count += 1
            sources = self.reader()
            changes = {p: sources.get(p) for p in set(sources) | set(self.base_sources)
                       if sources.get(p) != self.base_sources.get(p)}
            index = self.base.with_updated_files(changes)
            state = self._source_version(sources)
            self.latest_snapshot_action = self.actions_observed
            self.latest_workspace_version = state
            # Keep the provenance at failure time, before adding valid files
            # observed in this snapshot to the run's history.
            event.update(modified_files=sorted(changes),
                previously_valid_files=sorted(self.previously_valid_files),
                validity_basis='earlier_successful_index_in_this_run')
            result = analyze_failure(raw, repo_root=self.root, index=index,
                workspace_version=state, index_is_current=True, ranking_strategy='near_exception')
            self.analysis_count += 1
            self.previously_valid_files.update(set(index.files) - {e.path for e in index.errors})
            event.update(analysis=result.to_dict(), workspace_version=state,
                         index_sha256=index.digest(), base_index_sha256=self.base.digest())
            self.pending.append((result, event))
        except Exception as exc:
            event.update(update_status='skipped', no_update_reason='snapshot_or_mapping_failed',
                         error=f'{type(exc).__name__}: {exc}')
        finally:
            self.events.append(event)
            self.overhead_seconds += time.monotonic() - started
            self._record_feedback_time(event, timing_started)
            self._persist()
        return response

    def _ranking_delta(self, ranking):
        """Only useful changes in the exposed top-k; full lists stay in logs."""
        before = select_prompt_candidates([LocalizationCandidate(**x) for x in self.ranking], self.top_k)
        after = select_prompt_candidates([LocalizationCandidate(**x) for x in ranking], self.top_k)
        old = {x.file: x.rank for x in before}
        new = {x.file: x.rank for x in after}
        changes = [{'file': path, 'before_rank': old.get(path), 'rank': rank}
                   for path, rank in new.items() if old.get(path) != rank]
        removed = [path for path in old if path not in new]
        lines = []
        if changes:
            lines.append('Fused candidate rank changes: ' + json.dumps(changes[:3], ensure_ascii=False))
        if removed:
            lines.append('Left exposed candidate list: ' + json.dumps(removed[:3], ensure_ascii=False))
        if len(changes) > 3 or len(removed) > 3:
            lines.append('Additional fused changes omitted; full ranking retained in logs.')
        return '\n'.join(lines)

    def _inject_context_message(self, messages, context):
        request_count = len(messages)
        history = self.agent.messages
        history_count = len(history)
        try:
            formatted = self.agent.model.format_message(role='user', content=context)
            items = formatted if isinstance(formatted, list) else [formatted]
            if not items or any(not isinstance(item, dict) for item in items):
                raise TypeError('formatted feedback must contain message dictionaries')
            # mini-SWE-agent add_messages accepts *messages, including adapters
            # that return multiple formatted messages.
            self.agent.add_messages(*items)
            if history is not messages:
                messages.extend(items)
            if not any(m.get('content') == context for m in messages[request_count:]):
                raise RuntimeError('diagnostic message absent from actual model request')
        except Exception:
            self._rollback_context_message(messages, request_count, history, history_count)
            raise
        return request_count, history, history_count

    @staticmethod
    def _rollback_context_message(messages, request_count, history, history_count):
        del messages[request_count:]
        if history is not messages:
            del history[history_count:]

    def query(self, messages, **kwargs):
        selected = None
        pending, self.pending = self.pending, []
        # If other actions ran after the failure snapshot, verify that the
        # observed locations still describe this workspace before delivering.
        freshness_error = None
        if pending and self.latest_snapshot_action != self.actions_observed:
            started = time.perf_counter()
            try:
                self.snapshot_count += 1
                self.latest_workspace_version = self._source_version(self.reader())
                self.latest_snapshot_action = self.actions_observed
            except Exception as exc:
                freshness_error = f'{type(exc).__name__}: {exc}'
            finally:
                self.feedback_total_seconds += time.perf_counter() - started
        for result, event in pending:
            started = time.perf_counter()
            try:
                if freshness_error or result.workspace_version != self.latest_workspace_version:
                    event.update(update_status='skipped', no_update_reason='workspace_changed_since_failure'
                        if not freshness_error else 'freshness_check_failed')
                    if freshness_error:
                        event['error'] = freshness_error
                    continue
                plan = prepare_feedback(result, modified_files=event['modified_files'],
                    previously_valid_files=event['previously_valid_files'],
                    previous_evidence=self.gate.last_evidence,
                    max_locations=3, max_message_chars=300)
                event.update(feedback_plan=plan.to_dict(), feedback_route=plan.route,
                             feedback_route_reason=plan.reason)
                if plan.route == 'skip':
                    event.update(update_status='skipped', no_update_reason=plan.reason)
                    continue
                ranking = self.ranking
                context = plan.context
                if plan.route == 'rank_update':
                    ranking = fuse_condition_d_for_agent(self.lexical, self.structural,
                        plan.ranking_candidates, failure_weight=self.failure_weight)
                    delta = self._ranking_delta(ranking)
                    if delta:
                        context += '\n' + delta
                prompt = select_prompt_candidates([LocalizationCandidate(**x) for x in ranking], self.top_k)
                # The exact final bounded text is both checked and acknowledged.
                allowed, reason = self.gate.check(plan, delivered_context=context)
                event.update(before_ranking=self.ranking, proposed_ranking=ranking,
                    prompt_candidates=[asdict(x) for x in prompt], localization_top_k=self.top_k,
                    proposed_context=context,
                    proposed_context_sha256=hashlib.sha256(context.encode()).hexdigest())
                if not allowed:
                    event.update(update_status='skipped', no_update_reason=reason)
                    continue
                if selected is not None:
                    event.update(update_status='skipped', no_update_reason='additional_failure_same_decision')
                    continue
                selected = plan, event, ranking, context
            except Exception as exc:
                event.update(update_status='skipped', no_update_reason='feedback_preparation_failed',
                             error=f'{type(exc).__name__}: {exc}')
            finally:
                self._record_feedback_time(event, started)
        injection = None
        if selected:
            plan, event, ranking, context = selected
            started = time.perf_counter()
            try:
                try:
                    injection = self._inject_context_message(messages, context)
                    event.update(delivered_context=context,
                        delivered_context_sha256=hashlib.sha256(context.encode()).hexdigest(),
                        update_status='awaiting_model_call')
                except Exception as exc:
                    event.update(update_status='failed', no_update_reason='context_injection_failed',
                                 error=f'{type(exc).__name__}: {exc}')
                    raise
            finally:
                self._record_feedback_time(event, started)
                self._persist()
        try:
            response = self._query(messages, **kwargs)
        except Exception as exc:
            if selected:
                selected[1].update(update_status='failed', no_update_reason='model_call_failed',
                                   error=f'{type(exc).__name__}: {exc}')
                self._rollback_context_message(messages, *injection)
            self._persist()
            raise
        if selected:
            plan, event, ranking, context = selected
            started = time.perf_counter()
            try:
                self.gate.mark_applied(plan, delivered_context=context)
                self.ranking = ranking
                self.applied += 1
                event.update(update_applied=True, ranking_updated=plan.route == 'rank_update',
                             update_status='applied', delivered_before_model_call=self.agent.n_calls)
            finally:
                self._record_feedback_time(event, started)
        self._persist()
        return response

    def close(self):
        if self.closed:
            return
        for _, event in self.pending:
            event.update(update_status='skipped', no_update_reason='no_subsequent_model_decision')
        self.pending.clear()
        self.agent.env.execute = self._execute
        self.agent.model.query = self._query
        self.closed = True
        self._persist()
        self._save_json('feedback_summary.json', self.summary())

    def summary(self):
        return {**failure_fusion_config(self.failure_weight,
                    max_updates=self.gate.limits['rank_update'],
                    max_recovery_updates=self.gate.limits['edit_recovery'],
                    max_diagnostic_updates=self.gate.limits['diagnostic_only']),
                'max_updates': self.gate.limits['rank_update'], 'context_top_k': self.top_k,
                'feedback_route_counts': self.gate.counts.copy(),
                'ranking_updates_applied': self.gate.counts['rank_update'],
                'recovery_messages_applied': self.gate.counts['edit_recovery'],
                'diagnostic_messages_applied': self.gate.counts['diagnostic_only'],
                'observations_recorded': len(self.observations),
                'failures_observed': sum(e['observation']['observed_failure'] for e in self.events),
                'actions_observed': self.actions_observed, 'process_failures': self.process_failures,
                'evidence_observations': len(self.events), 'analyses_completed': self.analysis_count,
                'runtime_snapshots_attempted': self.snapshot_count, 'updates_applied': self.applied,
                'localization_overhead_seconds': self.overhead_seconds,
                'initial_localization_seconds': self.initial_localization_seconds,
                'feedback_total_seconds': self.feedback_total_seconds,
                'initial_LS_fixed': True, 'failure_signal': 'status_or_observation_v2_first_eligible',
                'provenance_policy': 'execution_metadata_or_conservative_single_command_form',
                'deduplication': 'delivered_evidence_increment_and_final_context_with_workspace_and_index_scope',
                'log_directory': str(self.directory)}
