from __future__ import annotations

from src.agent.contracts import (
    LocalizationCandidate,
)


def select_prompt_candidates(
    candidates: list[LocalizationCandidate],
    top_k: int | None,
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

    if top_k is None:
        return ordered

    return ordered[:top_k]


def format_localization_context(
    candidates: list[LocalizationCandidate],
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

    return "\n".join(lines)


def augment_task_with_localization(
    task: str,
    candidates: list[LocalizationCandidate],
) -> str:
    """
    Append localization guidance to the original task.
    """

    context = (
        format_localization_context(
            candidates
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