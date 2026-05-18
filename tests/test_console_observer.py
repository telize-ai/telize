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
    import telize.console.display as display

    buffer = StringIO()
    display._CONSOLE = Console(file=buffer, width=120, force_terminal=True)

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

    display._CONSOLE = None
