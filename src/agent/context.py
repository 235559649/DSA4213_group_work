from __future__ import annotations

from src.agent.contracts import (
    LocalizationCandidate,
)
from src.repository.ast_parser import is_test_path

# Prompt policy (development revision, 2026-10-27). The candidate list shown
# to the agent holds source files only; the highest-ranked test files of the
# same ranking are listed separately as possibly relevant existing tests.
# The full ranking is still recorded unfiltered for evaluation.
PROMPT_POLICY = "source_only+related_tests_v1"
RELATED_TESTS_LIMIT = 3
_NON_SOURCE_TOP_DIRS = {"doc", "docs", "example", "examples"}


def is_source_file(path: str) -> bool:
    """Not a test, documentation or example file (same rule as the evaluation's target set)."""
    return not is_test_path(path) and path.split("/", 1)[0] not in _NON_SOURCE_TOP_DIRS


def select_related_tests(
    candidates: list[LocalizationCandidate],
    limit: int = RELATED_TESTS_LIMIT,
) -> list[str]:
    """The highest-ranked test files of a ranking, best first."""
    ordered = sorted(candidates, key=lambda candidate: (candidate.rank, candidate.file))
    tests: list[str] = []
    for candidate in ordered:
        if is_test_path(candidate.file) and candidate.file not in tests:
            tests.append(candidate.file)
            if len(tests) == limit:
                break
    return tests


def select_prompt_candidates(
    candidates: list[LocalizationCandidate],
    top_k: int | None,
    *,
    source_only: bool = True,
) -> list[LocalizationCandidate]:
    """
    Select the localization candidates that are actually
    shown to the agent.

    The full ranking should be preserved separately for
    evaluation and reproducibility.

    Parameters
    ----------
    candidates:
        Full localization ranking.

    top_k:
        Number of candidates to expose to the model.

        - None: expose the complete ranking.
        - positive integer: expose only the first top_k items.

    source_only:
        Skip test, documentation and example files, so the
        top_k slots go to source files (PROMPT_POLICY). Ranks
        keep their values from the full ranking.

    Returns
    -------
    list[LocalizationCandidate]
        Candidates ordered by rank.
    """

    if (
        top_k is not None
        and (
            isinstance(top_k, bool)
            or not isinstance(top_k, int)
            or top_k <= 0
        )
    ):
        raise ValueError(
            "localization top_k must be "
            "a positive integer or None."
        )

    ordered = sorted(
        candidates,
        key=lambda candidate: (
            candidate.rank,
            candidate.file,
        ),
    )

    if source_only:
        ordered = [
            candidate
            for candidate in ordered
            if is_source_file(candidate.file)
        ]

    if top_k is None:
        return ordered

    return ordered[:top_k]


def format_localization_context(
    candidates: list[LocalizationCandidate],
    related_tests: list[str] | None = None,
) -> str:
    """
    Convert the candidates selected for the prompt into
    text that can be injected into mini-SWE-agent.

    These candidates are guidance only. The agent may
    still inspect any repository file.
    """

    if not candidates:
        return ""

    lines = [
        (
            "Additional repository localization "
            "hints are provided below."
        ),
        (
            "These are navigation suggestions only. "
            "You may inspect any file in the "
            "repository if needed."
        ),
        "",
    ]

    for candidate in candidates:
        symbol_text = ""

        if candidate.symbol:
            symbol_type = (
                candidate.symbol_type
                or "symbol"
            )

            symbol_text = (
                f" | {symbol_type}: "
                f"{candidate.symbol}"
            )

        reason_text = (
            f" | reason: {candidate.reason}"
            if candidate.reason
            else ""
        )

        lines.append(
            f"{candidate.rank}. "
            f"{candidate.file}"
            f"{symbol_text}"
            f" | score: "
            f"{candidate.score:.4f}"
            f"{reason_text}"
        )

    if related_tests:
        lines.append("")
        lines.append(
            "Possibly relevant existing tests "
            "(from the same ranking):"
        )
        lines.extend(
            f"- {path}" for path in related_tests
        )

    return "\n".join(lines)


def augment_task_with_localization(
    task: str,
    candidates: list[LocalizationCandidate],
    related_tests: list[str] | None = None,
) -> str:
    """
    Append localization guidance to the original task.
    """

    context = (
        format_localization_context(
            candidates,
            related_tests,
        )
    )

    if not context:
        return task

    return (
        f"{task}\n\n"
        "----\n"
        "Repository localization guidance:\n"
        f"{context}"
    )