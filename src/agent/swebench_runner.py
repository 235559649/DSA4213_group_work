from __future__ import annotations

import json
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any

from minisweagent import __version__ as mini_version

from src.agent.contracts import RunResult, RunUsage


class SWEbenchRunner:
    """
    Role 1 SWE-bench integration runner.

    Phase 2 responsibilities:
    - run a frozen SWE-bench instance through mini-swe-agent
    - use the official Docker benchmark environment
    - save trajectory, patch, task metadata and runner log
    - normalize run metadata into RunResult

    Phase 2 currently implements Condition A only.
    Conditions B/C/D will be connected after the localization
    modules are integrated.
    """

    def __init__(
        self,
        model_name: str = "openai/gpt-5.4-mini",
        model_class: str = "openrouter",
        subset: str = "lite",
        split: str = "dev",
        output_root: str | Path = "runs",
    ):
        self.model_name = model_name
        self.model_class = model_class
        self.subset = subset
        self.split = split
        self.output_root = Path(output_root)

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        return json.loads(
            path.read_text(encoding="utf-8")
        )

    @staticmethod
    def _walk_strings(value: Any):
        """
        Recursively yield strings from trajectory objects.
        """

        if isinstance(value, str):
            yield value

        elif isinstance(value, dict):
            for item in value.values():
                yield from SWEbenchRunner._walk_strings(item)

        elif isinstance(value, list):
            for item in value:
                yield from SWEbenchRunner._walk_strings(item)

    @staticmethod
    def _extract_diff(text: str) -> str:
        """
        Extract a git-style unified diff from a block of text.
        """

        marker = "diff --git "

        if marker not in text:
            return ""

        patch = text[text.find(marker):]

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

        If the agent produced a patch but failed to terminate cleanly
        (e.g. RepeatedFormatError), recover the most recent git diff
        from the trajectory messages.
        """

        info = trajectory.get("info", {})

        submission = info.get(
            "submission",
            "",
        )

        if isinstance(submission, str):
            patch = cls._extract_diff(
                submission
            )

            if patch:
                return patch

        candidates: list[str] = []

        for text in cls._walk_strings(
            trajectory.get("messages", [])
        ):
            patch = cls._extract_diff(text)

            if patch:
                candidates.append(patch)

        if not candidates:
            return ""

        # Later observations generally correspond to the final patch.
        return candidates[-1]

    def _build_command(
        self,
        *,
        instance_id: str,
        trajectory_path: Path,
    ) -> list[str]:

        executable = shutil.which(
            "mini-extra"
        )

        if executable is None:
            raise RuntimeError(
                "mini-extra was not found. "
                "Activate the project virtual environment first."
            )

        return [
            executable,
            "swebench-single",

            "--subset",
            self.subset,

            "--split",
            self.split,

            "-i",
            instance_id,

            "-m",
            self.model_name,

            "--model-class",
            self.model_class,

            "--environment-class",
            "docker",

            "-y",

            "--exit-immediately",

            "-o",
            str(trajectory_path),
        ]

    @staticmethod
    def _run_and_stream(
        command: list[str],
        log_path: Path,
    ) -> int:
        """
        Stream mini-swe-agent output to both terminal and runner.log.
        """

        with log_path.open(
            "w",
            encoding="utf-8",
        ) as log_file:

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            assert process.stdout is not None

            for line in process.stdout:
                print(
                    line,
                    end="",
                    flush=True,
                )

                log_file.write(line)
                log_file.flush()

            return process.wait()

    def run(
        self,
        *,
        instance_id: str,
        task_config: str | Path,
        condition: str = "A",
    ) -> RunResult:

        condition = condition.upper()

        if condition != "A":
            raise NotImplementedError(
                "SWE-bench Phase 2 currently supports "
                "Condition A only. B/C/D will be integrated "
                "after the localization interfaces are connected."
            )

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

        configured_instance = metadata.get(
            "instance_id"
        )

        if configured_instance != instance_id:
            raise ValueError(
                "Instance mismatch: "
                f"CLI requested {instance_id!r}, "
                f"but task config contains "
                f"{configured_instance!r}."
            )

        run_id = (
            f"{instance_id}_{condition}_"
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

        runner_log_path = (
            run_dir
            / "runner.log"
        )

        task_metadata_path.write_text(
            json.dumps(
                metadata,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        command = self._build_command(
            instance_id=instance_id,
            trajectory_path=trajectory_path,
        )

        print()
        print("SWE-bench Condition A")
        print("---------------------")
        print(
            f"instance: {instance_id}"
        )
        print(
            f"run_dir: {run_dir}"
        )
        print()

        started = time.time()

        cli_returncode = (
            self._run_and_stream(
                command,
                runner_log_path,
            )
        )

        runtime_seconds = (
            time.time() - started
        )

        trajectory: dict[str, Any] = {}

        if trajectory_path.exists():
            try:
                trajectory = self._load_json(
                    trajectory_path
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
            info.get(
                "exit_status",
                f"cli_returncode_{cli_returncode}",
            )
        )

        submission = info.get(
            "submission",
            "",
        )

        submission_present = bool(
            isinstance(submission, str)
            and submission.strip()
        )

        patch = self.extract_patch(
            trajectory
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

        error: str | None = None

        if cli_returncode != 0:
            error = (
                "mini-extra exited with return code "
                f"{cli_returncode}"
            )

        elif not submission_present:
            error = (
                "Agent did not record an official submission. "
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

                "base_commit":
                    metadata.get(
                        "base_commit"
                    ),

                "model_class":
                    self.model_class,

                "step_limit":
                    agent_config.get(
                        "step_limit"
                    ),

                "cost_limit":
                    agent_config.get(
                        "cost_limit"
                    ),

                "command_timeout_seconds":
                    environment_config.get(
                        "timeout"
                    ),

                "docker_image":
                    environment_config.get(
                        "image"
                    ),
            },

            evaluation={
                "cli_returncode":
                    cli_returncode,

                "submission_present":
                    submission_present,

                "patch_generated":
                    patch_generated,

                "official_swebench_evaluation":
                    None,
            },

            error=error,
        )

        result.save(
            result_path
        )

        print()
        print("SWE-bench run recorded")
        print("----------------------")
        print(f"status: {status}")
        print(
            f"termination: {exit_status}"
        )
        print(
            f"patch_generated: {patch_generated}"
        )
        print(
            f"submission_present: {submission_present}"
        )
        print(
            f"run_result: {result_path}"
        )

        return result
