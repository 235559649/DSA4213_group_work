import json

import pytest

from scripts.run_agent import (
    load_candidates,
)


def test_load_role3_bm25_batch(
    tmp_path,
):
    path = (
        tmp_path
        / "bm25.json"
    )

    path.write_text(
        json.dumps([
            {
                "instance_id":
                    "task-a",
                "ranked_files": [
                    {
                        "path":
                            "src/a.py",
                        "rank":
                            1,
                        "bm25_score":
                            12.5,
                    },
                    {
                        "path":
                            "src/b.py",
                        "rank":
                            2,
                        "bm25_score":
                            8.0,
                    },
                ],
            }
        ]),
        encoding="utf-8",
    )

    result = load_candidates(
        str(path),
        instance_id="task-a",
    )

    assert len(result) == 2

    assert (
        result[0].file
        == "src/a.py"
    )

    assert (
        result[0].score
        == 12.5
    )

    assert (
        result[0].reason
        == "BM25"
    )


def test_load_role3_rrf_batch(
    tmp_path,
):
    path = (
        tmp_path
        / "rrf.json"
    )

    path.write_text(
        json.dumps([
            {
                "instance_id":
                    "task-a",
                "condition":
                    "C",
                "rrf_k":
                    60,
                "ranked_files": [
                    {
                        "file":
                            "src/a.py",
                        "rank":
                            1,
                        "rrf_score":
                            0.032,
                    }
                ],
            }
        ]),
        encoding="utf-8",
    )

    result = load_candidates(
        str(path),
        instance_id="task-a",
    )

    assert len(result) == 1

    assert (
        result[0].file
        == "src/a.py"
    )

    assert (
        result[0].score
        == 0.032
    )

    assert (
        result[0].reason
        == "RRF"
    )


def test_load_batch_requires_matching_instance(
    tmp_path,
):
    path = (
        tmp_path
        / "ranking.json"
    )

    path.write_text(
        json.dumps([
            {
                "instance_id":
                    "task-a",
                "ranked_files":
                    [],
            }
        ]),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="No ranking found",
    ):
        load_candidates(
            str(path),
            instance_id="task-b",
        )


def test_reject_unknown_candidate_schema(
    tmp_path,
):
    path = (
        tmp_path
        / "bad.json"
    )

    path.write_text(
        json.dumps([
            {
                "rank": 1,
                "unknown": 123,
            }
        ]),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match=(
            "Unsupported localization "
            "candidate schema"
        ),
    ):
        load_candidates(
            str(path)
        )