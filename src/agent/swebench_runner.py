from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from minisweagent import (
    __version__ as mini_version,
)
from minisweagent.agents import get_agent
from minisweagent.config import (
    builtin_config_dir,
    get_config_from_spec,
)
from minisweagent.models import get_model
from minisweagent.run.benchmarks.swebench import (
    get_sb_environment,
)
from minisweagent.utils.serialize import (
    recursive_merge,
)

from src.agent.context import (
    augment_task_with_localization,
    select_prompt_candidates,
    with_repair_guidance, REPAIR_GUIDANCE_VERSION,
)
from src.agent.contracts import (
    LocalizationCandidate,
    RunResult,
    RunUsage,
)

from src.repository.swebench import build_task_index
from src.agent.failure_feedback import (
    FailureFeedbackController, RemoteSourceReader, failure_fusion_config,
    validate_failure_limits, validate_failure_weight,
)


class SWEbenchRunner:
    """
    Role 1 SWE-bench integration runner.

    Responsibilities:
    - run a frozen SWE-bench instance through mini-SWE-agent
    - use the official Docker benchmark environment
    - support controlled A/B/C/D task-context conditions
    - save trajectory, patch, task metadata, effective task,
      and localization candidates
    - normalize run metadata into RunResult

    Conditions:
    - A: original SWE-bench problem statement
    - B: original task + lexical localization context
    - C: original task + lexical/structural localization context
    - D: initial C context plus eligible runtime failure reranking
    """

    def __init__(
        self,
        model_name: str = "openai/gpt-5.4-mini",
        model_class: str = "openrouter",
        subset: str = "lite",
        split: str = "dev",
        output_root: str | Path = "runs",
        failure_max_updates: int = 3,
        failure_repo_root: str = '/testbed',
        *,
        failure_weight: float = 1.0,
        failure_max_recovery_updates: int = 2,
        failure_max_diagnostic_updates: int = 1,
    ):
        self.failure_weight = validate_failure_weight(failure_weight)
        validate_failure_limits(failure_max_updates, failure_max_recovery_updates,
                                failure_max_diagnostic_updates)
        self.failure_max_recovery_updates = failure_max_recovery_updates
        self.failure_max_diagnostic_updates = failure_max_diagnostic_updates
        self.model_name = model_name
        self.model_class = model_class
        self.subset = subset
        self.split = split
        self.output_root = Path(output_root)
        self.failure_max_updates = failure_max_updates
        self.failure_repo_root = failure_repo_root


    def _build_repository_index_metadata(
        self,
        instance_id: str,
    ) -> dict:
        index = build_task_index(instance_id)

        return {
            "instance_id": instance_id,
            "repo": index.metadata.get("repo"),
            "base_commit": index.metadata.get("commit"),
            "index_sha256": index.metadata.get(
                "index_sha256"
            ),
            "file_count": len(index.files),
            "record_count": len(index.records),
            "error_count": len(index.errors),
        }

    @staticmethod
    def _load_json(
        path: Path,
    ) -> dict[str, Any]:
        return json.loads(
            path.read_text(
                encoding="utf-8",
            )
        )

    @staticmethod
    def build_effective_task(
        *,
        task: str,
        condition: str,
        localization_candidates: (
            list[LocalizationCandidate] | None
        ) = None,
    ) -> str:
        """
        Build the task actually shown to the agent.

        Condition A receives the original task only.
        Conditions B/C receive the original task plus
        localization guidance.
        """

        condition = condition.upper()

        candidates = (
            localization_candidates
            or []
        )

        if condition == "A":
            return task

        if condition in {"B", "C"}:
            if not candidates:
                raise ValueError(
                    f"Condition {condition} requires "
                    "localization candidates."
                )

            return augment_task_with_localization(
                task,
                candidates,
            )

        if condition == "D":
            # Real initial C context is built from task sources after env setup.
            return augment_task_with_localization(task, candidates)

        raise ValueError(
            f"Unknown condition: {condition}"
        )

    @staticmethod
    def _walk_strings(
        value: Any,
    ):
        """
        Recursively yield strings from trajectory objects.
        """

        if isinstance(value, str):
            yield value

        elif isinstance(value, dict):
            for item in value.values():
                yield from (
                    SWEbenchRunner._walk_strings(
                        item
                    )
                )

        elif isinstance(value, list):
            for item in value:
                yield from (
                    SWEbenchRunner._walk_strings(
                        item
                    )
                )

    @staticmethod
    def _extract_diff(
        text: str,
    ) -> str:
        """
        Extract a git-style unified diff from a block of text.
        """

        marker = "diff --git "

        if marker not in text:
            return ""

        patch = text[
            text.find(marker):
        ]

        # Tool observations may end with XML-like wrappers.
        for end_marker in [
            "</output>",
            "</output_tail>",
        ]:
            if end_marker in patch:
                patch = patch.split(
                    end_marker,
                    1,
                )[0]

        return patch.strip()

    @classmethod
    def extract_patch(
        cls,
        trajectory: dict[str, Any],
    ) -> str:
        """
        Prefer the official submission field.

        If the agent produced a patch but failed to terminate
        cleanly, recover the most recent git diff from the
        trajectory messages.
        """

        info = trajectory.get(
            "info",
            {},
        )

        submission = info.get(
            "submission",
            "",
        )

        if isinstance(
            submission,
            str,
        ):
            patch = cls._extract_diff(
                submission
            )

            if patch:
                return patch

        candidates: list[str] = []

        for text in cls._walk_strings(
            trajectory.get(
                "messages",
                [],
            )
        ):
            patch = cls._extract_diff(
                text
            )

            if patch:
                candidates.append(
                    patch
                )

        if not candidates:
            return ""

        # The latest diff is normally the final patch.
        return candidates[-1]

    def _build_agent(
        self,
        *,
        instance_id: str,
        trajectory_path: Path,
    ):
        """
        Build mini-SWE-agent directly through its Python API.

        This mirrors swebench-single, but allows Role 1 to control
        the task text passed into agent.run().
        """

        default_config = (
            builtin_config_dir
            / "benchmarks"
            / "swebench.yaml"
        )

        base_config = (
            get_config_from_spec(
                str(default_config)
            )
        )

        override = {
            "agent": {
                "mode": "yolo",
                "confirm_exit": False,
                "output_path":
                    trajectory_path,
            },
            "model": {
                "model_name":
                    self.model_name,
                "model_class":
                    self.model_class,
            },
            "environment": {
                "environment_class":
                    "docker",
            },
        }

        config = recursive_merge(
            base_config,
            override,
        )
        config['agent']['system_template'] = with_repair_guidance(
            config['agent'].get('system_template', ''))

        # mini-SWE-agent derives the official SWE-bench
        # Docker image from the instance ID.
        instance = {
            "instance_id":
                instance_id,
        }

        environment = (
            get_sb_environment(
                config,
                instance,
            )
        )

        model = get_model(
            config=config.get(
                "model",
                {},
            )
        )

        agent = get_agent(
            model,
            environment,
            config.get(
                "agent",
                {},
            ),
            default_type="interactive",
        )

        return agent, environment

    def run(
        self,
        *,
        instance_id: str,
        task_config: str | Path,
        condition: str = "A",
        localization_candidates: (
            list[LocalizationCandidate] | None
        ) = None,
        localization_top_k: int | None = None,
    ) -> RunResult:
        """
        Execute one SWE-bench instance.

        The only intended experimental difference between
        Conditions A/B/C is the task context supplied to the agent.
        """

        condition = condition.upper()

        task_config = Path(
            task_config
        ).resolve()

        if not task_config.exists():
            raise FileNotFoundError(
                task_config
            )

        metadata = self._load_json(
            task_config
        )

        configured_instance = (
            metadata.get(
                "instance_id"
            )
        )

        if (
            configured_instance
            != instance_id
        ):
            raise ValueError(
                "Instance mismatch: "
                f"CLI requested "
                f"{instance_id!r}, "
                "but task config contains "
                f"{configured_instance!r}."
            )

        original_task = (
            metadata.get(
                "problem_statement"
            )
        )

        repository_index_metadata = (
            self._build_repository_index_metadata(
                instance_id
            )
        )

        if not original_task:
            raise ValueError(
                "task config does not "
                "contain problem_statement"
            )

        full_candidates = list(
            localization_candidates
            or []
        )

        if condition == "A":
            prompt_candidates = []

        else:
            prompt_candidates = (
                select_prompt_candidates(
                    full_candidates,
                    localization_top_k,
                )
            )

        effective_task = (
            self.build_effective_task(
                task=original_task,
                condition=condition,
                localization_candidates=(
                    prompt_candidates
                ),
            )
        )

        run_id = (
            f"{instance_id}_"
            f"{condition}_"
            f"{uuid.uuid4().hex[:8]}"
        )

        run_dir = (
            self.output_root
            / run_id
        ).resolve()

        run_dir.mkdir(
            parents=True,
            exist_ok=False,
        )

        trajectory_path = (
            run_dir
            / "trajectory.json"
        )

        patch_path = (
            run_dir
            / "patch.diff"
        )

        result_path = (
            run_dir
            / "run_result.json"
        )

        task_metadata_path = (
            run_dir
            / "task_metadata.json"
        )

        effective_task_path = (
            run_dir
            / "effective_task.txt"
        )

        candidates_path = (
            run_dir
            / "localization_candidates.json"
        )

        prompt_candidates_path = (
            run_dir
            / "prompt_candidates.json"
        )

        # Save the frozen task metadata.
        task_metadata_path.write_text(
            json.dumps(
                metadata,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        # Save exactly what is passed to the agent.
        effective_task_path.write_text(
            effective_task,
            encoding="utf-8",
        )

        # Save the localization input separately for reproducibility.
        candidate_records = [
            {
                "file":
                    candidate.file,
                "rank":
                    candidate.rank,
                "score":
                    candidate.score,
                "symbol":
                    candidate.symbol,
                "symbol_type":
                    candidate.symbol_type,
                "reason":
                    candidate.reason,
            }
            for candidate in full_candidates
        ]

        candidates_path.write_text(
            json.dumps(
                candidate_records,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        prompt_candidate_records = [
            {
                "file":
                    candidate.file,
                "rank":
                    candidate.rank,
                "score":
                    candidate.score,
                "symbol":
                    candidate.symbol,
                "symbol_type":
                    candidate.symbol_type,
                "reason":
                    candidate.reason,
            }
            for candidate in prompt_candidates
        ]

        prompt_candidates_path.write_text(
            json.dumps(
                prompt_candidate_records,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        print()
        print(
            f"SWE-bench Condition "
            f"{condition}"
        )
        print(
            "---------------------"
        )
        print(
            f"instance: "
            f"{instance_id}"
        )
        print(
            f"run_dir: "
            f"{run_dir}"
        )
        print(
            "full localization ranking: "
            f"{len(candidate_records)}"
        )

        print(
            "prompt localization candidates: "
            f"{len(prompt_candidate_records)}"
        )

        print(
            "localization top_k: "
            f"{localization_top_k}"
        )

        print()

        started = time.time()

        error: str | None = None
        outcome: dict[str, Any] = {}

        agent = None
        environment = None
        feedback = None

        # Phases of runtime_seconds, so the agent's own time can be
        # separated from container start-up and shutdown. For D, the
        # failure updates happen inside agent.run(), so agent_seconds
        # includes failure_feedback.feedback_total_seconds; the initial
        # ranking runs between set-up and agent.run() (see
        # docs/evaluation/timing.md). None means the phase did not run.
        timing: dict[str, float | None] = {
            "env_setup_seconds": None,
            "agent_seconds": None,
            "env_teardown_seconds": None,
        }

        try:
            phase_started = time.perf_counter()
            try:
                agent, environment = (
                    self._build_agent(
                        instance_id=instance_id,
                        trajectory_path=(
                            trajectory_path
                        ),
                    )
                )
            finally:
                # Recorded even when start-up fails, e.g. a Docker timeout.
                timing["env_setup_seconds"] = round(
                    time.perf_counter() - phase_started, 3
                )

            if condition == 'D':
                feedback = FailureFeedbackController(agent,
                    RemoteSourceReader(environment.execute, self.failure_repo_root), original_task,
                    run_dir / 'failure_feedback', self.failure_max_updates, localization_top_k,
                    failure_weight=self.failure_weight,
                    max_recovery_updates=self.failure_max_recovery_updates,
                    max_diagnostic_updates=self.failure_max_diagnostic_updates)
                full_candidates = feedback.initial_full_candidates()
                prompt_candidates = select_prompt_candidates(full_candidates, localization_top_k)
                candidate_records = [dict(file=c.file, rank=c.rank, score=c.score,
                    symbol=c.symbol, symbol_type=c.symbol_type, reason=c.reason) for c in full_candidates]
                prompt_candidate_records = [dict(file=c.file, rank=c.rank, score=c.score,
                    symbol=c.symbol, symbol_type=c.symbol_type, reason=c.reason) for c in prompt_candidates]
                effective_task = augment_task_with_localization(original_task, prompt_candidates)
                effective_task_path.write_text(effective_task, encoding='utf-8')
                candidates_path.write_text(json.dumps(candidate_records, ensure_ascii=False, indent=2), encoding='utf-8')
                prompt_candidates_path.write_text(json.dumps(prompt_candidate_records, ensure_ascii=False, indent=2), encoding='utf-8')
            phase_started = time.perf_counter()
            try:
                outcome = agent.run(
                    effective_task
                )
            finally:
                timing["agent_seconds"] = round(
                    time.perf_counter() - phase_started, 3
                )

        except Exception as exc:
            error = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            outcome = {
                "exit_status":
                    type(exc).__name__,
                "submission":
                    "",
            }

            # DefaultAgent normally saves its trajectory
            # in finally. Save again when possible so that
            # partial runs are not lost.
            if agent is not None:
                try:
                    agent.save(
                        trajectory_path
                    )
                except Exception:
                    pass

        finally:
            phase_started = time.perf_counter()
            if feedback is not None:
                feedback.close()
            if environment is not None:
                cleanup = getattr(
                    environment,
                    "cleanup",
                    None,
                )

                if callable(cleanup):
                    cleanup()
            timing["env_teardown_seconds"] = round(
                time.perf_counter() - phase_started, 3
            )

        runtime_seconds = (
            time.time()
            - started
        )

        trajectory: dict[str, Any] = {}

        if trajectory_path.exists():
            try:
                trajectory = (
                    self._load_json(
                        trajectory_path
                    )
                )

            except json.JSONDecodeError:
                trajectory = {}

        info = trajectory.get(
            "info",
            {},
        )

        model_stats = info.get(
            "model_stats",
            {},
        )

        exit_status = str(
            outcome.get(
                "exit_status"
            )
            or info.get(
                "exit_status"
            )
            or (
                "error"
                if error
                else "unknown"
            )
        )

        submission = (
            outcome.get(
                "submission"
            )
            or info.get(
                "submission",
                "",
            )
        )

        submission_present = bool(
            isinstance(
                submission,
                str,
            )
            and submission.strip()
        )

        patch = self.extract_patch(
            trajectory
        )

        # If the trajectory is unavailable but the agent returned
        # a valid submission, try to recover the diff directly.
        if (
            not patch
            and isinstance(
                submission,
                str,
            )
        ):
            patch = self._extract_diff(
                submission
            )

        patch_path.write_text(
            patch,
            encoding="utf-8",
        )

        patch_generated = bool(
            patch.strip()
        )

        if submission_present:
            status = "completed"

        elif patch_generated:
            status = "partial"

        else:
            status = "error"

        if (
            error is None
            and not submission_present
        ):
            error = (
                "Agent did not record an "
                "official submission. "
                f"exit_status={exit_status}"
            )

        agent_config = (
            info.get(
                "config",
                {},
            ).get(
                "agent",
                {},
            )
        )

        environment_config = (
            info.get(
                "config",
                {},
            ).get(
                "environment",
                {},
            )
        )

        result = RunResult(
            run_id=run_id,
            task_id=instance_id,
            condition=condition,

            model=self.model_name,

            mini_swe_agent_version=(
                mini_version
            ),

            status=status,

            termination_reason=(
                exit_status
            ),

            trajectory_path=str(
                trajectory_path
            ),

            patch_path=str(
                patch_path
            ),

            runtime_seconds=(
                runtime_seconds
            ),

            usage=RunUsage(
                api_calls=(
                    model_stats.get(
                        "api_calls"
                    )
                ),
                cost_usd=(
                    model_stats.get(
                        "instance_cost"
                    )
                ),
            ),

            config={
                **failure_fusion_config(self.failure_weight,
                    max_updates=self.failure_max_updates,
                    max_recovery_updates=self.failure_max_recovery_updates,
                    max_diagnostic_updates=self.failure_max_diagnostic_updates),
                "repair_guidance_version": REPAIR_GUIDANCE_VERSION,
                "benchmark":
                    metadata.get(
                        "benchmark"
                    ),

                "split":
                    metadata.get(
                        "split"
                    ),

                "instance_id":
                    instance_id,

                "repo":
                    metadata.get(
                        "repo"
                    ),

                "version":
                    metadata.get(
                        "version"
                    ),

                "base_commit":
                    metadata.get(
                        "base_commit"
                    ),

                "model_class":
                    self.model_class,

                "repository_index":
                    repository_index_metadata,

                "localization_source":
                    {
                        "A": None,
                        "B": "bm25",
                        "C": "rrf_l_s",
                        "D": "rrf_l_s_f",
                    }.get(condition),
                "localization_candidate_count":
                    len(
                        candidate_records
                    ),

                "localization_full_ranking_size":
                    len(
                        candidate_records
                    ),

                "localization_top_k":
                    localization_top_k,

                "localization_prompt_candidate_count":
                    len(
                        prompt_candidate_records
                    ),

                "effective_task_path":
                    str(
                        effective_task_path
                    ),

                "localization_candidates_path":
                    str(
                        candidates_path
                    ),

                "prompt_candidates_path":
                    str(
                        prompt_candidates_path
                    ),

                "step_limit":
                    agent_config.get(
                        "step_limit"
                    ),

                "cost_limit":
                    agent_config.get(
                        "cost_limit"
                    ),

                "wall_time_limit_seconds":
                    agent_config.get(
                        "wall_time_limit_seconds"
                    ),

                "command_timeout_seconds":
                    environment_config.get(
                        "timeout"
                    ),

                "docker_image":
                    environment_config.get(
                        "image"
                    ),

                "localization_candidate_count":
                    len(
                        candidate_records
                    ),

                "effective_task_path":
                    str(
                        effective_task_path
                    ),

                "localization_candidates_path":
                    str(
                        candidates_path
                    ),
            },
            evaluation={
                "agent_run_completed":
                    error is None,

                "submission_present":
                    submission_present,

                "patch_generated":
                    patch_generated,

                "official_swebench_evaluation":
                    None,
            },

            error=error,
        )

        result.config["timing"] = timing
        if feedback is not None:
            result.config['failure_feedback'] = feedback.summary()
        result.save(
            result_path
        )

        print()
        print(
            "SWE-bench run recorded"
        )
        print(
            "----------------------"
        )
        print(
            f"condition: {condition}"
        )
        print(
            f"status: {status}"
        )
        print(
            "termination: "
            f"{exit_status}"
        )
        print(
            "patch_generated: "
            f"{patch_generated}"
        )
        print(
            "submission_present: "
            f"{submission_present}"
        )
        print(
            "api_calls: "
            f"{model_stats.get('api_calls')}"
        )
        print(
            "cost_usd: "
            f"{model_stats.get('instance_cost')}"
        )
        print(
            f"run_result: "
            f"{result_path}"
        )

        return result
