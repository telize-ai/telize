from __future__ import annotations

import importlib
from typing import Any

from telize.config.models import PythonStep, Step
from telize.exceptions import ExecutionError
from telize.runtime.actions.base import ActionContext, ActionExecutor
from telize.runtime.state import StepResult


class PythonActionExecutor(ActionExecutor):
    uses = "python"

    def execute(self, step: Step, ctx: ActionContext) -> StepResult:
        if not isinstance(step, PythonStep):
            raise ExecutionError(f"expected python step, got {step.uses}")

        args = ctx.renderer.render_mapping(dict(step.args))
        callable_obj = _import_callable(step.call)
        try:
            result = callable_obj(**args)
        except Exception as exc:
            raise ExecutionError(f"python step '{step.name}' failed: {exc}") from exc

        output = str(result)
        return StepResult(name=step.name, output=output)


def _import_callable(path: str) -> Any:
    parts = path.rsplit(".", 1)
    if len(parts) != 2:
        msg = f"invalid python call path '{path}'; expected 'module.function'"
        raise ExecutionError(msg)
    module_name, attr = parts
    try:
        module = importlib.import_module(module_name)
        return getattr(module, attr)
    except (ImportError, AttributeError) as exc:
        raise ExecutionError(f"cannot import '{path}': {exc}") from exc
