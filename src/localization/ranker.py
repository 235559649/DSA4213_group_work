"""Reciprocal Rank Fusion (RRF) for bug localization."""

from __future__ import annotations

from collections import defaultdict
from itertools import repeat
import math
from numbers import Real
from typing import Any, Iterable, Mapping, Sequence


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

    return _weighted_rank_fusion(rankings, repeat(1.0), k)


def _weighted_rank_fusion(
    rankings: Sequence[Sequence[Mapping[str, Any]]],
    weights: Iterable[float],
    k: int,
) -> list[dict[str, Any]]:
    """Shared accumulator; public unweighted RRF keeps its exact old behavior."""
    if k <= 0:
        raise ValueError("k must be positive")

    scores: dict[str, float] = defaultdict(float)

    for ranking, weight in zip(rankings, weights):
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

            scores[path] += weight / (k + rank)

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
    *,
    failure_weight: float = 1.0,
) -> list[dict[str, Any]]:
    """
    Condition D: fuse L, S and available failure ranking F.

    L and S retain weight 1. F contributes failure_weight / (k + rank).
    Input score fields are not used as weights. If F is unavailable, return
    exactly Condition C, regardless of the valid configured failure weight.
    Default weight 1.0 preserves the previous D output and positional k calls.
    """
    if isinstance(failure_weight, bool) or not isinstance(failure_weight, Real):
        raise ValueError('failure_weight must be a finite positive number')
    try:
        weight = float(failure_weight)
    except (OverflowError, ValueError):
        raise ValueError('failure_weight must be a finite positive number') from None
    if not math.isfinite(weight) or weight <= 0:
        raise ValueError('failure_weight must be a finite positive number')
    if not failure_ranking:
        return fuse_condition_c(lexical_ranking, structural_ranking, k=k)
    return _weighted_rank_fusion(
        [lexical_ranking, structural_ranking, failure_ranking], [1.0, 1.0, weight], k)

def to_agent_candidates(
    fused_ranking: Sequence[Mapping[str, Any]],
    reason: str,
) -> list[dict[str, Any]]:
    """Convert a complete RRF ranking to Role 3's six-field agent contract."""
    return [
        {
            "file": item["file"],
            "rank": item["rank"],
            "score": item["rrf_score"],
            "symbol": None,
            "symbol_type": None,
            "reason": reason,
        }
        for item in fused_ranking
    ]


def fuse_condition_c_for_agent(
    lexical_ranking: Sequence[Mapping[str, Any]],
    structural_ranking: Sequence[Mapping[str, Any]],
    k: int = RRF_K,
) -> list[dict[str, Any]]:
    """Condition C complete ranking in the agreed agent-facing format."""
    fused = fuse_condition_c(lexical_ranking, structural_ranking, k=k)
    return to_agent_candidates(fused, reason="RRF(L,S)")


def fuse_condition_d_for_agent(
    lexical_ranking: Sequence[Mapping[str, Any]],
    structural_ranking: Sequence[Mapping[str, Any]],
    failure_ranking: Sequence[Mapping[str, Any]] | None = None,
    k: int = RRF_K,
    *,
    failure_weight: float = 1.0,
) -> list[dict[str, Any]]:
    """Condition D complete ranking; empty F falls back to Condition C."""
    fused = fuse_condition_d(lexical_ranking, structural_ranking, failure_ranking,
        k=k, failure_weight=failure_weight)
    reason = "RRF(L,S,F)" if failure_ranking else "RRF(L,S)"
    return to_agent_candidates(fused, reason=reason)
