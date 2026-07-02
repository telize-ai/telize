from __future__ import annotations

import time
from pathlib import Path

from rich.rule import Rule
from rich.status import Status

from telize.config.models import Step, WorkflowSpec
from telize.console.display import print_step_panel, print_workflow_header
from telize.console.terminal import get_console
from telize.runtime.state import StepResult


class RichConsoleObserver:
    """Print workflow progress to the terminal as each step finishes."""

    def __init__(self, spec: WorkflowSpec, spec_path: Path) -> None:
        self._spec = spec
        self._spec_path = spec_path
        self._console = get_console()
        self._started = 0.0
        self._estimated = 1
        self._completed = 0
        self._step_indices: dict[str, int] = {}
        self._status: Status | None = None
        self._active_step: Step | None = None
        self._active_index: int = 0

    def on_workflow_start(self, entrypoint: str, *, estimated_steps: int) -> None:
        self._estimated = max(estimated_steps, 1)
        self._started = time.monotonic()
        print_workflow_header(
            self._spec_path,
            entrypoint,
            tuple(sorted(self._spec.models)),
            estimated_steps=estimated_steps,
        )

    def on_flow_start(self, flow_name: str) -> None:
        self._console.print(f"[dim]flow[/] [bold cyan]{flow_name}[/]")

    def on_flow_complete(self, flow_name: str) -> None:
        self._console.print(f"[dim]flow[/] [green]{flow_name}[/] [dim]done[/]")

    def on_step_start(self, flow_name: str, step: Step, *, index: int) -> None:
        self._step_indices[f"{flow_name}:{step.name}"] = index
        self._active_step = step
        self._active_index = index
        if self._status is not None:
            self._status.stop()
        if step.uses == "chat":
            self._status = None
            return
        self._status = Status(
            self._step_status_text(step, index),
            console=self._console,
            spinner="dots",
        )
        self._status.start()

    def on_step_loop_progress(
        self, flow_name: str, step: Step, *, current: int, total: int
    ) -> None:
        if self._status is None:
            return
        index = self._step_indices.get(f"{flow_name}:{step.name}", self._active_index)
        self._status.update(self._step_status_text(step, index, current=current, total=total))

    def on_step_complete(self, flow_name: str, step: Step, result: StepResult) -> None:
        if self._status is not None:
            self._status.stop()
            self._status = None

        self._completed += 1
        if not result.uses:
            result.uses = step.uses
        if not result.flow_name:
            result.flow_name = flow_name

        index = self._step_indices.get(f"{flow_name}:{step.name}", self._completed)
        print_step_panel(result, index=index)
        self._console.print()

    def _step_status_text(
        self,
        step: Step,
        index: int,
        *,
        current: int | None = None,
        total: int | None = None,
    ) -> str:
        text = f"[bold]Step {index}/{self._estimated}[/]  {step.name} [dim]({step.uses})[/]"
        if current is not None and total is not None:
            text += f" [dim]|[/] item {current}/{total}"
        return text

    def on_step_error(self, flow_name: str, step: Step, error: BaseException) -> None:
        if self._status is not None:
            self._status.stop()
            self._status = None
        self._console.print(
            f"[bold red]✗ {step.name}[/] failed in flow [cyan]{flow_name}[/]: {error}"
        )

    def on_workflow_complete(self) -> None:
        if self._status is not None:
            self._status.stop()
            self._status = None
        elapsed = time.monotonic() - self._started
        self._console.print(
            Rule(
                f"[green]{self._completed} step(s)[/] in [cyan]{elapsed:.1f}s[/]",
                style="dim",
            )
        )

    def on_workflow_interrupted(self) -> None:
        if self._status is not None:
            self._status.stop()
            self._status = None
        self._console.print(Rule("[yellow]Interrupted[/]", style="dim"))
