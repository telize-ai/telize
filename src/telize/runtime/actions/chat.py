from __future__ import annotations

from collections.abc import Callable

from rich.panel import Panel
from rich.prompt import Prompt

from telize.config.models import ChatStep, Step
from telize.console.terminal import get_console
from telize.exceptions import ExecutionError
from telize.runtime.actions.base import ActionContext, ActionExecutor
from telize.runtime.state import StepResult

PromptUserFn = Callable[[str], str]


def prompt_user(message: str) -> str:
    """Display a styled prompt and return the user's response."""
    console = get_console()
    console.print()
    if message.strip():
        console.print(
            Panel(
                message.rstrip(),
                title="[bold #a371f7]◈ Telize[/]  [dim]waiting for input[/]",
                border_style="#a371f7",
                padding=(1, 2),
            )
        )
        console.print()
    try:
        return Prompt.ask("[bold green]You[/]")
    except EOFError:
        raise KeyboardInterrupt from None


class ChatActionExecutor(ActionExecutor):
    """Interactive steps that collect user input in the terminal."""

    uses = "chat"

    def __init__(self, prompt_user_fn: PromptUserFn | None = None) -> None:
        self._prompt_user = prompt_user_fn or prompt_user

    def execute(self, step: Step, ctx: ActionContext) -> StepResult:
        if not isinstance(step, ChatStep):
            raise ExecutionError(f"expected chat step, got {step.uses}")

        message = ctx.renderer.render(step.message)
        try:
            output = self._prompt_user(message)
        except EOFError:
            raise KeyboardInterrupt from None
        return StepResult(name=step.name, output=output)
