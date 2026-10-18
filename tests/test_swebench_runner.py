from src.agent.contracts import (
    LocalizationCandidate,
)
from src.agent.swebench_runner import (
    SWEbenchRunner,
)


def test_extract_patch_from_submission():
    trajectory = {
        "info": {
            "submission": (
                "diff --git a/src/a.py b/src/a.py\n"
                "--- a/src/a.py\n"
                "+++ b/src/a.py\n"
                "@@ -1 +1 @@\n"
                "-old\n"
                "+new\n"
            )
        },
        "messages": [],
    }

    patch = (
        SWEbenchRunner.extract_patch(
            trajectory
        )
    )

    assert (
        "diff --git a/src/a.py"
        in patch
    )

    assert "+new" in patch


def test_extract_patch_from_messages():
    trajectory = {
        "info": {
            "submission": ""
        },
        "messages": [
            {
                "role": "tool",
                "content": (
                    "<returncode>0</returncode>\n"
                    "<output>\n"
                    "diff --git a/src/a.py b/src/a.py\n"
                    "--- a/src/a.py\n"
                    "+++ b/src/a.py\n"
                    "@@ -1 +1 @@\n"
                    "-old\n"
                    "+new\n"
                    "</output>"
                ),
            }
        ],
    }

    patch = (
        SWEbenchRunner.extract_patch(
            trajectory
        )
    )

    assert (
        "diff --git a/src/a.py"
        in patch
    )

    assert "+new" in patch
    assert "</output>" not in patch


def test_condition_a_keeps_original_task():
    task = (
        "Fix the DateTime nesting bug."
    )

    result = (
        SWEbenchRunner.build_effective_task(
            task=task,
            condition="A",
            localization_candidates=[],
        )
    )

    assert result == task


def test_condition_b_adds_localization():
    task = (
        "Fix the DateTime nesting bug."
    )

    candidates = [
        LocalizationCandidate(
            file=(
                "src/marshmallow/"
                "fields.py"
            ),
            rank=1,
            score=1.0,
            symbol="DateTime",
            symbol_type="class",
            reason="BM25 lexical match",
        )
    ]

    result = (
        SWEbenchRunner.build_effective_task(
            task=task,
            condition="B",
            localization_candidates=(
                candidates
            ),
        )
    )

    # Original SWE-bench issue remains present.
    assert task in result

    # Localization guidance is appended.
    assert (
        "Repository localization guidance"
        in result
    )

    assert (
        "src/marshmallow/fields.py"
        in result
    )

    assert "DateTime" in result

    assert (
        "BM25 lexical match"
        in result
    )


def test_condition_b_requires_candidates():
    try:
        SWEbenchRunner.build_effective_task(
            task="Fix the bug.",
            condition="B",
            localization_candidates=[],
        )

    except ValueError as exc:
        assert (
            "requires localization candidates"
            in str(exc)
        )

    else:
        raise AssertionError(
            "Condition B should require "
            "localization candidates."
        )