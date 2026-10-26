"""D runtime integration for mini-SWE-agent 2.4.6.

Uses existing Role 2 index updates, Role 3 fusion and Role 4 evidence/Gate.
Initial L/S are frozen per run. Runtime failure evidence may add F; the first
eligible feedback item per model decision is delivered. No hidden evaluation
inputs are used.
"""
from __future__ import annotations

import base64
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shlex
import time

from src.agent.context import format_localization_context, select_prompt_candidates
from src.agent.contracts import LocalizationCandidate
from src.failure_analysis import UpdateGate, analyze_failure
from src.failure_analysis.observation import detect_observation
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
                raise RuntimeError("D source snapshot exceeds 64 MiB limit")

            data = file.read_bytes()
            size += len(data)
            if size > SNAPSHOT_LIMIT:
                raise RuntimeError("D source snapshot exceeds 64 MiB limit")
            files[path] = data

        return files


class RemoteSourceReader:
    """Read task Python sources through the existing container executor.

    No host paths/credentials are mounted. Invalid, truncated or oversized
    output is a snapshot failure, never a claim of a fresh index.
    """

    def __init__(self, execute, root="/testbed"):
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
'''.replace("ROOT", repr(self.root), 1)

        encoded = base64.b64encode(code.encode()).decode()
        command = "python -c " + shlex.quote(
            "import base64;exec(base64.b64decode('" + encoded + "'))"
        )
        response = self.execute({"command": command})
        if response.get("returncode") != 0:
            raise RuntimeError("D container snapshot command failed")

        raw = response.get("output", "")
        if len(raw) > SNAPSHOT_LIMIT * 2:
            raise RuntimeError("D encoded snapshot exceeds limit")

        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("D snapshot must be a path-content mapping")

        return {
            path: base64.b64decode(data, validate=True)
            for path, data in payload.items()
        }


class FailureFeedbackController:
    """Attach runtime localization feedback to the actual agent/model boundary."""

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
        self.observations = []
        self.applied = 0
        self.closed = False
        self.overhead_seconds = 0.0
        self.feedback_total_seconds = 0.0

        self._execute = agent.env.execute
        self._query = agent.model.query

        started = time.monotonic()
        timing_started = time.perf_counter()

        self.base_sources = reader()
        self.base = index_sources(
            self.base_sources,
            read_bytes=self.base_sources.__getitem__,
            file_size=lambda p: len(self.base_sources[p]),
        )
        self.lexical = [
            {"path": path, "rank": rank, "bm25_score": score}
            for rank, (path, score) in enumerate(
                BM25Retriever(self.base).retrieve(task),
                1,
            )
        ]
        self.structural = [
            asdict(candidate)
            for candidate in structural_ranking(
                self.base,
                [(item["path"], item["bm25_score"]) for item in self.lexical],
            )
        ]
        self.ranking = fuse_condition_c_for_agent(self.lexical, self.structural)

        self._save_json(
            "initial_rankings.json",
            {
                "index_sha256": self.base.digest(),
                "lexical": self.lexical,
                "structural": self.structural,
                "fused": self.ranking,
            },
        )

        self.initial_localization_seconds = time.perf_counter() - timing_started
        self.overhead_seconds += time.monotonic() - started

        agent.env.execute = self.execute
        agent.model.query = self.query

    def _save_json(self, filename, value):
        (self.directory / filename).write_text(
            json.dumps(value, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _persist(self):
        event_text = "".join(
            json.dumps(event, ensure_ascii=False) + "\n"
            for event in self.events
        )
        (self.directory / "failure_updates.jsonl").write_text(
            event_text,
            encoding="utf-8",
        )

        observation_text = "".join(
            json.dumps(observation, ensure_ascii=False) + "\n"
            for observation in self.observations
        )
        (self.directory / "observations.jsonl").write_text(
            observation_text,
            encoding="utf-8",
        )

    def initial_candidates(self):
        return select_prompt_candidates(self.initial_full_candidates(), self.top_k)

    def initial_full_candidates(self):
        return [LocalizationCandidate(**item) for item in self.ranking]

    def _record_feedback_time(self, event, started):
        # Accumulate active D-feedback processing only; never command/model wait.
        elapsed = time.perf_counter() - started
        event["feedback_processing_seconds"] += elapsed
        self.feedback_total_seconds += elapsed

    @staticmethod
    def _message_items(formatted):
        """Return formatted model messages as a list without changing contents."""
        if isinstance(formatted, list):
            return formatted
        return [formatted]

    def _inject_context_message(self, messages, context):
        """Inject feedback and ensure the list passed to _query sees it.

        mini-SWE-agent normally passes its live message list to model.query(), so
        add_messages() should update ``messages`` in place. If a future adapter
        passes a distinct list, mirror the exact formatted message into that
        request list as well. Counts are returned so a failed call can roll back
        both lists without consuming an update.
        """
        request_count = len(messages)
        agent_messages = getattr(self.agent, "messages", None)
        agent_count = len(agent_messages) if isinstance(agent_messages, list) else None

        formatted = self.agent.model.format_message(role="user", content=context)
        try:
            self.agent.add_messages(formatted)

            if len(messages) == request_count:
                messages.extend(self._message_items(formatted))

            if len(messages) == request_count:
                raise RuntimeError(
                    "failure feedback context was not added to model messages"
                )
        except Exception:
            self._rollback_context_message(
                messages,
                request_count,
                agent_messages,
                agent_count,
            )
            raise

        return request_count, agent_messages, agent_count

    @staticmethod
    def _rollback_context_message(messages, request_count, agent_messages, agent_count):
        """Remove only feedback messages added for the failed model decision."""
        del messages[request_count:]

        if (
            isinstance(agent_messages, list)
            and agent_messages is not messages
            and agent_count is not None
        ):
            del agent_messages[agent_count:]

    def execute(self, action, *args, **kwargs):
        response = self._execute(action, *args, **kwargs)

        raw = response.get("output", "")
        returncode = response.get("returncode")

        # Provenance metadata must come from a trusted execution layer. The
        # current generic executor may not provide it, so rc=0/unknown evidence
        # remains diagnostic-only rather than being promoted by command guessing.
        trusted_kind = response.get("observation_kind", "unknown")
        is_truncated = response.get("output_truncated", False)

        observed = detect_observation(
            raw,
            returncode=returncode,
            observation_kind=trusted_kind,
            output_truncated=is_truncated,
        )

        self.observations.append(
            {
                "step": self.agent.n_calls,
                "action": action,
                "observation": observed.to_dict(),
            }
        )
        self._persist()

        # Weak/source-display/expected/unknown rc=0 diagnostics are retained in
        # observations.jsonl but never become F candidates or consume updates.
        if not observed.should_analyze:
            return response

        started = time.monotonic()
        timing_started = time.perf_counter()
        number = len(self.events) + 1
        event = {
            "event_id": f"failure-{number}",
            "step": self.agent.n_calls,
            "returncode": returncode,
            "update_applied": False,
            "update_status": "pending",
            "action": action,
            "feedback_processing_seconds": 0.0,
            "observation": observed.to_dict(),
        }

        evidence_file = f"failure-{number}-output.txt"
        (self.directory / evidence_file).write_text(raw, encoding="utf-8")
        event["raw_evidence"] = evidence_file

        try:
            # Snapshot immediately after the observed failing action, before
            # another edit, so traceback lines map to the current workspace.
            sources = self.reader()
            changes = {
                path: sources.get(path)
                for path in set(sources) | set(self.base_sources)
                if sources.get(path) != self.base_sources.get(path)
            }
            index = self.base.with_updated_files(changes)
            state = hashlib.sha256(
                json.dumps(
                    {
                        path: hashlib.sha256(data).hexdigest()
                        for path, data in sorted(sources.items())
                    },
                    sort_keys=True,
                ).encode()
            ).hexdigest()

            result = analyze_failure(
                raw,
                repo_root=self.root,
                index=index,
                workspace_version=state,
                index_is_current=True,
            )
            event.update(
                analysis=result.to_dict(),
                workspace_version=state,
                index_sha256=index.digest(),
                base_index_sha256=self.base.digest(),
            )
            self.pending.append((result, event))
        except Exception as exc:
            event.update(
                update_status="skipped",
                no_update_reason="snapshot_or_mapping_failed",
                error=f"{type(exc).__name__}: {exc}",
            )

        self.events.append(event)
        self.overhead_seconds += time.monotonic() - started
        self._record_feedback_time(event, timing_started)
        self._persist()
        return response

    def query(self, messages, **kwargs):
        # Runs at the actual provider boundary, after Agent limit checks and
        # after all action observations have been added to the conversation.
        selected = None
        pending, self.pending = self.pending, []

        # Build the COMPLETE candidate text before Gate checking. New-mode Gate
        # deduplication is based on the exact final text plus workspace/index.
        for result, event in pending:
            started = time.perf_counter()
            try:
                if not result.usable:
                    event.update(
                        update_status="skipped",
                        no_update_reason=result.reason,
                    )
                    continue

                ranking = fuse_condition_d_for_agent(
                    self.lexical,
                    self.structural,
                    result.to_localization_candidates(),
                )
                prompt = select_prompt_candidates(
                    [LocalizationCandidate(**item) for item in ranking],
                    self.top_k,
                )

                ranking_context = (
                    "Runtime failure localization update\n"
                    + format_localization_context(prompt)
                )
                diagnostic_context = result.format_feedback_evidence(
                    max_locations=3,
                    max_message_chars=300,
                )
                context = ranking_context + "\n\n" + diagnostic_context

                allowed, reason = self.gate.check(
                    result,
                    delivered_context=context,
                )
                if not allowed:
                    event.update(
                        update_status="skipped",
                        no_update_reason=reason,
                    )
                    continue

                # Only the first actually eligible failure is delivered for this
                # model decision. Later eligible candidates remain audited.
                if selected is not None:
                    event.update(
                        update_status="skipped",
                        no_update_reason="additional_failure_same_decision",
                    )
                    continue

                selected = (result, event, ranking, prompt, context)
            finally:
                self._record_feedback_time(event, started)

        injection_state = None

        if selected is not None:
            result, event, ranking, prompt, context = selected
            started = time.perf_counter()
            try:
                event.update(
                    before_ranking=self.ranking,
                    proposed_ranking=ranking,
                    prompt_candidates=[asdict(candidate) for candidate in prompt],
                    localization_top_k=self.top_k,
                    delivered_context=context,
                    update_status="awaiting_model_call",
                )

                try:
                    injection_state = self._inject_context_message(messages, context)
                except Exception as exc:
                    event.update(
                        update_status="failed",
                        no_update_reason="context_injection_failed",
                        error=f"{type(exc).__name__}: {exc}",
                    )
                    if injection_state is not None:
                        self._rollback_context_message(messages, *injection_state)
                    raise
            finally:
                self._record_feedback_time(event, started)
                self._persist()

        try:
            response = self._query(messages, **kwargs)
        except Exception as exc:
            if selected is not None:
                _, event, _, _, _ = selected
                event.update(
                    update_status="failed",
                    no_update_reason="model_call_failed",
                    error=f"{type(exc).__name__}: {exc}",
                )
                if injection_state is not None:
                    self._rollback_context_message(messages, *injection_state)
            self._persist()
            raise

        if selected is not None:
            result, event, ranking, prompt, context = selected
            started = time.perf_counter()
            try:
                # A successful model decision is the acknowledgement boundary.
                # Use the exact same final context that was checked and delivered.
                self.gate.mark_applied(
                    result,
                    delivered_context=context,
                )
                self.ranking = ranking
                self.applied += 1
                event.update(
                    update_applied=True,
                    update_status="applied",
                    delivered_before_model_call=self.agent.n_calls,
                )
            finally:
                self._record_feedback_time(event, started)

        self._persist()
        return response

    def close(self):
        if self.closed:
            return

        for _, event in self.pending:
            event.update(
                update_status="skipped",
                no_update_reason="no_subsequent_model_decision",
            )
        self.pending.clear()

        self.agent.env.execute = self._execute
        self.agent.model.query = self._query
        self.closed = True
        self._persist()
        self._save_json("feedback_summary.json", self.summary())

    def summary(self):
        return {
            "max_updates": self.gate.max_updates,
            "context_top_k": self.top_k,
            "observations_recorded": len(self.observations),
            "failures_observed": len(self.events),
            "updates_applied": self.applied,
            "localization_overhead_seconds": self.overhead_seconds,
            "initial_localization_seconds": self.initial_localization_seconds,
            "feedback_total_seconds": self.feedback_total_seconds,
            "initial_LS_fixed": True,
            "failure_signal": "observed_runtime_evidence_first_eligible_per_decision",
            "observation_provenance": "trusted_metadata_or_unknown",
            "log_directory": str(self.directory),
        }
