from __future__ import annotations

from src.agent.contracts import (
    LocalizationCandidate,
)

REPAIR_GUIDANCE_VERSION = 'closed_loop_v2'
REPAIR_GUIDANCE = """
Repository investigation and verification:
- Use localization hints as leads. Inspect the relevant implementation before
  editing; if you skip a high-ranked plausible candidate, explain why and follow
  evidence to another location. A filename or one traceback line is not enough
  to establish the cause. Do not open every candidate just to satisfy a checklist.
- Turn the public issue's expected behavior into executable assertions. Check
  the original reproduction after edits, relevant alternative/default branches,
  and available nearby regression tests. Derive expectations only from the issue
  and repository specification, never hidden evaluation tests or reference fixes.
- Run reproduction/test commands separately from source display or git diff so
  a later successful command cannot mask a failure. If you catch an unexpected
  exception for diagnostics, print the full traceback and preserve failure status.
- A printed result, successful compilation, or a narrow example is not proof of
  correctness. Before submission, revisit visible exceptions and failed assertions;
  fix them or explicitly report unresolved behavior and validation limitations.
  If tests are unavailable, report that limitation rather than claiming they pass.
""".strip()


def with_repair_guidance(system_template: str) -> str:
    """Same verification instruction for every A/B/C/D run in the v2 protocol."""
    return system_template + '\n\n' + REPAIR_GUIDANCE


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
        "Inspect plausible implementation candidates before editing; explain evidence-based departures from the ranking.",
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

        # Historical C artifacts used RRF while D used RRF(L,S). Normalize
        # this presentation-only alias; keep full saved ranking metadata intact.
        reason = 'RRF(L,S)' if candidate.reason in {'RRF', 'RRF(L,S)'} else candidate.reason
        reason_text = (
            f" | reason: {reason}"
            if reason
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
