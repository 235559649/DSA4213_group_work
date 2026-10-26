import importlib.util
import json
from pathlib import Path

import pytest

from src.evaluation import gold
from src.evaluation.gold import ChangedFile, changed_files, target_files
from src.evaluation.localization import first_hit, score_ranking, summarize
from src.repository import swebench
from src.repository.indexer import build_index

PATCH = """diff --git a/pkg/core.py b/pkg/core.py
index 1..2 100644
--- a/pkg/core.py
+++ b/pkg/core.py
@@ -1 +1 @@
-x = 1
+x = 2
diff --git a/pkg/new.py b/pkg/new.py
new file mode 100644
--- /dev/null
+++ b/pkg/new.py
@@ -0,0 +1 @@
+y = 1
diff --git a/pkg/old.py b/pkg/old.py
deleted file mode 100644
diff --git a/tests/test_core.py b/tests/test_core.py
--- a/tests/test_core.py
+++ b/tests/test_core.py
diff --git a/docs/conf.py b/docs/conf.py
--- a/docs/conf.py
+++ b/docs/conf.py
diff --git a/README.rst b/README.rst
--- a/README.rst
+++ b/README.rst
diff --git a/pkg/a.py b/pkg/b.py
similarity index 90%
rename from pkg/a.py
rename to pkg/b.py
"""


def test_changed_files_reads_status_from_git_headers():
    assert changed_files(PATCH) == [
        ChangedFile("pkg/core.py", "modified"),
        ChangedFile("pkg/new.py", "added"),
        ChangedFile("pkg/old.py", "deleted"),
        ChangedFile("tests/test_core.py", "modified"),
        ChangedFile("docs/conf.py", "modified"),
        ChangedFile("README.rst", "modified"),
        ChangedFile("pkg/b.py", "renamed"),
    ]


def test_target_files_keep_only_modified_indexed_source(tmp_path):
    for rel in ["pkg/core.py", "pkg/old.py", "tests/test_core.py", "docs/conf.py", "pkg/a.py"]:
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text("x = 1\n", encoding="utf-8")
    changes = changed_files(PATCH) + [ChangedFile("pkg/gone.py", "modified")]

    targets, excluded = target_files(changes, build_index(tmp_path))
    assert targets == ["pkg/core.py"]
    assert excluded == {
        "pkg/new.py": "added",
        "pkg/old.py": "deleted",
        "tests/test_core.py": "test",
        "docs/conf.py": "documentation",
        "README.rst": "not_python",
        "pkg/b.py": "renamed",
        "pkg/gone.py": "not_indexed",
    }


def test_reference_files_cache_keeps_file_lists_not_patches(tmp_path, monkeypatch):
    pa = pytest.importorskip("pyarrow")
    pq = pytest.importorskip("pyarrow.parquet")
    secret = "x = 'REFERENCE-SOLUTION-TEXT'"
    patch = f"diff --git a/pkg/core.py b/pkg/core.py\n--- a/pkg/core.py\n+++ b/pkg/core.py\n+{secret}\n"
    table = pa.table({"instance_id": ["acme__shop-1"], "patch": [patch], "test_patch": ["t"]})
    monkeypatch.setattr(swebench, "_fetch", lambda url, dest: pq.write_table(table, dest))

    refs = gold.reference_files(tmp_path)
    assert refs == {"acme__shop-1": [ChangedFile("pkg/core.py", "modified")]}
    cached = "".join(p.read_text(encoding="utf-8") for p in (tmp_path / "eval").iterdir())
    assert secret not in cached and "REFERENCE-SOLUTION-TEXT" not in cached
    assert not list(tmp_path.rglob("*.parquet"))


# ----- metrics (proposal 5.2) -----


def test_first_hit_and_scores():
    ranking = ["a.py", "b.py", "a.py", "c.py", "d.py", "e.py", "f.py"]
    assert first_hit(ranking, {"c.py"}) == 3  # duplicates do not shift ranks
    scores = score_ranking(ranking, {"c.py", "f.py", "z.py"})
    assert scores["first_hit"] == 3
    assert scores["rr"] == pytest.approx(1 / 3)
    assert (scores["hit@1"], scores["hit@5"]) == (0, 1)
    assert scores["recall@5"] == pytest.approx(1 / 3)  # c.py in top 5; f.py, z.py not


