from __future__ import annotations

from pathlib import Path

import pytest

from telize.config import load_spec
from telize.exceptions import ConfigError
from telize.runtime import WorkflowRunner


def test_repeat_defaults_to_zero() -> None:
    path = Path(__file__).parent / "fixtures" / "minimal_workflow.yaml"
    spec = load_spec(path)
    assert spec.config.repeat == 0


def test_negative_repeat_rejected(tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        """
config:
  entrypoint: main
  repeat: -1
flows:
  main:
    steps:
      - name: greet
        uses: shell
        run: echo hi
""",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="repeat"):
        load_spec(workflow)


def test_repeat_zero_runs_once(tmp_path: Path) -> None:
    from test_observer import RecordingObserver

    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        """
config:
  entrypoint: main
  repeat: 0
flows:
  main:
    steps:
      - name: greet
        uses: shell
        run: echo hi
""",
        encoding="utf-8",
    )
    spec = load_spec(workflow)
    observer = RecordingObserver()
    WorkflowRunner(spec, workflow, observer=observer).run()
    assert observer.events.count("workflow_done") == 1


def test_repeat_runs_n_times(tmp_path: Path) -> None:
    from test_observer import RecordingObserver

    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        """
config:
  entrypoint: main
  repeat: 3
flows:
  main:
    steps:
      - name: greet
        uses: shell
        run: echo hi
""",
        encoding="utf-8",
    )
    spec = load_spec(workflow)
    observer = RecordingObserver()
    WorkflowRunner(spec, workflow, observer=observer).run()
    assert observer.events.count("workflow_done") == 3
    assert observer.events.count("workflow:main:1") == 3
