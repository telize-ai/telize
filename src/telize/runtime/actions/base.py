from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from telize.config.models import Step
from telize.runtime.state import ExecutionState, StepResult
from telize.templating.renderer import TemplateRenderer


@dataclass(frozen=True)
class ActionContext:
    """Dependencies passed to every action executor."""

    state: ExecutionState
    renderer: TemplateRenderer
    base_path: Path
    run_flow: Callable[[str], str] | None = None
    run_workflow_file: Callable[[Path, Mapping[str, Any] | None], str] | None = None


class ActionExecutor(Protocol):
    """Execute a single typed step and return its output."""

    uses: str

    def execute(self, step: Step, ctx: ActionContext) -> StepResult: ...
