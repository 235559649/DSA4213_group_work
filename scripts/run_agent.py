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

from src.agent.context import (  # noqa: E402
    select_prompt_candidates,
)


def load_candidates(
    path: str | None,
    *,
    instance_id: str | None = None,
) -> list[LocalizationCandidate]:
    """
    Load localization candidates from JSON.

    Supported formats:

    1. Role 1 canonical format:
       {
           "file": "...",
           "rank": 1,
           "score": 0.9
       }

    2. Role 3 BM25 format:
       {
           "path": "...",
           "rank": 1,
           "bm25_score": 12.3
       }

    3. Role 3 RRF format:
       {
           "file": "...",
           "rank": 1,
           "rrf_score": 0.03
       }

    The file may contain either a flat ranking list or
    Role 3's batch format:

       [
           {
               "instance_id": "...",
               "ranked_files": [...]
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

    # ---------------------------------------------------------
    # Role 3 batch output
    # ---------------------------------------------------------

    if (
        data
        and isinstance(data[0], dict)
        and "instance_id" in data[0]
        and "ranked_files" in data[0]
    ):
        if not instance_id:
            raise ValueError(
                "instance_id is required when "
                "loading a batch ranking file."
            )

        matching = [
            item
            for item in data
            if item.get("instance_id")
            == instance_id
        ]

        if not matching:
            raise ValueError(
                "No ranking found for "
                f"instance_id={instance_id!r}."
            )

        if len(matching) > 1:
            raise ValueError(
                "Multiple rankings found for "
                f"instance_id={instance_id!r}."
            )

        data = matching[0].get(
            "ranked_files",
            [],
        )

    # ---------------------------------------------------------
    # Normalize external schemas into Role 1's contract
    # ---------------------------------------------------------

    candidates: list[
        LocalizationCandidate
    ] = []

    for item in data:
        if not isinstance(
            item,
            dict,
        ):
            raise ValueError(
                "Each localization candidate "
                "must be a JSON object."
            )

        rank = item.get(
            "rank"
        )

        if rank is None:
            raise ValueError(
                "Localization candidate "
                "is missing rank."
            )

        # Role 1 canonical format.
        if (
            "file" in item
            and "score" in item
        ):
            candidate = (
                LocalizationCandidate(
                    file=item["file"],
                    rank=rank,
                    score=item["score"],
                    symbol=item.get(
                        "symbol"
                    ),
                    symbol_type=item.get(
                        "symbol_type"
                    ),
                    reason=item.get(
                        "reason",
                        "",
                    ),
                )
            )

        # Role 3 BM25 output.
        elif (
            "path" in item
            and "bm25_score" in item
        ):
            candidate = (
                LocalizationCandidate(
                    file=item["path"],
                    rank=rank,
                    score=item[
                        "bm25_score"
                    ],
                    symbol=None,
                    symbol_type=None,
                    reason="BM25",
                )
            )

        # Role 3 RRF output.
        elif (
            "file" in item
            and "rrf_score" in item
        ):
            candidate = (
                LocalizationCandidate(
                    file=item["file"],
                    rank=rank,
                    score=item[
                        "rrf_score"
                    ],
                    symbol=None,
                    symbol_type=None,
                    reason="RRF",
                )
            )

        else:
            raise ValueError(
                "Unsupported localization "
                "candidate schema."
            )

        candidates.append(
            candidate
        )

    return sorted(
        candidates,
        key=lambda candidate: (
            candidate.rank,
            candidate.file,
        ),
    )


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
    parser.add_argument(
        "--localization-top-k",
        type=int,
        default=None,
        help=(
            "Number of ranked localization "
            "candidates exposed to the model. "
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

    if (
        args.condition in {"B", "C"}
        and not args.candidates
    ):
        parser.error(
            "--candidates is required "
            "for Conditions B/C."
        )

    if (
        args.condition in {"B", "C"}
        and args.localization_top_k is None
    ):
        parser.error(
            "--localization-top-k is required "
            "for Conditions B/C."
        )

    if (
        args.localization_top_k is not None
        and args.localization_top_k <= 0
    ):
        parser.error(
            "--localization-top-k must be "
            "a positive integer."
        )

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
            args.candidates,
        )

        prompt_candidates = (
            select_prompt_candidates(
                candidates,
                args.localization_top_k,
            )
            if args.condition in {"B", "C"}
            else []
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
                prompt_candidates
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
            args.candidates,
            instance_id=instance_id,
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
            localization_top_k=(
                args.localization_top_k
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