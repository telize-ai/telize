from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from telize.config import load_spec
from telize.config.models import Step
from telize.runtime import WorkflowRunner
from telize.runtime.state import StepResult

FIXTURES = Path(__file__).parent / "fixtures"


@dataclass
class RecordingObserver:
    events: list[str] = field(default_factory=list)

    def on_workflow_start(self, entrypoint: str, *, estimated_steps: int) -> None:
        self.events.append(f"workflow:{entrypoint}:{estimated_steps}")

    def on_flow_start(self, flow_name: str) -> None:
        self.events.append(f"flow_start:{flow_name}")

    def on_flow_complete(self, flow_name: str) -> None:
        self.events.append(f"flow_done:{flow_name}")

    def on_step_start(self, flow_name: str, step: Step, *, index: int) -> None:
        self.events.append(f"step_start:{flow_name}:{step.name}:{step.uses}")

    def on_step_loop_progress(
        self, flow_name: str, step: Step, *, current: int, total: int
    ) -> None:
        self.events.append(f"loop:{step.name}:{current}/{total}")

    def on_step_complete(self, flow_name: str, step: Step, result: StepResult) -> None:
        self.events.append(f"step_done:{step.name}")

    def on_step_skipped(
        self, flow_name: str, step: Step, result: StepResult, *, index: int
    ) -> None:
        self.events.append(f"step_skipped:{step.name}:{index}")

    def on_step_error(self, flow_name: str, step: Step, error: BaseException) -> None:
        self.events.append(f"step_err:{step.name}")

    def on_workflow_complete(self) -> None:
        self.events.append("workflow_done")

    def on_workflow_interrupted(self) -> None:
        self.events.append("workflow_interrupted")


def test_observer_loop_progress_events(monkeypatch: pytest.MonkeyPatch) -> None:
    from contextlib import contextmanager

    from telize.config.models import ModelConfig
    from telize.providers.base import LLMClient

    class FakeClient(LLMClient):
        def chat(self, prompt: str, *, system: str | None = None) -> str:
            return prompt

    @contextmanager
    def fake_client(_model: ModelConfig):
        yield FakeClient()

    monkeypatch.setattr("telize.runtime.actions.llm.get_llm_client", fake_client)

    path = FIXTURES / "loop_workflow.yaml"
    spec = load_spec(path)
    observer = RecordingObserver()
    WorkflowRunner(spec, path, observer=observer).run()

    assert observer.events.count("loop:loop_llm:1/3") == 1
    assert observer.events.count("loop:loop_llm:2/3") == 1
    assert observer.events.count("loop:loop_llm:3/3") == 1


def test_observer_events_on_minimal_run() -> None:
    path = FIXTURES / "minimal_workflow.yaml"
    spec = load_spec(path)
    observer = RecordingObserver()
    WorkflowRunner(spec, path, observer=observer).run()
    assert observer.events[0].startswith("workflow:main:")
    assert "step_start:main:greet:shell" in observer.events
    assert "step_done:greet" in observer.events
    assert observer.events[-1] == "workflow_done"


def test_observer_skipped_when_false(tmp_path: Path) -> None:
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
        run: echo "alpha"
      - name: skipped
        uses: shell
        when: "{{ 'beta' in steps.seed.output }}"
        run: echo "nope"
""",
        encoding="utf-8",
    )
    observer = RecordingObserver()
    WorkflowRunner(load_spec(workflow), workflow, observer=observer).run()
    assert "step_start:main:skipped:shell" not in observer.events
    assert "step_skipped:skipped:2" in observer.events
    assert "step_done:seed" in observer.events
