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
    assert "hello telize" in state.steps["echo_greet"].output


def test_output_to_on_shell_step(tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        """
config:
  entrypoint: main
flows:
  main:
    steps:
      - name: greet
        uses: shell
        run: echo "hello telize"
        output_to: ./greet_output.txt
""",
        encoding="utf-8",
    )
    spec = load_spec(workflow)
    state = WorkflowRunner(spec, workflow).run()
    result = state.steps["greet"]
    assert result.output.strip() == "hello telize"
    assert result.output_path == tmp_path / "greet_output.txt"
    assert result.output_path.read_text(encoding="utf-8").strip() == "hello telize"


def test_vars_in_loop(tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        """
config:
  entrypoint: main
vars:
  hosts: "alpha, beta"
  greeting: hello
flows:
  main:
    steps:
      - name: greet_each
        uses: shell
        loop:
          items: "{{ vars.hosts }}"
          split_by: ","
        run: echo "{{ vars.greeting }} {{ item }}"
""",
        encoding="utf-8",
    )
    spec = load_spec(workflow)
    assert spec.vars == {"hosts": "alpha, beta", "greeting": "hello"}
    state = WorkflowRunner(spec, workflow).run()
    output = state.steps["greet_each"].output
    assert "hello alpha" in output
    assert "hello beta" in output
