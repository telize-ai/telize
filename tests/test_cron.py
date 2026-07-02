from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from telize.config import load_spec
from telize.exceptions import ConfigError
from telize.runtime import WorkflowRunner
from telize.runtime.runner import cron_wait_seconds

FIXTURES = Path(__file__).parent / "fixtures"


def test_cron_wait_seconds() -> None:
    base = datetime(2026, 7, 2, 12, 30, 0)
    assert cron_wait_seconds("0 * * * *", now=base) == 30 * 60
    assert cron_wait_seconds("30 12 * * *", now=datetime(2026, 7, 2, 12, 29, 0)) == 60.0
    assert cron_wait_seconds("0 13 * * *", now=base) == 30 * 60


def test_cron_disabled_by_default() -> None:
    path = FIXTURES / "minimal_workflow.yaml"
    spec = load_spec(path)
    assert spec.config.cron is None


def test_invalid_cron_rejected(tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        """
config:
  entrypoint: main
  cron: not-a-cron
flows:
  main:
    steps:
      - name: greet
        uses: shell
        run: echo hi
""",
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="invalid cron expression"):
        load_spec(workflow)


def test_no_cron_runs_once(tmp_path: Path) -> None:
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


def test_cron_loops_and_waits(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        """
config:
  entrypoint: main
  cron: "0 * * * *"
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
    waits = iter([1800.0, 3600.0])
    sleeps: list[float] = []

    monkeypatch.setattr(
        "telize.runtime.runner.cron_wait_seconds",
        lambda _cron: next(waits, 0.0),
    )
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
    assert sleeps == [1800.0, 3600.0]
    assert state is not None


def test_cron_interrupt_returns_last_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.yaml"
    workflow.write_text(
        """
config:
  entrypoint: main
  cron: "0 * * * *"
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

    monkeypatch.setattr("telize.runtime.runner.cron_wait_seconds", lambda _cron: 60.0)
    monkeypatch.setattr(
        "telize.runtime.runner.time.sleep",
        lambda _seconds: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    state = WorkflowRunner(spec, workflow).run()
    assert state is not None
