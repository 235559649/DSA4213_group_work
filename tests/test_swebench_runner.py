from src.agent.contracts import (
    LocalizationCandidate,
)
from src.agent.swebench_runner import (
    SWEbenchRunner,
)

import json
import src.agent.swebench_runner as swebench_runner_module

class FakeRepositoryIndex:
    files = [
        "src/a.py",
        "src/b.py",
    ]

    records = [
        object(),
        object(),
        object(),
    ]

    errors = []

    metadata = {
        "repo": "owner/repo",
        "commit": "abc123",
        "index_sha256": "index-sha",
    }

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

def test_run_preserves_full_ranking_and_prompt_top_k(
    tmp_path,
    monkeypatch,
):
    task_config = (
        tmp_path
        / "task.json"
    )

    task_config.write_text(
        json.dumps({
            "instance_id": "task-a",
            "problem_statement": (
                "Fix the parser bug."
            ),
            "benchmark": "swebench",
            "split": "dev",
            "repo": "example/repo",
            "version": "1.0",
            "base_commit": "abc123",
        }),
        encoding="utf-8",
    )

    candidates = [
        LocalizationCandidate(
            file="src/a.py",
            rank=1,
            score=10.0,
            reason="BM25",
        ),
        LocalizationCandidate(
            file="src/b.py",
            rank=2,
            score=9.0,
            reason="BM25",
        ),
        LocalizationCandidate(
            file="src/c.py",
            rank=3,
            score=8.0,
            reason="BM25",
        ),
    ]

    class FakeEnvironment:
        def cleanup(self):
            pass

    class FakeAgent:
        def __init__(
            self,
            trajectory_path,
        ):
            self.trajectory_path = (
                trajectory_path
            )

        def run(
            self,
            task,
        ):
            submission = (
                "diff --git a/src/a.py "
                "b/src/a.py\n"
                "--- a/src/a.py\n"
                "+++ b/src/a.py\n"
                "@@ -1 +1 @@\n"
                "-old\n"
                "+new\n"
            )

            trajectory = {
                "info": {
                    "submission":
                        submission,
                    "exit_status":
                        "Submitted",
                    "model_stats": {
                        "api_calls": 0,
                        "instance_cost": 0,
                    },
                    "config": {
                        "agent": {},
                        "environment": {},
                    },
                },
                "messages": [
                    {
                        "role": "user",
                        "content": task,
                    }
                ],
            }

            self.trajectory_path.write_text(
                json.dumps(
                    trajectory
                ),
                encoding="utf-8",
            )

            return {
                "exit_status":
                    "Submitted",
                "submission":
                    submission,
            }

    monkeypatch.setattr(
        swebench_runner_module,
        "build_task_index",
        lambda instance_id: FakeRepositoryIndex(),
    )
    runner = SWEbenchRunner(
        output_root=(
            tmp_path
            / "runs"
        )
    )

    def fake_build_agent(
        *,
        instance_id,
        trajectory_path,
    ):
        assert (
            instance_id
            == "task-a"
        )

        return (
            FakeAgent(
                trajectory_path
            ),
            FakeEnvironment(),
        )

    monkeypatch.setattr(
        runner,
        "_build_agent",
        fake_build_agent,
    )

    result = runner.run(
        instance_id="task-a",
        task_config=task_config,
        condition="B",
        localization_candidates=(
            candidates
        ),
        localization_top_k=2,
    )

    run_dir = (
        tmp_path
        / "runs"
        / result.run_id
    )

    full = json.loads(
        (
            run_dir
            / "localization_candidates.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    prompt = json.loads(
        (
            run_dir
            / "prompt_candidates.json"
        ).read_text(
            encoding="utf-8"
        )
    )

    effective_task = (
        run_dir
        / "effective_task.txt"
    ).read_text(
        encoding="utf-8"
    )

    assert len(full) == 3
    assert len(prompt) == 2

    assert (
        prompt[0]["file"]
        == "src/a.py"
    )

    assert (
        prompt[1]["file"]
        == "src/b.py"
    )

    assert "src/a.py" in effective_task
    assert "src/b.py" in effective_task
    assert "src/c.py" not in effective_task

    assert (
        result.config[
            "localization_source"
        ]
        == "bm25"
    )

    assert (
        result.config[
            "localization_full_ranking_size"
        ]
        == 3
    )

    assert (
        result.config[
            "localization_top_k"
        ]
        == 2
    )

    assert (
        result.config[
            "localization_prompt_candidate_count"
        ]
        == 2
    )

    assert result.usage.api_calls == 0
    assert result.usage.cost_usd == 0

    assert (
        result.config[
            "repository_index"
        ]
        == {
            "instance_id": "task-a",
            "repo": "owner/repo",
            "base_commit": "abc123",
            "index_sha256": "index-sha",
            "file_count": 2,
            "record_count": 3,
            "error_count": 0,
        }
    )

def test_repository_index_metadata(
    tmp_path,
    monkeypatch,
):
    class FakeIndex:
        files = [
            "src/a.py",
            "src/b.py",
        ]

        records = [
            object(),
            object(),
            object(),
        ]

        errors = []

        metadata = {
            "repo": "owner/repo",
            "commit": "abc123",
            "index_sha256": "sha256-test",
        }

    monkeypatch.setattr(
        swebench_runner_module,
        "build_task_index",
        lambda instance_id: FakeIndex(),
    )

    runner = SWEbenchRunner(
        output_root=(
            tmp_path
            / "runs"
        )
    )

    metadata = (
        runner._build_repository_index_metadata(
            "task-a"
        )
    )

    assert metadata == {
        "instance_id": "task-a",
        "repo": "owner/repo",
        "base_commit": "abc123",
        "index_sha256": "sha256-test",
        "file_count": 2,
        "record_count": 3,
        "error_count": 0,
    }


def _timing_runner(tmp_path, monkeypatch, build_agent):
    task_config = tmp_path / "task.json"
    task_config.write_text(
        json.dumps({
            "instance_id": "task-a",
            "problem_statement": "Fix the parser bug.",
            "benchmark": "swebench",
            "split": "dev",
            "repo": "example/repo",
            "version": "1.0",
            "base_commit": "abc123",
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        swebench_runner_module,
        "build_task_index",
        lambda instance_id: FakeRepositoryIndex(),
    )
    runner = SWEbenchRunner(output_root=tmp_path / "runs")
    monkeypatch.setattr(runner, "_build_agent", build_agent)
    return runner.run(instance_id="task-a", task_config=task_config, condition="A")


def test_run_records_setup_agent_and_teardown_time(tmp_path, monkeypatch):
    class FakeEnvironment:
        def cleanup(self):
            pass

    class FakeAgent:
        def __init__(self, trajectory_path):
            self.trajectory_path = trajectory_path

        def run(self, task):
            self.trajectory_path.write_text(
                json.dumps({"info": {"submission": "", "exit_status": "Submitted",
                                     "model_stats": {"api_calls": 0, "instance_cost": 0}}}),
                encoding="utf-8",
            )
            return {"exit_status": "Submitted", "submission": ""}

    result = _timing_runner(
        tmp_path,
        monkeypatch,
        lambda *, instance_id, trajectory_path: (FakeAgent(trajectory_path), FakeEnvironment()),
    )

    timing = result.config["timing"]
    assert set(timing) == {"env_setup_seconds", "agent_seconds", "env_teardown_seconds"}
    assert all(isinstance(v, float) and v >= 0 for v in timing.values())
    # The phases are parts of runtime_seconds (two clocks, so allow a little slack).
    assert sum(timing.values()) <= result.runtime_seconds + 0.05


def test_failed_container_start_still_records_setup_time(tmp_path, monkeypatch):
    def failing_build_agent(*, instance_id, trajectory_path):
        raise RuntimeError("docker start-up timed out")

    result = _timing_runner(tmp_path, monkeypatch, failing_build_agent)

    timing = result.config["timing"]
    assert "docker start-up timed out" in result.error
    assert isinstance(timing["env_setup_seconds"], float)
    assert timing["agent_seconds"] is None
    assert isinstance(timing["env_teardown_seconds"], float)
