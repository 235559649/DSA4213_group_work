"""Regression checks against the published preliminary-report observations."""
import os
import unittest
from pathlib import Path

from tools.offline_eval.core import analyze

EXTERNAL_MANIFEST = os.environ.get("OFFLINE_EVAL_MANIFEST")


@unittest.skipUnless(EXTERNAL_MANIFEST, "Set OFFLINE_EVAL_MANIFEST to run full-evidence integration tests")
class RecordedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.analysis = analyze(Path(EXTERNAL_MANIFEST).resolve())
        cls.rows = cls.analysis["attempts"]

    def test_attempt_selection_and_missing_data(self):
        self.assertEqual(len(self.rows), 76)
        self.assertEqual(sum(r["selected"] for r in self.rows), 63)
        self.assertEqual(len({r["task_id"] for r in self.rows}), 8)
        self.assertEqual(self.analysis["missing_selected"], [])
        self.assertEqual(self.analysis["audit_failures"], [])

    def test_official_success_counts_match_reports(self):
        expected = {"original_dev5": [3, 4, 3, 3], "original_dev3": [2, 0, 1, 1],
                    "d_fix1": [1], "d_fix2_abcd": [0, 1, 1, 0], "prompt_policy4": [1, 1, 2, 2]}
        for experiment, counts in expected.items():
            with self.subTest(experiment=experiment):
                actual = [r["resolved"] for r in self.analysis["condition_summary"] if r["experiment_id"] == experiment]
                self.assertEqual(actual, counts)

    def test_four_task_usage_is_summed_over_all_responses(self):
        rows = [r for r in self.rows if r["experiment_id"] == "prompt_policy4"]
        self.assertEqual(sum(r["api_calls"] for r in rows), 259)
        self.assertEqual(sum(r["total_tokens"] for r in rows), 3900811)
        self.assertAlmostEqual(sum(r["cost_usd"] for r in rows), 0.77604795)

    def test_paid_retry_is_retained_without_becoming_a_new_task(self):
        rows = [r for r in self.rows if r["experiment_id"] == "d_fix2_abcd"]
        self.assertEqual(sum(r["api_calls"] for r in rows), 163)
        self.assertEqual(sum(r["api_calls"] for r in rows if r["selected"]), 149)
        self.assertAlmostEqual(sum(r["cost_usd"] for r in rows), 0.5144133)
        self.assertAlmostEqual(sum(r["cost_usd"] for r in rows if r["selected"]), 0.4778583)

    def test_new_d_timing_and_route_boundaries(self):
        rows = [r for r in self.rows if r["experiment_id"] == "prompt_policy4" and r["condition"] == "D"]
        self.assertAlmostEqual(sum(r["runtime_seconds"] for r in rows), 433.161599, places=4)
        self.assertAlmostEqual(sum(r["initial_localization_seconds"] for r in rows), 147.66718, places=4)
        self.assertAlmostEqual(sum(r["feedback_total_seconds"] for r in rows), 69.08141, places=4)
        events = [e for r in rows for e in r["feedback"]["events"] if e["delivery_found"]]
        self.assertEqual(len(events), 6)
        self.assertEqual(sum(e["route"] == "rank_update" for e in events), 5)
        self.assertEqual(sum(e["order_changed"] is True for e in events), 4)


if __name__ == "__main__":
    unittest.main()
