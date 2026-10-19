"""Reciprocal Rank Fusion (RRF) for bug localization."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence


RRF_K = 60


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[Mapping[str, Any]]],
    k: int = RRF_K,
) -> list[dict[str, Any]]:
    """
    Fuse multiple file rankings using RRF.

    Supports:
    - BM25 ranking: {"path": ..., "rank": ..., "bm25_score": ...}
    - Structural ranking: {"file": ..., "rank": ..., "score": ...}
    - Failure ranking: {"file": ..., "rank": ..., "score": ...}

    Returns all ranked files, sorted by descending RRF score.
    """

    if k <= 0:
        raise ValueError("k must be positive")

    scores: dict[str, float] = defaultdict(float)

    for ranking in rankings:
        seen: set[str] = set()

        ordered = sorted(
            ranking,
            key=lambda item: item["rank"],
        )

        for item in ordered:
            path = item.get("file", item.get("path"))

            if not path:
                raise ValueError("Ranking item has no file path")

            if path in seen:
                continue

            seen.add(path)

            rank = int(item["rank"])

            if rank < 1:
                raise ValueError("Rank must be >= 1")

            scores[path] += 1.0 / (k + rank)

    fused = sorted(
        scores.items(),
        key=lambda item: (-item[1], item[0]),
    )

    return [
        {
            "file": path,
            "rank": rank,
            "rrf_score": round(score, 10),
        }
        for rank, (path, score) in enumerate(fused, start=1)
    ]


def fuse_condition_c(
    lexical_ranking: Sequence[Mapping[str, Any]],
    structural_ranking: Sequence[Mapping[str, Any]],
    k: int = RRF_K,
) -> list[dict[str, Any]]:
    """Condition C: fuse BM25 (L) and Structural Ranking (S)."""

    return reciprocal_rank_fusion(
        [lexical_ranking, structural_ranking],
        k=k,
    )


def fuse_condition_d(
    lexical_ranking: Sequence[Mapping[str, Any]],
    structural_ranking: Sequence[Mapping[str, Any]],
    failure_ranking: Sequence[Mapping[str, Any]] | None = None,
    k: int = RRF_K,
) -> list[dict[str, Any]]:
    """
    Condition D: fuse L, S and available failure ranking F.

    If failure evidence is unavailable, fall back to L + S.
    """

    rankings = [lexical_ranking, structural_ranking]

    if failure_ranking:
        rankings.append(failure_ranking)

    return reciprocal_rank_fusion(rankings, k=k)