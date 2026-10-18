"""Offline failure evidence and runtime ranking. No BM25, RRF or agent calls."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass

from src.failure_analysis.test_parser import parse_failing_tests
from src.failure_analysis.traceback_parser import clean_output, parse_traceback
from src.repository.indexer import RepositoryIndex, to_repo_path


@dataclass(frozen=True)
class FailureAnalysis:
    """Role 4 draft wire format; serialize with to_dict for other roles."""

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

    def to_dict(self) -> dict:
        return asdict(self)


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
    environment_hint = any(marker in text.lower() for marker in (
        "command not found", "no module named", "could not resolve host",
        "no matching distribution found", "permission denied", "timed out",
    ))
    reason = (
        "stale_index" if not index_is_current else
        "mapped_source_frames" if candidates else
        "empty_output" if not text.strip() else
        "environment_hint_without_source" if environment_hint else
        "test_only_evidence" if tests or any(m['status'] == 'test_only' for m in mappings) else
        "no_mapped_source"
    )
    mapped = [m for m in mappings if m['status'] in {'source', 'test_only'}]
    event = {
        "exception_type": parsed.exception_types[-1] if parsed.exception_types else None,
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
