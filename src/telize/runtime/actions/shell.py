from __future__ import annotations

import os
import subprocess

from telize.config.models import ShellStep, Step
from telize.exceptions import ExecutionError
from telize.runtime.actions.base import ActionContext, ActionExecutor
from telize.runtime.state import StepResult


class ShellActionExecutor(ActionExecutor):
    uses = "shell"

    def execute(self, step: Step, ctx: ActionContext) -> StepResult:
        if not isinstance(step, ShellStep):
            raise ExecutionError(f"expected shell step, got {step.uses}")

        script = ctx.renderer.render(step.run)
        env = ctx.renderer.render_mapping(dict(step.envs))
        merged_env = {**os.environ, **{k: str(v) for k, v in env.items()}}

        try:
            completed = subprocess.run(
                script,
                shell=True,
                capture_output=True,
                text=True,
                cwd=ctx.base_path,
                env=merged_env,
                check=False,
            )
        except OSError as exc:
            raise ExecutionError(f"shell step '{step.name}' failed: {exc}") from exc

        if completed.returncode != 0:
            raise ExecutionError(
                f"shell step '{step.name}' exited {completed.returncode}:\n{completed.stderr}"
            )

        output = completed.stdout
        return StepResult(name=step.name, output=output)
