"""Synthetic boundary tests; no external packages or experiment execution."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.offline_eval.core import (
    analyze, complete_sum, feedback_events, feedback_summary, localization, measured,
    official_result, paired_rows, ranking_rows, response_usage, safe_path,
    sha256, summarize, verify_checksums, write_outputs,
)


def response(role="assistant", tokens=10, cost=0.1):
    return {"role": role, "extra": {"response": {"usage": {
        "prompt_tokens": tokens - 2, "completion_tokens": 2,
        "total_tokens": tokens, "cost": cost}}}}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


class MetricTests(unittest.TestCase):
    def test_format_error_response_is_counted(self):
        result = response_usage([response(), response("user", 20)], 2)
        self.assertEqual(result["total_tokens"], 30)
        self.assertEqual(result["api_calls"], 2)

    def test_unknown_cache_is_not_zero(self):
        self.assertIsNone(response_usage([response()], 1)["cached_input_tokens"])

    def test_partial_response_total_is_unknown(self):
        result = response_usage([response()], 2)
        self.assertFalse(result["response_count_matches"])
        self.assertIsNone(result["cost_usd"])
        self.assertEqual(result["partial_response_totals"]["total_tokens"], 10)

    def test_zero_call_infrastructure_attempt(self):
        result = response_usage([], 0)
        self.assertEqual(result["total_tokens"], 0)
        self.assertEqual(result["cost_usd"], 0)

    def test_unknown_is_not_zero(self):
        self.assertIsNone(complete_sum([1, None]))
        self.assertIsNone(complete_sum([]))
        self.assertEqual(measured([1, None]), {"sum": 1, "known": 1, "total": 2, "complete": False})

    def test_gapped_prompt_ranks_are_display_positions(self):
        full = [{"file": "a.py", "rank": 1}, {"file": "b.py", "rank": 12}]
        result = localization(full, [full[1]], ["b.py"], "C")
        self.assertEqual(result["target_ranks"]["b.py"], 12)
        self.assertEqual(result["target_display_positions"]["b.py"], 1)
        self.assertEqual(result["visible_hit"], 1)
        self.assertEqual(result["hit5"], 0)

    def test_multiple_targets_and_absent_target(self):
        result = localization([{"file": "a.py", "rank": 3}], [], ["a.py", "b.py"], "D")
        self.assertEqual(result["recall5"], 0.5)
        self.assertEqual(result["rr"], 1 / 3)
        self.assertEqual(result["visible_hit"], 0)

    def test_a_localization_is_not_applicable(self):
        self.assertIsNone(localization([], [], ["a.py"], "A")["rr"])

    def test_missing_rankings_are_not_empty_rankings(self):
        self.assertIsNone(localization(None, None, ["a.py"], "B")["rr"])
        self.assertEqual(localization([], [], ["a.py"], "B")["rr"], 0)

    def test_duplicate_rank_is_rejected(self):
        with self.assertRaises(ValueError):
            ranking_rows([{"file": "a", "rank": 1}, {"file": "b", "rank": 1}])

    def test_agent_submission_is_not_official_success(self):
        self.assertIsNone(official_result(None, "task")["resolved"])
        result = official_result({"task": {"resolved": False, "patch_successfully_applied": True}}, "task")
        self.assertFalse(result["resolved"])

    def test_wrong_official_task_is_rejected(self):
        with self.assertRaises(ValueError):
            official_result({"wrong": {"resolved": True}}, "task")

    def test_diagnostic_delivery_does_not_require_usable_rank_evidence(self):
        event = {"analysis": {"usable": False}, "feedback_route": "diagnostic_only",
                 "delivered_context": "diagnostic", "update_applied": True,
                 "delivered_context_sha256": sha256(b"diagnostic"), "delivered_before_model_call": 2}
        messages = [response(), {"role": "user", "content": "diagnostic"}]
        result = feedback_events([event], messages, ["a.py"])[0]
        self.assertTrue(result["delivery_found"])
        self.assertTrue(result["delivery_hash_matches"])
        self.assertIsNone(result["order_changed"])
        self.assertFalse(result["usable"])

    def test_repeated_feedback_uses_chronological_occurrences(self):
        events = [{"delivered_context": "same", "delivered_before_model_call": i} for i in (2, 3)]
        messages = [response(), {"content": "same"}, response(), {"content": "same"}]
        result = feedback_events(events, messages, None)
        self.assertEqual([r["next_model_call_from_trajectory"] for r in result], [2, 3])

    def test_rank_update_route_can_leave_order_unchanged(self):
        ranks = [{"file": "a.py", "rank": 1}]
        result = feedback_events([{"before_ranking": ranks, "proposed_ranking": ranks,
                                   "feedback_route": "rank_update"}], [], ["a.py"])[0]
        self.assertFalse(result["order_changed"])

    def test_first_usable_event_is_not_replaced_by_later_success(self):
        events = feedback_events([
            {"analysis": {"usable": True}, "update_applied": False},
            {"analysis": {"usable": True}, "update_applied": True, "delivered_context": "later"},
        ], [{"content": "later"}], ["a.py"])
        summary = feedback_summary(events, True)
        self.assertEqual(summary["first_usable"]["sequence"], 1)
        self.assertEqual(summary["first_delivered"]["sequence"], 2)
        self.assertEqual(summary["status"], "first_usable_not_applied")
        self.assertIsNone(summary["first_usable_delta_rr"])

    def test_path_escape_and_windows_absolute_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for path in ("../secret", "C:/secret", "foo\\bar", "/secret"):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    safe_path(Path(directory), path)

    def test_checksum_corruption_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "file.txt").write_text("changed", encoding="utf-8")
            (root / "checksums").write_text(sha256(b"original") + "  file.txt\n", encoding="utf-8")
            self.assertEqual(verify_checksums(root, root / "checksums")["failures"], ["file.txt"])

    def test_output_is_not_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                write_outputs({}, Path(directory))


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def manifest(self, count=2, repeats=1):
        tasks = [f"task-{i}" for i in range(count)]
        manifest = {"schema_version": 1, "experiments": [{"id": "sample", "tasks": tasks,
                    "conditions": ["D"], "repeat_ids": list(range(1, repeats + 1))}], "records": []}
        for task in tasks:
            for repeat in range(1, repeats + 1):
                run_id = task + f"-r{repeat}"
                result = {"run_id": run_id, "task_id": task, "condition": "D",
                          "usage": {"api_calls": 1, "cost_usd": 0.1}, "runtime_seconds": 5,
                          "config": {"failure_feedback": {"initial_localization_seconds": 1,
                                      "feedback_total_seconds": 2}}}
                write_json(self.root / run_id / "result.json", result)
                write_json(self.root / run_id / "trajectory.json", {"messages": [response()]})
                write_json(self.root / run_id / "official.json", {task: {"resolved": True}})
                manifest["records"].append({"experiment_id": "sample", "run_id": run_id, "task_id": task,
                    "condition": "D", "repeat_id": repeat, "attempt_id": 1, "selected": True,
                    "selection_reason": "Only planned attempt", "artifacts": {
                        "result": run_id + "/result.json", "trajectory": run_id + "/trajectory.json",
                        "official_report": run_id + "/official.json"}})
        return manifest

    def run_analysis(self, manifest):
        path = self.root / "manifest.json"
        write_json(path, manifest)
        return analyze(path)

    def test_variable_task_counts_and_d_only(self):
        for count in (1, 3, 6, 11):
            with self.subTest(count=count):
                result = self.run_analysis(self.manifest(count))
                self.assertEqual(len(result["attempts"]), count)
                self.assertEqual(result["condition_summary"][0]["resolved"], count)
                self.assertEqual(result["comparisons"], [])

    def test_repeats_are_separate_from_attempts(self):
        result = self.run_analysis(self.manifest(2, repeats=2))
        self.assertEqual(result["condition_summary"][0]["selected"], 4)

    def test_missing_selected_is_explicit(self):
        manifest = self.manifest(2)
        manifest["records"].pop()
        result = self.run_analysis(manifest)
        self.assertEqual(len(result["missing_selected"]), 1)
        self.assertEqual(result["condition_summary"][0]["missing_selected"], 1)

    def test_missing_official_report_is_unknown(self):
        manifest = self.manifest(2)
        del manifest["records"][0]["artifacts"]["official_report"]
        result = self.run_analysis(manifest)
        summary = result["condition_summary"][0]
        self.assertEqual(summary["official_evaluated"], 1)
        self.assertIsNone(summary["resolved_rate_selected"])

    def test_duplicate_selected_attempt_is_rejected(self):
        manifest = self.manifest(1)
        clone = dict(manifest["records"][0], run_id="duplicate", attempt_id=2)
        manifest["records"].append(clone)
        with self.assertRaises(ValueError):
            self.run_analysis(manifest)

    def test_duplicate_planned_tasks_cannot_inflate_denominator(self):
        manifest = self.manifest(1)
        manifest["experiments"][0]["tasks"].append("task-0")
        with self.assertRaises(ValueError):
            self.run_analysis(manifest)

    def test_excluded_attempt_must_still_belong_to_plan(self):
        manifest = self.manifest(1)
        manifest["records"][0].update(selected=False, condition="unplanned")
        with self.assertRaises(ValueError):
            self.run_analysis(manifest)

    def test_excluded_attempt_cost_is_retained(self):
        manifest = self.manifest(2)
        manifest["records"][0]["selected"] = False
        result = self.run_analysis(manifest)
        summary = result["condition_summary"][0]
        self.assertEqual(summary["selected_costs"]["cost_usd"]["sum"], 0.1)
        self.assertEqual(summary["all_attempt_costs"]["cost_usd"]["sum"], 0.2)

    def test_timing_subtotals_are_not_added_twice(self):
        result = self.run_analysis(self.manifest(1))
        costs = result["condition_summary"][0]["selected_costs"]
        self.assertEqual(costs["runtime_seconds"]["sum"], 5)
        self.assertEqual(costs["initial_localization_seconds"]["sum"], 1)
        self.assertEqual(costs["feedback_total_seconds"]["sum"], 2)

    def test_cross_version_pairs_do_not_require_same_retry_number(self):
        result = self.run_analysis(self.manifest(1))
        first = result["attempts"][0]
        second = dict(first, experiment_id="next", run_id="retry2", attempt_id=2, system_sha256="changed")
        pairs = paired_rows([first, second], ["sample"], ["next"])
        self.assertTrue(pairs[0]["matched"])
        self.assertEqual(pairs[0]["resolved_delta"], 0)

    def test_unmatched_tasks_are_kept(self):
        result = self.run_analysis(self.manifest(2))
        pairs = paired_rows(result["attempts"], ["sample"], ["absent"])
        self.assertEqual(len(pairs), 2)
        self.assertTrue(all(not row["matched"] for row in pairs))


if __name__ == "__main__":
    unittest.main()
