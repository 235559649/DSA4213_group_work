from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.repository.models import IndexRecord

__all__ = [
    "IndexRecord",
    "LocalizationCandidate",
    "FailureEvent",
    "RunUsage",
    "RunResult",
]

@dataclass(frozen=True)
class LocalizationCandidate:
    """
    Ranked localization candidate.

    Mainly produced by Role 3 and consumed by Role 1.
    """
    file: str
    rank: int
    score: float

    symbol: str | None = None
    symbol_type: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class FailureEvent:
    """
    Runtime failure information.

    Mainly produced by Role 4.
    """
    exception_type: str | None = None
    traceback_files: list[str] = field(default_factory=list)
    traceback_symbols: list[str] = field(default_factory=list)
    failing_tests: list[str] = field(default_factory=list)
    identifiers: list[str] = field(default_factory=list)

    source: str = ""
    locatable: bool = False


@dataclass
class RunUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    api_calls: int | None = None
    cost_usd: float | None = None


@dataclass
class RunResult:
    """
    Unified result produced by Role 1.

    Role 5 should be able to consume this structure directly.
    """
    run_id: str
    task_id: str
    condition: str

    model: str
    mini_swe_agent_version: str | None

    status: str
    termination_reason: str

    trajectory_path: str
    patch_path: str

    runtime_seconds: float | None = None
    usage: RunUsage = field(default_factory=RunUsage)

    config: dict[str, Any] = field(default_factory=dict)
    evaluation: dict[str, Any] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                self.to_dict(),
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )