from __future__ import annotations

from pathlib import Path

import pytest

from telize.config import load_spec
from telize.runtime import WorkflowRunner
from telize.runtime.runner import repeat_wait_seconds

FIXTURES = Path(__file__).parent / "fixtures"


def test_repeat_wait_seconds() -> None:
    assert repeat_wait_seconds(0, 5.0) == 0.0
    assert repeat_wait_seconds(10, 3.0) == 7.0
    assert repeat_wait_seconds(10, 10.0) == 0.0
    assert repeat_wait_seconds(10, 15.0) == 0.0
    assert repeat_wait_seconds(3600, 120.0) == 3480.0


def test_repeat_disabled_by_default() -> None:
    path = FIXTURES / "minimal_workflow.yaml"
    spec = load_spec(path)
    assert spec.config.repeat is None


def test_repeat_disabled_for_negative_one(tmp_path: Path) -> None:
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
    spec = load_spec(workflow)
    assert spec.config.repeat == -1


def test_no_repeat_runs_once(tmp_path: Path) -> None:
    from test_observer import RecordingObserver

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
    spec = load_spec(workflow)
    observer = RecordingObserver()
    WorkflowRunner(spec, workflow, observer=observer).run()
    assert observer.events.count("workflow_done") == 1


def test_repeat_zero_runs_immediately(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
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
    sleeps: list[float] = []
    monkeypatch.setattr("telize.runtime.runner.time.sleep", lambda seconds: sleeps.append(seconds))

    calls = {"n": 0}
    real_run_once = WorkflowRunner._run_once

    def counting_run_once(self: WorkflowRunner):
        calls["n"] += 1
        if calls["n"] >= 3:
            raise KeyboardInterrupt
        return real_run_once(self)

    monkeypatch.setattr(WorkflowRunner, "_run_once", counting_run_once)

    state = WorkflowRunner(spec, workflow).run()

    assert calls["n"] == 3
    assert sleeps == []
    assert state is not None


def test_repeat_interval_waits_from_run_start(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        """
config:
  entrypoint: main
  repeat: 10
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
    times = iter([0.0, 3.0, 3.0])
    sleeps: list[float] = []

    monkeypatch.setattr("telize.runtime.runner.time.monotonic", lambda: next(times, 100.0))
    monkeypatch.setattr(
        "telize.runtime.runner.time.sleep",
        lambda seconds: sleeps.append(seconds) or (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    calls = {"n": 0}
    real_run_once = WorkflowRunner._run_once

    def counting_run_once(self: WorkflowRunner):
        calls["n"] += 1
        return real_run_once(self)

    monkeypatch.setattr(WorkflowRunner, "_run_once", counting_run_once)

    state = WorkflowRunner(spec, workflow).run()

    assert calls["n"] == 1
    assert sleeps == [7.0]
    assert state is not None


def test_repeat_interval_skips_wait_when_run_exceeds_interval(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        """
config:
  entrypoint: main
  repeat: 10
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
    times = iter([0.0, 12.0, 12.0, 12.0, 24.0, 24.0])
    sleeps: list[float] = []

    monkeypatch.setattr("telize.runtime.runner.time.monotonic", lambda: next(times, 100.0))
    monkeypatch.setattr(
        "telize.runtime.runner.time.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    calls = {"n": 0}
    real_run_once = WorkflowRunner._run_once

    def counting_run_once(self: WorkflowRunner):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise KeyboardInterrupt
        return real_run_once(self)

    monkeypatch.setattr(WorkflowRunner, "_run_once", counting_run_once)

    state = WorkflowRunner(spec, workflow).run()

    assert calls["n"] == 2
    assert sleeps == []
    assert state is not None
