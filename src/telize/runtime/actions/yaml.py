from __future__ import annotations

from telize.config.models import Step, YamlStep
from telize.exceptions import ExecutionError
from telize.runtime.actions.base import ActionContext, ActionExecutor
from telize.runtime.paths import resolve_under_base
from telize.runtime.state import StepResult


class YamlActionExecutor(ActionExecutor):
    uses = "yaml"

    def execute(self, step: Step, ctx: ActionContext) -> StepResult:
        if not isinstance(step, YamlStep):
            raise ExecutionError(f"expected yaml step, got {step.uses}")

        if ctx.run_workflow_file is None:
            raise ExecutionError("nested workflow execution is not available")

        file_path = resolve_under_base(ctx.base_path, ctx.renderer.render(step.file))
        child_input = ctx.renderer.render_mapping(dict(step.input))
        output = ctx.run_workflow_file(file_path, child_input)
        return StepResult(name=step.name, output=output)
