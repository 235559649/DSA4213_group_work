"""Prompt policy source_only+related_tests_v1 (src/agent/context.py)."""

import json

import src.agent.swebench_runner as swebench_runner_module
from src.agent.context import (
    PROMPT_POLICY,
    augment_task_with_localization,
    format_localization_context,
    is_source_file,
    select_prompt_candidates,
    select_related_tests,
)
from src.agent.contracts import LocalizationCandidate
from src.agent.swebench_runner import SWEbenchRunner

RANKING = [
    LocalizationCandidate(file="tests/test_parser.py", rank=1, score=9.0),
    LocalizationCandidate(file="docs/conf.py", rank=2, score=8.0),
    LocalizationCandidate(file="src/parser.py", rank=3, score=7.0),
    LocalizationCandidate(file="src/tests/test_lexer.py", rank=4, score=6.0),
    LocalizationCandidate(file="examples/demo.py", rank=5, score=5.0),
    LocalizationCandidate(file="src/lexer.py", rank=6, score=4.0),
    LocalizationCandidate(file="testing/test_io.py", rank=7, score=3.0),
    LocalizationCandidate(file="tests/conftest.py", rank=8, score=2.0),
]


def test_is_source_file():
    assert is_source_file("src/parser.py")
    # Known limitation, shared with the evaluation's target set: any directory
    # named test/tests/testing counts as test code, so Django's own test
    # framework (django/test/) is not offered as a candidate. No SWE-bench
    # Verified reference patch modifies such a file (checked 2026-10-27).
    assert not is_source_file("django/test/utils.py")
    for path in ["tests/test_parser.py", "src/tests/test_lexer.py", "docs/conf.py",
                 "doc/usage/example.py", "examples/demo.py", "pkg/conftest.py"]:
        assert not is_source_file(path)


def test_prompt_holds_source_files_only_and_keeps_full_ranks():
    prompt = select_prompt_candidates(RANKING, 2)
    assert [(c.file, c.rank) for c in prompt] == [("src/parser.py", 3), ("src/lexer.py", 6)]
    # The old behaviour stays available for comparisons.
    assert [c.file for c in select_prompt_candidates(RANKING, 2, source_only=False)] == [
        "tests/test_parser.py",
        "docs/conf.py",
    ]


def test_related_tests_are_the_top_test_files_of_the_same_ranking():
    assert select_related_tests(RANKING) == [
        "tests/test_parser.py",
        "src/tests/test_lexer.py",
        "testing/test_io.py",
    ]
    assert select_related_tests(RANKING, limit=1) == ["tests/test_parser.py"]
    assert select_related_tests([c for c in RANKING if is_source_file(c.file)]) == []


def test_context_lists_related_tests_separately():
    prompt = select_prompt_candidates(RANKING, 2)
    text = format_localization_context(prompt, ["tests/test_parser.py"])
    assert "3. src/parser.py" in text
    assert text.endswith("Possibly relevant existing tests (from the same ranking):\n- tests/test_parser.py")
    assert "Possibly relevant" not in format_localization_context(prompt)
    assert "tests/test_parser.py" in augment_task_with_localization("Fix it.", prompt, ["tests/test_parser.py"])


class _FakeIndex:
    files = ["src/parser.py"]
    records = []
    errors = []
    metadata = {"repo": "example/repo", "commit": "abc123", "index_sha256": "x", "schema_version": 4}

    def digest(self):
        return "x"


def test_runner_applies_and_records_the_policy(tmp_path, monkeypatch):
    task_config = tmp_path / "task.json"
    task_config.write_text(json.dumps({
        "instance_id": "task-a", "problem_statement": "Fix the parser bug.", "benchmark": "swebench",
        "split": "dev", "repo": "example/repo", "version": "1.0", "base_commit": "abc123",
    }), encoding="utf-8")

    seen_tasks = []

    class FakeEnvironment:
        def cleanup(self):
            pass

    class FakeAgent:
        def __init__(self, trajectory_path):
            self.trajectory_path = trajectory_path

        def run(self, task):
            seen_tasks.append(task)
            self.trajectory_path.write_text(json.dumps({"info": {
                "submission": "", "exit_status": "Submitted",
                "model_stats": {"api_calls": 0, "instance_cost": 0}}}), encoding="utf-8")
            return {"exit_status": "Submitted", "submission": ""}

    monkeypatch.setattr(swebench_runner_module, "build_task_index", lambda instance_id: _FakeIndex())
    runner = SWEbenchRunner(output_root=tmp_path / "runs")
    monkeypatch.setattr(runner, "_build_agent",
                        lambda *, instance_id, trajectory_path: (FakeAgent(trajectory_path), FakeEnvironment()))

    result = runner.run(instance_id="task-a", task_config=task_config, condition="B",
                        localization_candidates=RANKING, localization_top_k=2)

    (task,) = seen_tasks
    assert "src/parser.py" in task and "src/lexer.py" in task
    assert "docs/conf.py" not in task
    assert "- tests/test_parser.py" in task  # listed as a related test, not as a candidate
    assert result.config["localization_prompt_policy"] == PROMPT_POLICY
    assert result.config["localization_related_tests"] == [
        "tests/test_parser.py", "src/tests/test_lexer.py", "testing/test_io.py"]
    run_dir = tmp_path / "runs" / result.run_id
    full = json.loads((run_dir / "localization_candidates.json").read_text(encoding="utf-8"))
    assert len(full) == len(RANKING)  # the full ranking is still recorded unfiltered
