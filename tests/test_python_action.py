from pathlib import Path

from telize.config import load_spec
from telize.runtime import WorkflowRunner


def test_python_step_imports_from_workflow_directory(tmp_path: Path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "process.py").write_text(
        """
def double(value: str) -> str:
    return value * 2
""",
        encoding="utf-8",
    )

    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        """
config:
  entrypoint: main
flows:
  main:
    steps:
      - name: seed
        uses: shell
        run: echo "ab"
      - name: run_python
        uses: python
        call: scripts.process.double
        args:
          value: "{{ steps.seed.output }}"
""",
        encoding="utf-8",
    )

    spec = load_spec(workflow)
    state = WorkflowRunner(spec, workflow.resolve()).run()

    assert state.get_output("run_python") == "ab\nab\n"
