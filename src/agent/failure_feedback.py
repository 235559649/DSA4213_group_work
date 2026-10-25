"""D runtime integration for mini-SWE-agent 2.4.6 (local integration candidate).

Uses existing Role 2 index updates, Role 3 fusion and Role 4 evidence/Gate.
Initial L/S are frozen per run. F is from one failed action; first eligible
failure per decision is delivered. No hidden evaluation inputs are used.
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import shlex
import time
from dataclasses import asdict

from src.agent.context import format_localization_context, select_prompt_candidates
from src.agent.contracts import LocalizationCandidate
from src.failure_analysis import UpdateGate, analyze_failure
from src.localization.keyword import BM25Retriever
from src.localization.ranker import fuse_condition_c_for_agent, fuse_condition_d_for_agent
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


class FailureFeedbackController:
    """Attach to the actual environment and model calls, without changing algorithms."""
    def __init__(self, agent, reader, task, run_dir, max_updates=3, top_k=5):
        # Same validation and selection semantics as Role 1's A/B/C context.
        select_prompt_candidates([], top_k)
        self.agent = agent
        self.reader = reader
        self.root = reader.root
        self.directory = Path(run_dir)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.gate = UpdateGate(max_updates)
        self.top_k = top_k
        self.pending = []
        self.events = []
        self.applied = 0
        self.closed = False
        self.overhead_seconds = 0.0
        self._execute = agent.env.execute
        self._query = agent.model.query
        started = time.monotonic()
        self.base_sources = reader()
        self.base = index_sources(self.base_sources,
            read_bytes=self.base_sources.__getitem__, file_size=lambda p: len(self.base_sources[p]))
        self.lexical = [{'path': p, 'rank': i, 'bm25_score': s} for i, (p, s) in
            enumerate(BM25Retriever(self.base).retrieve(task), 1)]
        self.structural = [asdict(x) for x in structural_ranking(self.base,
            [(x['path'], x['bm25_score']) for x in self.lexical])]
        self.ranking = fuse_condition_c_for_agent(self.lexical, self.structural)
        self._save_json('initial_rankings.json', {'index_sha256': self.base.digest(),
            'lexical': self.lexical, 'structural': self.structural, 'fused': self.ranking})
        self.overhead_seconds += time.monotonic() - started
        agent.env.execute = self.execute
        agent.model.query = self.query

    def _save_json(self, filename, value):
        (self.directory / filename).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

    def _persist(self):
        text = ''.join(json.dumps(e, ensure_ascii=False) + '\n' for e in self.events)
        (self.directory / 'failure_updates.jsonl').write_text(text, encoding='utf-8')

    def initial_candidates(self):
        return select_prompt_candidates(self.initial_full_candidates(), self.top_k)

    def initial_full_candidates(self):
        return [LocalizationCandidate(**x) for x in self.ranking]

    def execute(self, action, *args, **kwargs):
        response = self._execute(action, *args, **kwargs)
        if response.get('returncode') == 0:
            return response
        started = time.monotonic()
        number = len(self.events) + 1
        event = {'event_id': f'failure-{number}', 'step': self.agent.n_calls,
                 'returncode': response.get('returncode'), 'update_applied': False,
                 'update_status': 'pending', 'action': action}
        raw = response.get('output', '')
        evidence_file = f'failure-{number}-output.txt'
        (self.directory / evidence_file).write_text(raw, encoding='utf-8')
        event['raw_evidence'] = evidence_file
        try:
            # Snapshot immediately after the failing action, before another edit.
            sources = self.reader()
            changes = {p: sources.get(p) for p in set(sources) | set(self.base_sources)
                       if sources.get(p) != self.base_sources.get(p)}
            index = self.base.with_updated_files(changes)
            state = hashlib.sha256(json.dumps({p: hashlib.sha256(b).hexdigest()
                for p, b in sorted(sources.items())}, sort_keys=True).encode()).hexdigest()
            result = analyze_failure(raw, repo_root=self.root, index=index,
                workspace_version=state, index_is_current=True)
            event.update(analysis=result.to_dict(), workspace_version=state,
                         index_sha256=index.digest(), base_index_sha256=self.base.digest())
            self.pending.append((result, event))
        except Exception as exc:
            event.update(update_status='skipped', no_update_reason='snapshot_or_mapping_failed',
                         error=f'{type(exc).__name__}: {exc}')
        self.events.append(event)
        self.overhead_seconds += time.monotonic() - started
        self._persist()
        return response

    def query(self, messages, **kwargs):
        # Runs at the actual provider boundary, after Agent limit checks and
        # after all action observations have been added to the conversation.
        selected = None
        pending, self.pending = self.pending, []
        for result, event in pending:
            allowed, reason = self.gate.check(result)
            if not allowed:
                event.update(update_status='skipped', no_update_reason=reason)
            elif selected is not None:
                event.update(update_status='skipped', no_update_reason='additional_failure_same_decision')
            else:
                selected = result, event
        message_count = len(messages)
        if selected:
            result, event = selected
            ranking = fuse_condition_d_for_agent(self.lexical, self.structural,
                                               result.to_localization_candidates())
            prompt = select_prompt_candidates([LocalizationCandidate(**x) for x in ranking], self.top_k)
            context = 'Runtime failure localization update\n' + format_localization_context(
                prompt)
            event.update(before_ranking=self.ranking, proposed_ranking=ranking,
                         prompt_candidates=[asdict(x) for x in prompt], localization_top_k=self.top_k,
                         delivered_context=context, update_status='awaiting_model_call')
            try:
                added = self.agent.model.format_message(role='user', content=context)
                self.agent.add_messages(added)
            except Exception as exc:
                event.update(update_status='failed', no_update_reason='context_injection_failed',
                             error=f'{type(exc).__name__}: {exc}')
                self._persist()
                raise
            self._persist()
        try:
            response = self._query(messages, **kwargs)
        except Exception as exc:
            if selected:
                selected[1].update(update_status='failed', no_update_reason='model_call_failed',
                                   error=f'{type(exc).__name__}: {exc}')
                # No successful decision: remove only the new context message.
                del messages[message_count:]
            self._persist()
            raise
        if selected:
            result, event = selected
            self.gate.mark_applied(result)
            self.ranking = ranking
            self.applied += 1
            event.update(update_applied=True, update_status='applied',
                         delivered_before_model_call=self.agent.n_calls)
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
        return {'max_updates': self.gate.max_updates, 'context_top_k': self.top_k,
                'failures_observed': len(self.events), 'updates_applied': self.applied,
                'localization_overhead_seconds': self.overhead_seconds,
                'initial_LS_fixed': True, 'failure_signal': 'single_action_first_eligible_per_decision',
                'log_directory': str(self.directory)}
