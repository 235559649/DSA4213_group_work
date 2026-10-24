from pathlib import Path

import pytest

from src.localization.structural import structural_ranking
from src.repository.indexer import build_index


@pytest.fixture(scope="module")
def index(tmp_path_factory):
    """a imports b and c; b imports d; e and test_a import a; f is isolated."""
    root: Path = tmp_path_factory.mktemp("repo")
    files = {
        "a.py": "import b\nimport c\n",
        "b.py": "import d\n",
        "c.py": "",
        "d.py": "",
        "e.py": "import a\n",
        "f.py": "",
        "test_a.py": "import a\n",
    }
    for name, text in files.items():
        (root / name).write_text(text, encoding="utf-8")
    return build_index(root)


def proposal_s(index, lexical, **kwargs):
    """S exactly as defined in the proposal: neighbors only."""
    return structural_ranking(index, lexical, include_seeds=False, **kwargs)


def ranked(candidates):
    return [(c.file, round(c.score, 4)) for c in candidates]


def test_proposal_formula(index):
    # Seed a (rank 1) has neighbors b, c, e (test_a excluded): 1/3 each.
    # Seed d (rank 2) has neighbor b: 1/2.
    result = proposal_s(index, [("a.py", 5.0), ("d.py", 3.0)])
    assert ranked(result) == [("b.py", 0.8333), ("c.py", 0.3333), ("e.py", 0.3333)]
    assert [c.rank for c in result] == [1, 2, 3]


def test_reasons_name_the_seeds(index):
    by_file = {c.file: c.reason for c in proposal_s(index, [("a.py", 5.0), ("d.py", 3.0)])}
    assert by_file["b.py"] == "imports lexical #2 d.py; imported by lexical #1 a.py"
    assert by_file["c.py"] == "imported by lexical #1 a.py"
    assert by_file["e.py"] == "imports lexical #1 a.py"


def test_test_files_can_be_included_as_neighbors(index):
    result = proposal_s(index, [("a.py", 5.0)], exclude_test_neighbors=False)
    assert ranked(result) == [("b.py", 0.25), ("c.py", 0.25), ("e.py", 0.25), ("test_a.py", 0.25)]


def test_test_file_seed_points_at_the_code_it_imports(index):
    assert ranked(proposal_s(index, [("test_a.py", 1.0)])) == [("a.py", 1.0)]


def test_ties_break_by_lexical_rank_then_path(index):
    # Seed a gives b, c, e 1/3 each; seed c (rank 2) gives a 1/2.
    result = proposal_s(index, [("a.py", 5.0), ("c.py", 1.0)])
    assert ranked(result) == [("a.py", 0.5), ("c.py", 0.3333), ("b.py", 0.3333), ("e.py", 0.3333)]


def test_only_positive_scores_and_first_seeds_count(index):
    assert proposal_s(index, [("a.py", 0.0), ("d.py", -1.0)]) == []
    result = proposal_s(index, [("a.py", 5.0), ("d.py", 3.0)], num_seeds=1)
    assert ranked(result) == [("b.py", 0.3333), ("c.py", 0.3333), ("e.py", 0.3333)]


def test_no_neighbors_gives_empty_ranking(index):
    assert proposal_s(index, [("f.py", 2.0), ("missing.py", 1.0)]) == []


def test_paths_are_normalized_and_duplicates_ignored(index):
    result = proposal_s(index, [(".\\a.py", 5.0), ("a.py", 4.0), ("./d.py", 3.0)])
    assert ranked(result) == [("b.py", 0.8333), ("c.py", 0.3333), ("e.py", 0.3333)]


def test_relations_are_structured(index):
    from src.localization.structural import IMPORTED_BY, IMPORTS

    by_file = {c.file: c for c in proposal_s(index, [("a.py", 5.0), ("d.py", 3.0)])}
    b = by_file["b.py"]
    assert [(r.seed, r.seed_rank, r.relation, round(r.weight, 4)) for r in b.relations] == [
        ("d.py", 2, IMPORTS, 0.5),
        ("a.py", 1, IMPORTED_BY, 0.3333),
    ]
    assert round(sum(r.weight for r in b.relations), 6) == round(b.score, 6)
    assert b.symbol is None and b.symbol_type is None


# ----- default: seeds head S (team decision 2026-10-19) -----


def test_seeds_head_s_in_lexical_order(index):
    result = structural_ranking(index, [("a.py", 5.0), ("d.py", 3.0)])
    assert ranked(result) == [
        ("a.py", 0.0),
        ("d.py", 0.0),
        ("b.py", 0.8333),
        ("c.py", 0.3333),
        ("e.py", 0.3333),
    ]
    assert [c.rank for c in result] == [1, 2, 3, 4, 5]
    assert result[0].reason == "lexical seed #1"


def test_seed_that_is_also_a_neighbor_keeps_both(index):
    from src.localization.structural import IMPORTS, SEED

    result = structural_ranking(index, [("a.py", 5.0), ("c.py", 1.0)])
    assert ranked(result) == [("a.py", 0.5), ("c.py", 0.3333), ("b.py", 0.3333), ("e.py", 0.3333)]
    a = result[0]
    assert [(r.relation, r.seed) for r in a.relations] == [(SEED, "a.py"), (IMPORTS, "c.py")]
    assert a.reason == "lexical seed #1; imports lexical #2 c.py"


def test_without_neighbors_s_is_just_the_seeds(index):
    # Fusing this S with L by RRF leaves L's order unchanged.
    result = structural_ranking(index, [("f.py", 2.0), ("missing.py", 1.0)])
    assert ranked(result) == [("f.py", 0.0), ("missing.py", 0.0)]
    assert structural_ranking(index, [("a.py", 0.0)]) == []


def test_only_the_first_seeds_head_s(index):
    result = structural_ranking(index, [("a.py", 5.0), ("d.py", 3.0)], num_seeds=1)
    assert [c.file for c in result] == ["a.py", "b.py", "c.py", "e.py"]
