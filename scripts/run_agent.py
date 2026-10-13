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
        LocalizationCandidate(
            **item
        )
        for item in data
    ]


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--condition",
        required=True,
        choices=["A", "B", "C", "D"],
    )

    parser.add_argument(
        "--task-id",
        required=True,
    )

    parser.add_argument(
        "--repo",
        required=True,
    )

    parser.add_argument(
        "--task",
        required=True,
    )

    parser.add_argument(
        "--model",
        default=(
            "openai/gpt-5.4-mini"
        ),
    )

    parser.add_argument(
        "--candidates",
        default=None,
        help=(
            "JSON file containing "
            "LocalizationCandidate records."
        ),
    )

    parser.add_argument(
        "--verify-cmd",
        default=None,
    )

    args = parser.parse_args()

    candidates = load_candidates(
        args.candidates
    )

    runner = MiniSWEWrapper(
        model_name=args.model,
    )

    result = runner.run(
        task_id=args.task_id,
        task=args.task,
        repo_path=args.repo,
        condition=args.condition,
        localization_candidates=candidates,
        verify_command=args.verify_cmd,
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