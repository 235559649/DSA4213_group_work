"""File-level localization metrics (evaluation protocol section 3.2)."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

DEFAULT_KS = (1, 5, 10, 20)


def first_hit(ranking: Sequence[str], targets: Iterable[str]) -> int | None:
    """1-based rank of the first target in `ranking`, or None if none appears."""
    targets = set(targets)
    for rank, path in enumerate(_dedupe(ranking), start=1):
        if path in targets:
            return rank
    return None


def score_ranking(
    ranking: Sequence[str], targets: Iterable[str], ks: Sequence[int] = DEFAULT_KS
) -> dict | None:
    """Hit@k, Recall@5 and reciprocal rank of one ranking; None when G is empty.

    A target absent from a complete ranking gives RR 0 (protocol 3.2).
    """
    targets = set(targets)
    if not targets:
        return None
    ranking = _dedupe(ranking)
    rank = first_hit(ranking, targets)
    scores = {"first_hit": rank, "rr": 1.0 / rank if rank else 0.0}
    for k in ks:
        scores[f"hit@{k}"] = int(rank is not None and rank <= k)
    scores["recall@5"] = len(targets & set(ranking[:5])) / len(targets)
    return scores


def summarize(per_task: Iterable[dict | None]) -> dict:
    """Mean of each metric over tasks with a non-empty G, plus that count."""
    scored = [s for s in per_task if s is not None]
    summary = {"tasks": len(scored)}
    if not scored:
        return summary
    for key in scored[0]:
        if key != "first_hit":
            summary[key] = sum(s[key] for s in scored) / len(scored)
    return summary


def _dedupe(ranking: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(ranking))
