"""Contract tests for Role 3's agent-facing ranking functions."""

from src.localization.ranker import (
    fuse_condition_c,
    fuse_condition_c_for_agent,
    fuse_condition_d,
    fuse_condition_d_for_agent,
)


L = [{"path": "a.py", "rank": 1}, {"path": "b.py", "rank": 2}]
S = [{"file": "b.py", "rank": 1}, {"file": "a.py", "rank": 2}]
F = [{"file": "b.py", "rank": 1, "score": 1.0,
      "symbol": None, "symbol_type": None, "reason": "direct_source_frame"}]


def test_condition_d_agent_contract():
    output = fuse_condition_d_for_agent(L, S, F)
    assert output[0]["file"] == "b.py"
    assert [x["rank"] for x in output] == [1, 2]
    assert all(set(x) == {"file", "rank", "score", "symbol", "symbol_type", "reason"}
               for x in output)
    assert all(x["reason"] == "RRF(L,S,F)" for x in output)
    assert [x["score"] for x in output] == [x["rrf_score"] for x in fuse_condition_d(L, S, F)]


def test_empty_failure_falls_back_to_c():
    c = fuse_condition_c_for_agent(L, S)
    assert fuse_condition_d_for_agent(L, S, []) == c
    assert fuse_condition_d_for_agent(L, S, None) == c
    assert [x["score"] for x in c] == [x["rrf_score"] for x in fuse_condition_c(L, S)]
