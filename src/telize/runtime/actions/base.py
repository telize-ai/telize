from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from telize.config.models import Step
from telize.runtime.paths import resolve_under_base
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


def apply_output_to(step: Step, result: StepResult, ctx: ActionContext) -> StepResult:
    """Write step output to disk when the step defines ``output_to``."""
    if step.output_to is None:
        return result
    output_path = resolve_under_base(ctx.base_path, ctx.renderer.render(step.output_to))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(result.output, encoding="utf-8")
    return StepResult(
        name=result.name,
        output=result.output,
        output_path=output_path,
        uses=result.uses,
        flow_name=result.flow_name,
    )
