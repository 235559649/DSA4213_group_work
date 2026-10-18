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
    """
    Load localization candidates from a JSON file.

    Expected format:
    [
        {
            "file": "src/example.py",
            "rank": 1,
            "score": 0.9,
            "symbol": "Example",
            "symbol_type": "class",
            "reason": "BM25"
        }
    ]
    """

    if not path:
        return []

    candidate_path = Path(
        path
    ).resolve()

    if not candidate_path.exists():
        raise FileNotFoundError(
            candidate_path
        )

    data = json.loads(
        candidate_path.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        data,
        list,
    ):
        raise ValueError(
            "Candidate file must contain "
            "a JSON list."
        )

    return [
        LocalizationCandidate(
            **item
        )
        for item in data
    ]


def require(
    parser: argparse.ArgumentParser,
    value,
    option: str,
):
    """
    Require an argument only for the selected benchmark mode.
    """

    if not value:
        parser.error(
            f"{option} is required for "
            "the selected benchmark mode."
        )

    return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Unified Role 1 runner for "
            "local and SWE-bench experiments."
        )
    )

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

    # ---------------------------------------------------------
    # Local / synthetic mode
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # Shared localization input
    # ---------------------------------------------------------

    parser.add_argument(
        "--candidates",
        default=None,
        help=(
            "JSON file containing "
            "LocalizationCandidate records. "
            "Required for Conditions B/C."
        ),
    )

    # ---------------------------------------------------------
    # SWE-bench mode
    # ---------------------------------------------------------

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

    # =========================================================
    # Local benchmark
    # =========================================================

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

    # =========================================================
    # SWE-bench
    # =========================================================

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

        candidates = load_candidates(
            args.candidates
        )

        runner = SWEbenchRunner(
            model_name=args.model,
        )

        result = runner.run(
            instance_id=instance_id,
            task_config=task_config,
            condition=args.condition,
            localization_candidates=(
                candidates
            ),
        )

    # =========================================================
    # Unified summary
    # =========================================================

    print()
    print("Run completed")
    print("-------------")

    print(
        f"run_id: "
        f"{result.run_id}"
    )

    print(
        f"condition: "
        f"{result.condition}"
    )

    print(
        f"status: "
        f"{result.status}"
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
        f"patch: "
        f"{result.patch_path}"
    )

    if result.usage:
        print(
            "api_calls: "
            f"{result.usage.api_calls}"
        )

        print(
            "cost_usd: "
            f"{result.usage.cost_usd}"
        )

    if result.error:
        print(
            f"error: "
            f"{result.error}"
        )


if __name__ == "__main__":
    main()