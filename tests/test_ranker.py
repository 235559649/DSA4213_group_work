"""Tests for RRF ranking fusion."""

import pytest

from src.localization.ranker import (
    reciprocal_rank_fusion,
    fuse_condition_c,
    fuse_condition_d,
)


def test_rrf_score():
    """Check RRF scores with k=60."""
    lexical = [
        {"path": "a.py", "rank": 1},
        {"path": "b.py", "rank": 2},
    ]

    structural = [
        {"file": "b.py", "rank": 1},
        {"file": "a.py", "rank": 2},
    ]

    results = fuse_condition_c(lexical, structural)

    assert len(results) == 2
    assert results[0]["file"] == "a.py"
    assert results[1]["file"] == "b.py"

    expected = 1 / 61 + 1 / 62
    assert results[0]["rrf_score"] == pytest.approx(expected)


def test_rrf_single_ranking():
    """Check fusion with only one ranking."""
    lexical = [
        {"path": "a.py", "rank": 1},
        {"path": "b.py", "rank": 2},
    ]

    results = reciprocal_rank_fusion([lexical])

    assert [r["file"] for r in results] == ["a.py", "b.py"]


def test_rrf_condition_d():
    """Check failure ranking integration."""
    lexical = [
        {"path": "a.py", "rank": 1},
        {"path": "b.py", "rank": 2},
    ]

    structural = [
        {"file": "a.py", "rank": 1},
        {"file": "b.py", "rank": 2},
    ]

    failure = [
        {"file": "b.py", "rank": 1},
    ]

    results = fuse_condition_d(lexical, structural, failure)

    assert results[0]["file"] == "b.py"


def test_rrf_no_failure_fallback():
    """Condition D without failure evidence equals C."""
    lexical = [{"path": "a.py", "rank": 1}]
    structural = [{"file": "b.py", "rank": 1}]

    condition_c = fuse_condition_c(lexical, structural)
    condition_d = fuse_condition_d(lexical, structural)

    assert condition_c == condition_d


def test_rrf_invalid_k():
    """Reject invalid RRF k."""
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([], k=0)