from __future__ import annotations

from src.agent.contracts import LocalizationCandidate


def format_localization_context(
    candidates: list[LocalizationCandidate],
) -> str:
    """
    Convert Role 3's candidate list into text that can be injected
    into mini-SWE-agent.

    The candidates are guidance only. The agent may still inspect
    any repository file.
    """

    if not candidates:
        return ""

    lines = [
        "Additional repository localization hints are provided below.",
        "These are navigation suggestions only. You may inspect any file "
        "in the repository if needed.",
        "",
    ]

    for candidate in candidates:
        symbol_text = ""

        if candidate.symbol:
            symbol_type = candidate.symbol_type or "symbol"
            symbol_text = (
                f" | {symbol_type}: {candidate.symbol}"
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
            f" | score: {candidate.score:.4f}"
            f"{reason_text}"
        )

    return "\n".join(lines)


def augment_task_with_localization(
    task: str,
    candidates: list[LocalizationCandidate],
) -> str:
    context = format_localization_context(candidates)

    if not context:
        return task

    return (
        f"{task}\n\n"
        "----\n"
        "Repository localization guidance:\n"
        f"{context}"
    )