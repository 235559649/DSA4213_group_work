"""Structural file ranking S from one-hop import neighbors (Condition C).

Implements proposal section 3.4, "Structure-Aware Localization":

* Q: up to the first `num_seeds` (10) files with positive scores in the
  lexical ranking L.
* N(q): repository files that seed q imports or that import q, from the
  index's import graph, excluding q itself.
* Each seed distributes 1 / r_L(q) equally among its distinct neighbors:

      s_struct(f) = sum over q in Q of [f in N(q)] / (r_L(q) * max(1, |N(q)|))

* S: files with a positive score, by score; ties broken by lexical rank
  (files missing from L rank last), then by path.

If no seed has a neighbor, S is empty and Condition C keeps L unchanged.
Fusing L and S with RRF is done by the retrieval module (role 3).

One design choice beyond the proposal, `exclude_test_neighbors` (default on):
test files may still be seeds, since a test file points at the code it
tests through its imports, but they are not counted as neighbors. Otherwise a
widely imported source file's weight is spread over dozens of test files, and
S fills up with tests, which are not localization targets.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from src.repository.indexer import RepositoryIndex, to_repo_path

DEFAULT_NUM_SEEDS = 10
MAX_REASONS = 3


IMPORTED_BY = "imported_by"  # the candidate is imported by the seed
IMPORTS = "imports"  # the candidate imports the seed


@dataclass(frozen=True)
class Relation:
    """One seed's contribution to a candidate's structural score."""

    seed: str  # the lexical file this relation comes from
    seed_rank: int  # its rank in L
    relation: str  # IMPORTED_BY or IMPORTS
    weight: float  # 1 / (seed_rank * |N(seed)|)


@dataclass(frozen=True)
class StructuralCandidate:
    """One file in S.

    `file`, `rank`, `score`, `symbol`, `symbol_type` and `reason` follow
    LocalizationCandidate (src/agent/contracts.py). S is file-level, so
    `symbol` and `symbol_type` are always None.
    """

    file: str
    rank: int
    score: float  # s_struct(file), the sum of the relation weights
    relations: tuple[Relation, ...]  # every contributing seed, strongest first
    reason: str  # the strongest relations as text, "imported by lexical #1 shop/pricing.py"
    symbol: None = None
    symbol_type: None = None


def structural_ranking(
    index: RepositoryIndex,
    lexical: Sequence[tuple[str, float]],
    *,
    num_seeds: int = DEFAULT_NUM_SEEDS,
    exclude_test_neighbors: bool = True,
) -> list[StructuralCandidate]:
    """Rank files by import proximity to the top lexical files.

    `lexical` is L as (path, score) pairs, best first, e.g. the output of
    BM25Retriever.retrieve. Pass the full positive ranking, not only the
    seeds: lexical ranks are also used to break ties.
    """
    lexical_rank: dict[str, int] = {}
    for path, score in lexical:
        path = to_repo_path(path) or path
        if score > 0 and path not in lexical_rank:
            lexical_rank[path] = len(lexical_rank) + 1
    seeds = [path for path, rank in lexical_rank.items() if rank <= num_seeds]

    scores: dict[str, float] = {}
    relations: dict[str, list[Relation]] = {}
    for seed in seeds:
        rank = lexical_rank[seed]
        imports = set(index.imports_of(seed))
        neighbors = [
            n
            for n in index.neighbors(seed)
            if not (exclude_test_neighbors and index.is_test_file(n))
        ]
        if not neighbors:
            continue
        weight = 1.0 / (rank * len(neighbors))
        for neighbor in neighbors:
            scores[neighbor] = scores.get(neighbor, 0.0) + weight
            relation = IMPORTED_BY if neighbor in imports else IMPORTS
            relations.setdefault(neighbor, []).append(Relation(seed, rank, relation, weight))

    never = len(lexical_rank) + 1
    ordered = sorted(scores, key=lambda f: (-scores[f], lexical_rank.get(f, never), f))
    candidates = []
    for i, f in enumerate(ordered, start=1):
        strongest = tuple(sorted(relations[f], key=lambda r: (-r.weight, r.seed_rank)))
        reason = "; ".join(
            f"{r.relation.replace('_', ' ')} lexical #{r.seed_rank} {r.seed}"
            for r in strongest[:MAX_REASONS]
        )
        candidates.append(StructuralCandidate(f, i, scores[f], strongest, reason))
    return candidates
