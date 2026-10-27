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

from src.agent.context import augment_task_with_localization, select_prompt_candidates
from src.agent.context import REPAIR_GUIDANCE_VERSION
from src.agent.failure_feedback import (
    FailureFeedbackController, LocalSourceReader, failure_fusion_config,
    validate_failure_limits, validate_failure_weight,
)
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
        failure_max_updates: int = 3,
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

        self.step_limit = step_limit
        self.cost_limit = cost_limit
        self.wall_time_limit_seconds = wall_time_limit_seconds
        self.command_timeout_seconds = command_timeout_seconds

        self.output_root = Path(output_root)
        self.failure_max_updates = failure_max_updates

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
        localization_top_k: int | None = None,
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

        full_candidates = list(localization_candidates or [])
        prompt_candidates = select_prompt_candidates(full_candidates, localization_top_k) if condition in {'B', 'C'} else []
        effective_task = (
            augment_task_with_localization(
                task,
                prompt_candidates,
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
        feedback = None

        def save_localization_inputs():
            for filename, selected in [('localization_candidates.json', full_candidates),
                                       ('prompt_candidates.json', prompt_candidates)]:
                records = [dict(file=c.file, rank=c.rank, score=c.score, symbol=c.symbol,
                                symbol_type=c.symbol_type, reason=c.reason) for c in selected]
                (run_dir / filename).write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
            (run_dir / 'effective_task.txt').write_text(effective_task, encoding='utf-8')

        save_localization_inputs()

        started = time.time()

        error: str | None = None

        outcome: dict = {}

        try:
            if condition == 'D':
                feedback = FailureFeedbackController(agent, LocalSourceReader(workspace), task,
                    run_dir / 'failure_feedback', self.failure_max_updates, localization_top_k,
                    failure_weight=self.failure_weight,
                    max_recovery_updates=self.failure_max_recovery_updates,
                    max_diagnostic_updates=self.failure_max_diagnostic_updates)
                full_candidates = feedback.initial_full_candidates()
                prompt_candidates = feedback.initial_candidates()
                effective_task = augment_task_with_localization(task, prompt_candidates)
                save_localization_inputs()
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

        finally:
            if feedback is not None:
                feedback.close()

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
                **failure_fusion_config(self.failure_weight,
                    max_updates=self.failure_max_updates,
                    max_recovery_updates=self.failure_max_recovery_updates,
                    max_diagnostic_updates=self.failure_max_diagnostic_updates),
                "repair_guidance_version": REPAIR_GUIDANCE_VERSION,
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

        result.config.update(localization_top_k=localization_top_k,
            localization_full_ranking_size=len(full_candidates),
            localization_prompt_candidate_count=len(prompt_candidates),
            localization_candidates_path=str(run_dir / 'localization_candidates.json'),
            prompt_candidates_path=str(run_dir / 'prompt_candidates.json'),
            effective_task_path=str(run_dir / 'effective_task.txt'))
        if feedback is not None:
            result.config['failure_feedback'] = feedback.summary()
        result.save(
            result_path
        )

        return result
