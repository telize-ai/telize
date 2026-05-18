import json
import subprocess
import sys
from pathlib import Path

from telize.config import load_spec
from telize.runtime import WorkflowRunner

FIXTURES = Path(__file__).parent / "fixtures"


def test_yaml_step_runs_external_workflow_with_input() -> None:
    workflow = FIXTURES / "yaml_input_workflow.yaml"
    spec = load_spec(workflow)
    state = WorkflowRunner(spec, workflow).run()

    alert = state.steps["build_alert"].output
    assert "child-only-model" in alert
    assert "launch ready" in alert


def test_yaml_step_child_uses_own_config_not_parent() -> None:
    workflow = FIXTURES / "yaml_child_config_workflow.yaml"
    spec = load_spec(workflow)
    state = WorkflowRunner(spec, workflow).run()
    output = state.steps["run_child"].output
    assert "child-only-model" in output
    assert "parent-model" not in output


def test_cli_workflow_input_pairs() -> None:
    workflow = FIXTURES / "cli_input_workflow.yaml"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "telize",
            "-f",
            str(workflow),
            "--input",
            "name=world",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "hello world" in result.stdout


def test_cli_workflow_input_file(tmp_path: Path) -> None:
    workflow = FIXTURES / "cli_input_workflow.yaml"
    input_file = tmp_path / "input.yaml"
    input_file.write_text("name: from-file\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "telize",
            "-f",
            str(workflow),
            "--input-file",
            str(input_file),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "hello from-file" in result.stdout


def test_cli_workflow_input_stdin() -> None:
    workflow = FIXTURES / "cli_input_workflow.yaml"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "telize",
            "-f",
            str(workflow),
            "--input-stdin",
        ],
        input=json.dumps({"name": "stdin"}),
        check=True,
        capture_output=True,
        text=True,
    )
    assert "hello stdin" in result.stdout
