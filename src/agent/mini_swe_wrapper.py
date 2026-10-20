from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

import yaml
from dotenv import load_dotenv

from minisweagent import (
    __version__ as mini_version,
    global_config_dir,
    package_dir,
)
from minisweagent.agents.default import DefaultAgent
from minisweagent.environments.local import LocalEnvironment
from minisweagent.models import get_model

from src.agent.context import augment_task_with_localization
from src.agent.contracts import (
    LocalizationCandidate,
    RunResult,
    RunUsage,
)


class MiniSWEWrapper:
    """
    Role 1 integration layer around mini-SWE-agent.

    Responsibilities:
    - prepare an isolated working copy
    - run mini-SWE-agent
    - save trajectory
    - save patch
    - normalize metadata into RunResult

    It does NOT implement BM25, structural ranking,
    failure parsing, or evaluation metrics.
    """

    def __init__(
        self,
        model_name: str = "openai/gpt-5.4-mini",
        model_class: str = "openrouter",
        step_limit: int = 50,
        cost_limit: float = 0.50,
        wall_time_limit_seconds: int = 1800,
        command_timeout_seconds: int = 120,
        output_root: str | Path = "runs",
    ):
        self.model_name = model_name
        self.model_class = model_class

        self.step_limit = step_limit
        self.cost_limit = cost_limit
        self.wall_time_limit_seconds = wall_time_limit_seconds
        self.command_timeout_seconds = command_timeout_seconds

        self.output_root = Path(output_root)

        # mini-extra config set writes keys here.
        load_dotenv(global_config_dir / ".env")

    @staticmethod
    def _run_git(
        workspace: Path,
        *args: str,
        check: bool = True,
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", "-C", str(workspace), *args],
            text=True,
            capture_output=True,
            check=check,
        )

    def _prepare_workspace(
        self,
        source_repo: Path,
        workspace: Path,
    ) -> str:
        """
        Copy source repo into an isolated local workspace and create
        a local Git baseline commit.

        Returns baseline commit hash.
        """

        shutil.copytree(
            source_repo,
            workspace,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                ".pytest_cache",
                "*.pyc",
                ".git",
            ),
        )

        self._run_git(workspace, "init", "-q")
        self._run_git(
            workspace,
            "config",
            "user.email",
            "agent@example.invalid",
        )
        self._run_git(
            workspace,
            "config",
            "user.name",
            "DSA4213 Agent",
        )

        self._run_git(workspace, "add", "-A")
        self._run_git(
            workspace,
            "commit",
            "-q",
            "-m",
            "baseline",
        )

        result = self._run_git(
            workspace,
            "rev-parse",
            "HEAD",
        )

        return result.stdout.strip()

    def _build_agent(
        self,
        workspace: Path,
        trajectory_path: Path,
    ) -> DefaultAgent:
        """
        Build mini-SWE-agent using the package's own mini.yaml
        templates, while overriding experiment limits.
        """

        builtin_config = yaml.safe_load(
            (
                Path(package_dir)
                / "config"
                / "mini.yaml"
            ).read_text(encoding="utf-8")
        )

        model_config = dict(
            builtin_config.get("model", {})
        )

        model_config["model_class"] = (
            self.model_class
        )

        model = get_model(
            input_model_name=self.model_name,
            config=model_config,
        )

        environment_config = dict(
            builtin_config.get(
                "environment",
                {},
            )
        )

        environment_config.update(
            {
                "cwd": str(workspace),
                "timeout": (
                    self.command_timeout_seconds
                ),
            }
        )

        environment = LocalEnvironment(
            **environment_config
        )

        source_agent_config = (
            builtin_config["agent"]
        )

        # Only pass options supported by DefaultAgent.
        allowed_keys = {
            "system_template",
            "instance_template",
            "max_consecutive_format_errors",
        }

        agent_config = {
            key: value
            for key, value
            in source_agent_config.items()
            if key in allowed_keys
        }

        agent_config.update(
            {
                "step_limit": self.step_limit,
                "cost_limit": self.cost_limit,
                "wall_time_limit_seconds": (
                    self.wall_time_limit_seconds
                ),
                "output_path": trajectory_path,
            }
        )

        return DefaultAgent(
            model,
            environment,
            **agent_config,
        )

    def _capture_patch(
        self,
        workspace: Path,
        baseline_commit: str,
    ) -> str:
        """
        Capture modified and newly created files.
        """

        # Make untracked files visible to git diff.
        self._run_git(
            workspace,
            "add",
            "-N",
            ".",
            check=False,
        )

        result = self._run_git(
            workspace,
            "diff",
            baseline_commit,
            "--",
            ".",
            check=False,
        )

        return result.stdout

    @staticmethod
    def _load_trajectory(
        path: Path,
    ) -> dict:
        if not path.exists():
            return {}

        try:
            return json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except json.JSONDecodeError:
            return {}

    def run(
        self,
        *,
        task_id: str,
        task: str,
        repo_path: str | Path,
        condition: str = "A",
        localization_candidates: (
            list[LocalizationCandidate] | None
        ) = None,
        verify_command: str | None = None,
    ) -> RunResult:

        condition = condition.upper()

        if condition not in {
            "A",
            "B",
            "C",
            "D",
        }:
            raise ValueError(
                f"Unknown condition: {condition}"
            )

        if condition in {"B", "C"}:
            if not localization_candidates:
                raise ValueError(
                    f"Condition {condition} "
                    "requires localization candidates."
                )

        if condition == "D":
            raise NotImplementedError(
                "Condition D requires runtime "
                "failure-aware reranking and will "
                "be connected after Role 4 delivers "
                "the FailureEvent interface."
            )

        repo_path = Path(
            repo_path
        ).resolve()

        if not repo_path.exists():
            raise FileNotFoundError(
                repo_path
            )

        run_id = (
            f"{task_id}_{condition}_"
            f"{uuid.uuid4().hex[:8]}"
        )

        run_dir = (
            self.output_root
            / run_id
        ).resolve()

        workspace = (
            run_dir
            / "workspace"
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

        run_dir.mkdir(
            parents=True,
            exist_ok=False,
        )

        baseline_commit = (
            self._prepare_workspace(
                repo_path,
                workspace,
            )
        )

        effective_task = (
            augment_task_with_localization(
                task,
                localization_candidates or [],
            )
        )

        if condition == "A":
            # Important:
            # A must receive the original task only.
            effective_task = task

        agent = self._build_agent(
            workspace,
            trajectory_path,
        )

        started = time.time()

        error: str | None = None

        outcome: dict = {}

        try:
            outcome = agent.run(
                effective_task
            )
        except Exception as exc:
            error = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            outcome = {
                "exit_status":
                    type(exc).__name__,
                "submission": "",
            }

            # run() normally saves in finally,
            # but explicitly save once more
            # for robustness.
            agent.save(
                trajectory_path
            )

        runtime_seconds = (
            time.time() - started
        )

        patch = self._capture_patch(
            workspace,
            baseline_commit,
        )

        patch_path.write_text(
            patch,
            encoding="utf-8",
        )

        verification = None

        if verify_command:
            verify = subprocess.run(
                verify_command,
                cwd=workspace,
                shell=True,
                text=True,
                capture_output=True,
            )

            verification = {
                "command":
                    verify_command,
                "returncode":
                    verify.returncode,
                "stdout":
                    verify.stdout,
                "stderr":
                    verify.stderr,
            }

        trajectory = (
            self._load_trajectory(
                trajectory_path
            )
        )

        trajectory_info = (
            trajectory.get(
                "info",
                {},
            )
        )

        model_stats = (
            trajectory_info.get(
                "model_stats",
                {},
            )
        )

        exit_status = (
            outcome.get(
                "exit_status"
            )
            or trajectory_info.get(
                "exit_status"
            )
            or (
                "error"
                if error
                else "unknown"
            )
        )

        status = (
            "completed"
            if not error
            else "error"
        )

        result = RunResult(
            run_id=run_id,
            task_id=task_id,
            condition=condition,

            model=self.model_name,
            mini_swe_agent_version=(
                mini_version
            ),

            status=status,
            termination_reason=(
                str(exit_status)
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
                "model_class":
                    self.model_class,
                "step_limit":
                    self.step_limit,
                "cost_limit":
                    self.cost_limit,
                "wall_time_limit_seconds":
                    self.wall_time_limit_seconds,
                "command_timeout_seconds":
                    self.command_timeout_seconds,
            },

            evaluation=(
                {
                    "local_verification":
                        verification
                }
                if verification
                else None
            ),

            error=error,
        )

        result.save(
            result_path
        )

        return result