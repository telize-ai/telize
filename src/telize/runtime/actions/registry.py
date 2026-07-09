from __future__ import annotations

from telize.config.models import Step
from telize.exceptions import ExecutionError
from telize.runtime.actions.base import ActionContext, ActionExecutor
from telize.runtime.actions.chat import ChatActionExecutor
from telize.runtime.actions.input import InputActionExecutor
from telize.runtime.actions.llm import LlmActionExecutor
from telize.runtime.actions.python import PythonActionExecutor
from telize.runtime.actions.shell import ShellActionExecutor
from telize.runtime.actions.text_search import TextSearchActionExecutor
from telize.runtime.actions.yaml import YamlActionExecutor
from telize.runtime.state import StepResult


class ActionRegistry:
    """Maps `uses` values to executor implementations."""

    def __init__(self) -> None:
        self._executors: dict[str, ActionExecutor] = {}

    def register(self, executor: ActionExecutor) -> None:
        self._executors[executor.uses] = executor

    def execute(self, step: Step, ctx: ActionContext) -> StepResult:
        executor = self._executors.get(step.uses)
        if executor is None:
            raise ExecutionError(f"No executor registered for action type '{step.uses}'")
        return executor.execute(step, ctx)


def default_registry() -> ActionRegistry:
    registry = ActionRegistry()
    for executor in (
        InputActionExecutor(),
        ChatActionExecutor(),
        LlmActionExecutor(),
        ShellActionExecutor(),
        PythonActionExecutor(),
        TextSearchActionExecutor(),
        YamlActionExecutor(),
    ):
        registry.register(executor)
    return registry
