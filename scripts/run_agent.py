from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)

sys.path.insert(
    0,
    str(PROJECT_ROOT),
)


from src.agent.contracts import (  # noqa: E402
    LocalizationCandidate,
)
from src.agent.mini_swe_wrapper import (  # noqa: E402
    MiniSWEWrapper,
)
from src.agent.swebench_runner import (  # noqa: E402
    SWEbenchRunner,
)


def load_candidates(
    path: str | None,
) -> list[LocalizationCandidate]:

    if not path:
        return []

    data = json.loads(
        Path(path).read_text(
            encoding="utf-8"
        )
    )

    return [
        LocalizationCandidate(**item)
        for item in data
    ]


def require(
    parser: argparse.ArgumentParser,
    value,
    option: str,
):
    if not value:
        parser.error(
            f"{option} is required for "
            "the selected benchmark mode."
        )

    return value


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--benchmark",
        choices=[
            "local",
            "swebench",
        ],
        default="local",
    )

    parser.add_argument(
        "--condition",
        required=True,
        choices=[
            "A",
            "B",
            "C",
            "D",
        ],
    )

    # Local / synthetic mode
    parser.add_argument(
        "--task-id",
    )

    parser.add_argument(
        "--repo",
    )

    parser.add_argument(
        "--task",
    )

    parser.add_argument(
        "--verify-cmd",
        default=None,
    )

    parser.add_argument(
        "--candidates",
        default=None,
        help=(
            "JSON file containing "
            "LocalizationCandidate records."
        ),
    )

    # SWE-bench mode
    parser.add_argument(
        "--instance-id",
    )

    parser.add_argument(
        "--task-config",
    )

    parser.add_argument(
        "--model",
        default=(
            "openai/gpt-5.4-mini"
        ),
    )

    args = parser.parse_args()

    if args.benchmark == "local":

        task_id = require(
            parser,
            args.task_id,
            "--task-id",
        )

        repo = require(
            parser,
            args.repo,
            "--repo",
        )

        task = require(
            parser,
            args.task,
            "--task",
        )

        candidates = load_candidates(
            args.candidates
        )

        runner = MiniSWEWrapper(
            model_name=args.model,
        )

        result = runner.run(
            task_id=task_id,
            task=task,
            repo_path=repo,
            condition=args.condition,
            localization_candidates=(
                candidates
            ),
            verify_command=(
                args.verify_cmd
            ),
        )

    else:

        instance_id = require(
            parser,
            args.instance_id,
            "--instance-id",
        )

        task_config = require(
            parser,
            args.task_config,
            "--task-config",
        )

        runner = SWEbenchRunner(
            model_name=args.model,
        )

        result = runner.run(
            instance_id=instance_id,
            task_config=task_config,
            condition=args.condition,
        )

    print()
    print("Run completed")
    print("-------------")
    print(
        f"run_id: {result.run_id}"
    )
    print(
        f"status: {result.status}"
    )
    print(
        "termination: "
        f"{result.termination_reason}"
    )
    print(
        "trajectory: "
        f"{result.trajectory_path}"
    )
    print(
        f"patch: {result.patch_path}"
    )

    if result.error:
        print(
            f"error: {result.error}"
        )


if __name__ == "__main__":
    main()
