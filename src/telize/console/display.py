from __future__ import annotations

from pathlib import Path

from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from telize.config.models import WorkflowSpec
from telize.console.terminal import get_console
from telize.runtime.state import ExecutionState, StepResult

ACTION_LABELS: dict[str, tuple[str, str]] = {
    "llm": ("LLM", "bold magenta"),
    "shell": ("SHELL", "bold yellow"),
    "python": ("PYTHON", "bold cyan"),
    "input": ("INPUT", "bold green"),
    "chat": ("CHAT", "bold #a371f7"),
    "flow": ("FLOW", "bold red"),
    "yaml": ("YAML", "bold blue"),
}


def print_validation_ok(
    *,
    workflow_file: Path,
    entrypoint: str,
    step_count: int,
) -> None:
    console = get_console()
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim")
    table.add_column()
    table.add_row("File", str(workflow_file))
    table.add_row("Entrypoint", f"[cyan]{entrypoint}[/]")
    table.add_row("Steps", str(step_count))
    console.print(
        Panel(
            table,
            title="[bold green]✓ Valid workflow[/]",
            border_style="green",
            padding=(1, 2),
        )
    )


def print_workflow_header(
    spec_path: Path,
    entrypoint: str,
    model_names: tuple[str, ...],
    *,
    estimated_steps: int,
) -> None:
    console = get_console()
    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim", no_wrap=True)
    table.add_column()
    table.add_row("Workflow", f"[bold]{spec_path.name}[/]")
    table.add_row("Entrypoint", f"[cyan]{entrypoint}[/]")
    if model_names:
        table.add_row("Models", ", ".join(model_names))
    table.add_row("Steps", str(estimated_steps))
    console.print()
    console.print(
        Panel(
            table,
            title="[bold #a371f7]◈ Telize[/]  [dim]running workflow[/]",
            border_style="#a371f7",
            padding=(1, 2),
        )
    )
    console.print()


def print_step_panel(result: StepResult, *, index: int) -> None:
    get_console().print(_build_step_panel(result, index=index))


def print_workflow_results(
    spec: WorkflowSpec,
    spec_path: Path,
    state: ExecutionState,
    *,
    entrypoint: str,
    elapsed: float,
) -> None:
    """Print all step results at once (used in tests and replay tooling)."""
    console = get_console()
    print_workflow_header(
        spec_path,
        entrypoint,
        tuple(sorted(spec.models)),
        estimated_steps=len(state.steps),
    )

    for index, result in enumerate(state.steps.values(), start=1):
        print_step_panel(result, index=index)
        console.print()

    console.print(
        Rule(
            f"[green]{len(state.steps)} step(s)[/] in [cyan]{elapsed:.1f}s[/]",
            style="dim",
        )
    )


def _build_step_panel(result: StepResult, *, index: int) -> Panel:
    uses = result.uses or "step"
    label, style = ACTION_LABELS.get(uses, (uses.upper(), "bold white"))
    title = Text()
    title.append(f"{index:02d} ", style="dim")
    title.append(f"{result.name} ", style="bold")
    title.append(label, style=style)
    if result.flow_name:
        title.append(f"  ·  {result.flow_name}", style="dim")

    subtitle_parts: list[str] = []
    if result.output_path:
        subtitle_parts.append(f"→ {result.output_path}")
    subtitle = "  ".join(subtitle_parts)

    if result.output:
        body = _render_step_body(result.output, uses)
    else:
        body = Text("(no output)", style="dim")

    return Panel(
        body,
        title=title,
        subtitle=subtitle if subtitle else None,
        border_style=_panel_border(uses),
        padding=(1, 2),
    )


def _panel_border(uses: str) -> str:
    return {
        "llm": "magenta",
        "shell": "yellow",
        "python": "cyan",
        "input": "green",
        "chat": "#a371f7",
        "flow": "red",
        "yaml": "blue",
    }.get(uses, "white")


def _render_step_body(output: str, uses: str) -> Markdown | Syntax | Text:
    text = output.rstrip()
    if not text:
        return Text("")

    if uses == "shell":
        return Text(text)
    if uses == "yaml":
        return Syntax(text, "yaml", theme="monokai", word_wrap=True)
    if uses == "python":
        return Syntax(text, "python", theme="monokai", word_wrap=True)
    if uses == "llm" or (uses == "input" and _looks_like_markdown(text)):
        return _as_markdown(text)
    return Text(text)


def _looks_like_markdown(text: str) -> bool:
    markers = ("# ", "## ", "- ", "* ", "```", "**", "\n- ", "\n* ")
    return any(marker in text for marker in markers)


def _as_markdown(content: str) -> Markdown | Text:
    try:
        return Markdown(content)
    except Exception:
        return Text(content)