def test_target_absent_from_ranking_scores_zero():
    scores = score_ranking(["a.py", "b.py"], {"z.py"})
    assert scores["first_hit"] is None and scores["rr"] == 0.0 and scores["hit@20"] == 0


def test_empty_target_set_is_not_scored():
    assert score_ranking(["a.py"], set()) is None
    summary = summarize([score_ranking(["a.py"], {"a.py"}), None, score_ranking(["b.py"], {"a.py"})])
    assert summary["tasks"] == 2
    assert summary["rr"] == 0.5 and summary["hit@1"] == 0.5


# ----- comparison table -----


def _load_script(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parents[1] / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_run(root: Path, run_id: str, condition: str, resolved, files=None, prompt=None, events=None, summary=None):
    run = root / run_id
    run.mkdir(parents=True)
    config = {"failure_feedback": summary} if summary else {}
    evaluation = {"official_swebench_evaluation": {"resolved": resolved}} if resolved is not None else {}
    (run / "run_result.json").write_text(json.dumps({
        "run_id": run_id, "task_id": "acme__shop-1", "condition": condition,
        "config": config, "evaluation": evaluation, "usage": {"cost_usd": 0.01},
    }), encoding="utf-8")
    if files is not None:
        (run / "localization_candidates.json").write_text(json.dumps([{"file": f} for f in files]), encoding="utf-8")
    if prompt is not None:
        (run / "prompt_candidates.json").write_text(json.dumps([{"file": f} for f in prompt]), encoding="utf-8")
    if events is not None:
        (run / "failure_feedback").mkdir()
        (run / "failure_feedback" / "failure_updates.jsonl").write_text(
            "".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    return run


def test_comparison_rows_per_condition(tmp_path):
    comparison = _load_script("run_comparison")
    targets = ["pkg/core.py"]
    ranking = ["pkg/x.py", "pkg/y.py", "pkg/core.py"]

    a = comparison.read_run(_write_run(tmp_path, "run_A_00000001", "A", True), targets)
    assert (a["delivered_rank"], a["prompt_size"], a["resolved"]) == (None, None, True)

    b = comparison.read_run(_write_run(tmp_path, "run_B_00000002", "B", False, ranking, ranking[:2]), targets)
    assert (b["delivered_rank"], b["prompt_rank"], b["prompt_size"]) == (3, None, 2)

    events = [
        {"analysis": {"usable": False}, "update_status": "skipped"},
        {"analysis": {"usable": True}, "update_status": "applied", "update_applied": True,
         "before_ranking": [{"file": f} for f in ranking],
         "proposed_ranking": [{"file": f} for f in ["pkg/core.py", "pkg/x.py"]]},
    ]
    d = comparison.read_run(
        _write_run(tmp_path, "run_D_00000003", "D", None, ranking, ranking, events,
                   {"failures_observed": 2, "updates_applied": 1}),
        targets,
    )
    assert (d["d_failures"], d["d_updates"]) == (2, 1)
    assert d["d_first_usable"] == {"status": "applied", "before": 3, "after": 1}

    text = comparison.render([a, b, d], {"acme__shop-1": targets}, show_paths=False)
    assert "3 -> 1" in text and "not evaluated" in text
    assert "pkg/core.py" not in text  # paths only with --show-paths
    assert "| B | 1 | 0/1 | 0/1 |" in text
    assert "| D | 1 | 0/0 (1 not evaluated) | 1/1 | 1/1 |" in text


def test_d_run_without_usable_failure(tmp_path):
    comparison = _load_script("run_comparison")
    d = comparison.read_run(
        _write_run(tmp_path, "run_D_1", "D", True, ["pkg/core.py"], ["pkg/core.py"],
                   [{"analysis": {"usable": False}}], {"failures_observed": 1, "updates_applied": 0}),
        ["pkg/core.py"],
    )
    assert d["d_first_usable"] is None
    assert "none" in comparison.render([d], {"acme__shop-1": ["pkg/core.py"]}, show_paths=False)


def test_missing_run_files_are_missing_not_misses(tmp_path):
    comparison = _load_script("run_comparison")
    c = comparison.read_run(_write_run(tmp_path, "run_C_1", "C", True), ["pkg/core.py"])
    text = comparison.render([c], {"acme__shop-1": ["pkg/core.py"]}, show_paths=False)
    assert "| missing | missing |" in text
    assert "| C | 1 | 1/1 | 0/0 (1 missing) |" in text
