from __future__ import annotations

import re
from io import StringIO
from pathlib import Path

import pytest
from rich.console import Console

from telize.config import load_spec
from telize.config.models import GlobalConfig
from telize.console.display import print_validation_ok, print_workflow_results
from telize.runtime import WorkflowRunner
from telize.runtime.state import ExecutionState, StepResult

FIXTURES = Path(__file__).parent / "fixtures"

_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


def _plain_console_output(buffer: StringIO) -> str:
    return _ANSI_ESCAPE.sub("", buffer.getvalue())


@pytest.fixture
def console_buffer():
    import telize.console.display as display

    buffer = StringIO()
    previous = display._CONSOLE
    display._CONSOLE = Console(file=buffer, width=120, force_terminal=True)
    try:
        yield buffer
    finally:
        display._CONSOLE = previous


def test_print_workflow_results_renders(console_buffer: StringIO) -> None:
    state = ExecutionState(
        config=GlobalConfig(entrypoint="main", model="test"),
        base_path=Path("."),
    )
    state.set_step(
        StepResult(
            name="greet",
            output="hello world",
            uses="shell",
            flow_name="main",
        )
    )
    state.set_step(
        StepResult(
            name="think",
            output="## Analysis\n\nAll good.",
            uses="llm",
            flow_name="main",
        )
    )

    path = FIXTURES / "minimal_workflow.yaml"
    spec = load_spec(path)
    print_workflow_results(spec, path, state, entrypoint="main", elapsed=1.5)

    out = _plain_console_output(console_buffer)
    assert "Telize" in out
    assert "greet" in out
    assert "think" in out
    assert "hello world" in out
    assert "Analysis" in out


def test_print_validation_ok(console_buffer: StringIO) -> None:
    print_validation_ok(
        workflow_file=Path("test.yaml"),
        entrypoint="main",
        step_count=3,
    )
    assert "Valid workflow" in _plain_console_output(console_buffer)


def test_runner_populates_uses_metadata() -> None:
    path = FIXTURES / "minimal_workflow.yaml"
    spec = load_spec(path)
    state = WorkflowRunner(spec, path).run()
    assert state.steps["greet"].uses == "shell"
    assert state.steps["echo_greet"].uses == "shell"
