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


def test_swebench_phase2_rejects_condition_b(
    tmp_path,
):
    runner = SWEbenchRunner(
        output_root=tmp_path
    )

    try:
        runner.run(
            instance_id="example__repo-1",
            task_config=(
                tmp_path
                / "missing.json"
            ),
            condition="B",
        )
    except NotImplementedError:
        pass
    else:
        raise AssertionError(
            "Condition B should not be "
            "enabled in Phase 2."
        )
