from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def test_summary(
    report: dict,
    category: str,
) -> dict:
    status = (
        report
        .get("tests_status", {})
        .get(category, {})
    )

    success = status.get(
        "success",
        [],
    )

    failure = status.get(
        "failure",
        [],
    )

    return {
        "passed": len(success),
        "failed": len(failure),
        "success_tests": success,
        "failure_tests": failure,
    }


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--run-dir",
        required=True,
    )

    parser.add_argument(
        "--report",
        required=True,
    )

    parser.add_argument(
        "--evaluation-run-id",
        required=True,
    )

    parser.add_argument(
        "--dataset",
        default="SWE-bench/SWE-bench_Lite",
    )

    parser.add_argument(
        "--split",
        default="dev",
    )

    args = parser.parse_args()

    run_dir = Path(
        args.run_dir
    ).resolve()

    result_path = (
        run_dir
        / "run_result.json"
    )

    report_path = Path(
        args.report
    ).resolve()

    result = load_json(
        result_path
    )

    report = load_json(
        report_path
    )

    instance_id = result[
        "task_id"
    ]

    if instance_id not in report:
        raise KeyError(
            "Evaluation report does not contain "
            f"{instance_id!r}"
        )

    instance_report = report[
        instance_id
    ]

    official_result = {
        "dataset":
            args.dataset,

        "split":
            args.split,

        "evaluation_run_id":
            args.evaluation_run_id,

        "resolved":
            instance_report.get(
                "resolved"
            ),

        "patch_exists":
            instance_report.get(
                "patch_exists"
            ),

        "patch_successfully_applied":
            instance_report.get(
                "patch_successfully_applied"
            ),

        "infra_failure":
            instance_report.get(
                "infra_failure"
            ),

        "FAIL_TO_PASS":
            test_summary(
                instance_report,
                "FAIL_TO_PASS",
            ),

        "PASS_TO_PASS":
            test_summary(
                instance_report,
                "PASS_TO_PASS",
            ),
    }

    evaluation = result.get(
        "evaluation"
    )

    if not isinstance(
        evaluation,
        dict,
    ):
        evaluation = {}

    evaluation[
        "official_swebench_evaluation"
    ] = official_result

    result[
        "evaluation"
    ] = evaluation

    result_path.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print(
        "Updated:",
        result_path,
    )

    print(
        "resolved:",
        official_result["resolved"],
    )

    print(
        "patch_successfully_applied:",
        official_result[
            "patch_successfully_applied"
        ],
    )

    print(
        "FAIL_TO_PASS:",
        official_result[
            "FAIL_TO_PASS"
        ]["passed"],
        "passed /",
        official_result[
            "FAIL_TO_PASS"
        ]["failed"],
        "failed",
    )

    print(
        "PASS_TO_PASS:",
        official_result[
            "PASS_TO_PASS"
        ]["passed"],
        "passed /",
        official_result[
            "PASS_TO_PASS"
        ]["failed"],
        "failed",
    )


if __name__ == "__main__":
    main()
