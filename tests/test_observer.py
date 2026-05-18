from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

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

    def on_step_complete(self, flow_name: str, step: Step, result: StepResult) -> None:
        self.events.append(f"step_done:{step.name}")

    def on_step_error(self, flow_name: str, step: Step, error: BaseException) -> None:
        self.events.append(f"step_err:{step.name}")

    def on_workflow_complete(self) -> None:
        self.events.append("workflow_done")


def test_observer_events_on_minimal_run() -> None:
    path = FIXTURES / "minimal_workflow.yaml"
    spec = load_spec(path)
    observer = RecordingObserver()
    WorkflowRunner(spec, path, observer=observer).run()
    assert observer.events[0].startswith("workflow:main:")
    assert "step_start:main:greet:shell" in observer.events
    assert "step_done:greet" in observer.events
    assert observer.events[-1] == "workflow_done"
