from pathlib import Path

from telize.config import load_spec
from telize.runtime import WorkflowRunner

FIXTURES = Path(__file__).parent / "fixtures"


def test_directory_input_default_separator(tmp_path: Path) -> None:
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "a.md").write_text("alpha", encoding="utf-8")
    (notes / "b.md").write_text("beta", encoding="utf-8")
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        f"""
config:
  entrypoint: main
flows:
  main:
    steps:
      - name: load
        uses: input
        directory:
          path: {notes.as_posix()}
          include: "*.md"
""",
        encoding="utf-8",
    )

    state = WorkflowRunner(load_spec(workflow), workflow).run()
    output = state.steps["load"].output
    assert output == "## a.md\n\nalpha\n<|separator|>\n## b.md\n\nbeta"


def test_directory_input_custom_separator(tmp_path: Path) -> None:
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "a.md").write_text("alpha", encoding="utf-8")
    (notes / "b.md").write_text("beta", encoding="utf-8")
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        f"""
config:
  entrypoint: main
flows:
  main:
    steps:
      - name: load
        uses: input
        directory:
          path: {notes.as_posix()}
          include: "*.md"
          separator: "==="
""",
        encoding="utf-8",
    )

    state = WorkflowRunner(load_spec(workflow), workflow).run()
    output = state.steps["load"].output
    assert output == "## a.md\n\nalpha===## b.md\n\nbeta"
