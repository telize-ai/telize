import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "spec_reference.yaml"


def test_validate_example() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "telize", "-f", str(EXAMPLE), "--validate-only"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "release_pipeline" in result.stdout


def test_keyboard_interrupt_exits_cleanly(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from telize.cli import main

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
        run: echo hi
""",
        encoding="utf-8",
    )

    def raise_interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr("telize.cli.WorkflowRunner.run", raise_interrupt)

    with pytest.raises(SystemExit) as exc_info:
        main(["-f", str(workflow)])

    assert exc_info.value.code == 130


def test_run_minimal_fixture() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "telize", "-f", str(FIXTURES / "shell_only.yaml")],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "greet" in result.stdout
    assert "hello telize" in result.stdout
