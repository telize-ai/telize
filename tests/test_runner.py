from pathlib import Path

from telize.config import load_spec
from telize.runtime import WorkflowRunner

FIXTURES = Path(__file__).parent / "fixtures"


def test_run_minimal_workflow() -> None:
    path = FIXTURES / "minimal_workflow.yaml"
    spec = load_spec(path)
    state = WorkflowRunner(spec, path).run()
    assert "greet" in state.steps
    assert "echo_greet" in state.steps
    assert "hello telize" in state.steps["greet"].output
    assert "ollama:" in state.steps["echo_greet"].output
    assert "hello telize" in state.steps["echo_greet"].output
