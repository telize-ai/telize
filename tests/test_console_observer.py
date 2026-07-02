from __future__ import annotations

from io import StringIO
from pathlib import Path
from unittest.mock import patch

from rich.console import Console

from telize.config import load_spec
from telize.console.observer import RichConsoleObserver
from telize.runtime import WorkflowRunner

FIXTURES = Path(__file__).parent / "fixtures"


def test_steps_printed_in_execution_order() -> None:
    import telize.console.terminal as terminal

    buffer = StringIO()
    terminal._CONSOLE = Console(file=buffer, width=120, force_terminal=True)

    path = FIXTURES / "minimal_workflow.yaml"
    spec = load_spec(path)
    observer = RichConsoleObserver(spec, path)

    with patch("telize.runtime.actions.llm.generate_completion", lambda _ctx, p: f"llm:{p}"):
        WorkflowRunner(spec, path, observer=observer).run()

    out = buffer.getvalue()
    greet_pos = out.find("greet")
    echo_pos = out.find("echo_greet")
    assert greet_pos != -1 and echo_pos != -1
    assert greet_pos < echo_pos, "greet should appear before echo_greet in output"

    terminal._CONSOLE = None


def test_loop_progress_updates_status_in_place() -> None:
    path = FIXTURES / "loop_workflow.yaml"
    spec = load_spec(path)
    observer = RichConsoleObserver(spec, path)
    observer._estimated = 1
    step = spec.flows["main"].steps[0]

    status_updates: list[str] = []

    class CapturingStatus:
        def __init__(self, status: str, **kwargs: object) -> None:
            status_updates.append(status)

        def start(self) -> None: ...

        def stop(self) -> None: ...

        def update(self, status: str, **kwargs: object) -> None:
            status_updates.append(status)

    with patch("telize.console.observer.Status", CapturingStatus):
        observer.on_step_start("main", step, index=1)
        observer.on_step_loop_progress("main", step, current=2, total=10)

    assert status_updates[0] == "[bold]Step 1/1[/]  loop_llm [dim](llm)[/]"
    assert status_updates[-1] == "[bold]Step 1/1[/]  loop_llm [dim](llm)[/] [dim]|[/] item 2/10"
